#!/usr/bin/env python3
"""
Arctic Satellite Imagery Collector — Sentinel-1 SAR

Fetches Sentinel-1 C-band SAR imagery over the Arctic monitoring region from
Copernicus Data Space (free tier). Writes GeoTIFF tiles to
data/satellite_imagery/tiles/ and appends to data/satellite_imagery/metadata.json.

Designed to run daily from .github/workflows/satellite_monitor.yml.

Credentials:
    Environment variables (CI):      SENTINEL_CLIENT_ID / SENTINEL_CLIENT_SECRET
    Local dev fallback:              config.yaml under key `sentinel_hub.*`

Usage:
    python scripts/collect_satellite.py                       # production default
    python scripts/collect_satellite.py --dry-run             # search only, no download
    python scripts/collect_satellite.py --tiles 3             # fewer tiles this run
    python scripts/collect_satellite.py --resolution 200      # lower res = fewer PU
    python scripts/collect_satellite.py --days-back 14        # wider time window
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml

try:
    from sentinelhub import (
        BBox,
        CRS,
        DataCollection,
        MimeType,
        SentinelHubCatalog,
        SentinelHubRequest,
        SHConfig,
        bbox_to_dimensions,
    )
except ImportError:
    print("ERROR: sentinelhub package not installed. Run: pip install sentinelhub", file=sys.stderr)
    sys.exit(2)


# ============================================================================
# Config
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
SATELLITE_DIR = DATA_DIR / 'satellite_imagery'
TILES_DIR = SATELLITE_DIR / 'tiles'
THUMBNAILS_DIR = SATELLITE_DIR / 'thumbnails'

# Thumbnail size — grayscale PNG, committed to git for the dashboard viewer.
# Larger dim = more detail but bigger commits. 512 px keeps PNGs ~80–180 KB.
THUMBNAIL_MAX_DIM = 512

# Arctic monitoring region (matches AIS coverage zone).
ARCTIC_REGION = {
    'lat_min': 65.0,
    'lat_max': 82.0,
    'lon_min': 0.0,
    'lon_max': 40.0,
}

# ----------------------------------------------------------------------------
# AIS-driven targeting: fetch live vessel positions, find density hotspots,
# request SAR tiles centered on where high-interest vessels actually cluster.
# This guarantees AIS overlap for validation — any CFAR detection without a
# nearby AIS match is a real dark-vessel candidate.
# Falls back to static zones if AIS fetch fails.
# ----------------------------------------------------------------------------
AIS_URL = "https://henrfo.github.io/ArcticShadowTracker/vessel_tracks.json"
MIN_ARCTIC_LAT = 65.0
CELL_LAT_STEP = 0.5   # grid cell: ~55km lat
CELL_LON_STEP = 1.0   # grid cell: ~35km lon at 70°N
HOTSPOT_HALF_LAT = 0.25   # tile bbox: ±28km lat
HOTSPOT_HALF_LON = 0.65   # tile bbox: ±25km lon at 70°N

FALLBACK_ZONES = [
    {'name': 'norwegian_coast', 'bbox': [14.0, 69.0, 16.0, 70.0]},
    {'name': 'barents_sea', 'bbox': [30.0, 70.5, 32.0, 71.5]},
    {'name': 'svalbard_approach', 'bbox': [14.0, 77.5, 16.0, 78.5]},
]

# Defaults (overridable via CLI)
DEFAULT_TILES = 5
DEFAULT_RESOLUTION_M = 20
DEFAULT_DAYS_BACK = 7

# Retention / quota constants
TILE_RETENTION_DAYS = 14
MONTHLY_PU_BUDGET = 30_000
PU_WARNING_THRESHOLD = 0.83   # warn at 83% of monthly budget

# Copernicus Data Space Process API hard limit: neither output dimension can
# exceed 2500 px per request. At 100 m resolution, any scene wider than
# ~250 km needs resolution automatically scaled down to fit. Zone tiles can
# span ~300 km so this kicks in routinely.
MAX_OUTPUT_DIM = 2500

# Retry policy for Copernicus API download calls
MAX_DOWNLOAD_RETRIES = 3
RETRY_BACKOFF_SECONDS = (1, 2, 4)


# ============================================================================
# Logging — matches the pattern in app.py
# ============================================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('arctic-shadow-tracker-satellite')


# ============================================================================
# Credentials
# ============================================================================

def load_credentials() -> dict:
    """Load Sentinel Hub credentials. Env vars take priority (CI), then config.yaml (local dev)."""
    client_id = os.getenv('SENTINEL_CLIENT_ID')
    client_secret = os.getenv('SENTINEL_CLIENT_SECRET')
    if client_id and client_secret:
        logger.info("Using credentials from environment variables")
        return {'client_id': client_id, 'client_secret': client_secret}

    config_path = BASE_DIR / 'config.yaml'
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        sh = config.get('sentinel_hub') or {}
        if not sh.get('client_id') or not sh.get('client_secret'):
            raise KeyError('sentinel_hub.client_id / client_secret missing from config.yaml')
        logger.info("Using credentials from config.yaml")
        return {'client_id': sh['client_id'], 'client_secret': sh['client_secret']}
    except FileNotFoundError:
        raise RuntimeError(
            "No credentials: set SENTINEL_CLIENT_ID / SENTINEL_CLIENT_SECRET env vars "
            "or create config.yaml with sentinel_hub.client_id and sentinel_hub.client_secret"
        )


def configure_sentinel_hub(credentials: dict) -> SHConfig:
    """Build a Copernicus Data Space (NOT commercial Sentinel Hub) SHConfig."""
    config = SHConfig()
    config.sh_client_id = credentials['client_id']
    config.sh_client_secret = credentials['client_secret']
    config.sh_token_url = 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
    config.sh_base_url = 'https://sh.dataspace.copernicus.eu'
    if not config.sh_client_id or not config.sh_client_secret:
        raise RuntimeError('Empty Sentinel Hub credentials after load')
    logger.info("Copernicus Data Space API configured (%s)", config.sh_base_url)
    return config


# ============================================================================
# Quota estimation
# ============================================================================

def _arctic_bbox() -> BBox:
    return BBox(
        bbox=[
            ARCTIC_REGION['lon_min'], ARCTIC_REGION['lat_min'],
            ARCTIC_REGION['lon_max'], ARCTIC_REGION['lat_max'],
        ],
        crs=CRS.WGS84,
    )


def estimate_pu_per_tile(resolution_m: int, n_bands: int = 2) -> float:
    """Rough PU estimate for a single Sentinel-1 IW scene at the given resolution.

    A Sentinel-1 IW swath is about 250 km × 170 km. We use per-scene bbox
    (not the full Arctic) because Copernicus charges by output pixel count.

    Copernicus Data Space charges roughly:
        PU = ceil(output_pixels / 512²) × bands × request_type_multiplier
    For Sentinel-1 GRD FLOAT32 output the multiplier is ~3x.

    Real cost is reported on the Copernicus dashboard. We use a conservative
    estimate that over-counts slightly to give a safety margin.
    """
    # Typical Sentinel-1 IW scene footprint in km
    scene_width_km = 250
    scene_height_km = 170
    pixels_x = int(scene_width_km * 1000 / resolution_m)
    pixels_y = int(scene_height_km * 1000 / resolution_m)
    output_pixels = pixels_x * pixels_y
    tiles_512 = max(1, (output_pixels + 512 * 512 - 1) // (512 * 512))
    return tiles_512 * n_bands * 3.0  # ~3x for S1 GRD FLOAT32


def log_quota_forecast(tiles_per_run: int, resolution_m: int, runs_per_month: int = 30) -> None:
    per_tile = estimate_pu_per_tile(resolution_m)
    per_run = per_tile * tiles_per_run
    monthly = per_run * runs_per_month
    used_pct = monthly / MONTHLY_PU_BUDGET * 100
    logger.info(
        "Quota forecast: ~%.0f PU/tile × %d tiles = %.0f PU/run × %d runs/month = %.0f PU/month (%.0f%% of %d budget)",
        per_tile, tiles_per_run, per_run, runs_per_month, monthly, used_pct, MONTHLY_PU_BUDGET,
    )
    if used_pct >= PU_WARNING_THRESHOLD * 100:
        logger.warning(
            "Projected monthly PU usage (%.0f%%) exceeds %.0f%% warning threshold. "
            "Consider lowering --tiles, --resolution, or --days-back.",
            used_pct, PU_WARNING_THRESHOLD * 100,
        )


# ============================================================================
# Catalog search + download
# ============================================================================

def search_sentinel1_imagery(config: SHConfig, bbox: BBox, days_back: int,
                              zone_name: str = 'arctic') -> list:
    """Search the Copernicus catalog for Sentinel-1 IW GRD tiles in a given bbox.

    Parameterized by bbox so the caller can query either the full Arctic region
    or a narrow high-value sub-zone. zone_name is log-only.
    """
    logger.info("Searching Sentinel-1 catalog for zone %r (last %d days)", zone_name, days_back)
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days_back)

    collection = DataCollection.SENTINEL1_IW.define_from(
        name='sentinel-1-grd',
        service_url=config.sh_base_url,
    )
    catalog = SentinelHubCatalog(config=config)
    # Include geometry + bbox so we can request per-scene footprints on download
    # (full-Arctic at 100m blows the PU budget by ~20x).
    results = list(catalog.search(
        collection,
        bbox=bbox,
        time=(start_time, end_time),
        filter="sar:instrument_mode='IW'",
        fields={
            'include': [
                'id',
                'bbox',
                'geometry',
                'properties.datetime',
                'properties.sar:instrument_mode',
            ],
            'exclude': [],
        },
    ))
    logger.info("  %s: found %d Sentinel-1 scenes", zone_name, len(results))
    return results


def _bbox_from_list(b: list) -> BBox:
    return BBox(bbox=b, crs=CRS.WGS84)


def _get_ais_hotspots(n_tiles: int) -> list:
    """Compute top vessel density cells from live AIS data.

    Fetches vessel_tracks.json, filters to high-interest vessels (Russia,
    China, shadow fleet, suspected shadow) above MIN_ARCTIC_LAT, grids into
    ~50km cells, and returns the top N cell centers as (lat, lon, name) tuples.
    """
    try:
        resp = requests.get(AIS_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("AIS fetch failed: %s — using fallback zones", exc)
        return []

    vessels = data.get('vessels', {})
    logger.info("AIS hotspot targeting — %d vessels loaded", len(vessels))

    cells = {}  # (cell_lat, cell_lon) -> count
    for mmsi, v in vessels.items():
        # High-interest filter
        if not (v.get('country') in ('Russia', 'China')
                or v.get('is_shadow_fleet')
                or v.get('is_suspected_shadow')):
            continue
        # Get most recent position
        for tier in ('realtime', 'tactical', 'strategic'):
            pts = v.get('tiers', {}).get(tier, [])
            if pts:
                pt = max(pts, key=lambda p: p.get('timestamp', ''))
                lat, lon = pt.get('lat'), pt.get('lon')
                if lat is not None and lon is not None and lat >= MIN_ARCTIC_LAT:
                    key = (round(lat / CELL_LAT_STEP) * CELL_LAT_STEP,
                           round(lon / CELL_LON_STEP) * CELL_LON_STEP)
                    cells[key] = cells.get(key, 0) + 1
                break

    if not cells:
        logger.warning("No high-interest Arctic vessels found — using fallback zones")
        return []

    ranked = sorted(cells.items(), key=lambda x: x[1], reverse=True)
    hotspots = []
    for (lat, lon), count in ranked[:n_tiles]:
        name = f"hotspot_{lat:.1f}N_{lon:.0f}E_{count}v"
        logger.info("  AIS hotspot: %.1f°N, %.0f°E — %d high-interest vessels", lat, lon, count)
        hotspots.append((lat, lon, name))
    return hotspots


def select_tiles_by_ais_hotspots(config: SHConfig, days_back: int,
                                  total_target: int) -> list:
    """Select SAR tiles centered on live AIS vessel density hotspots.

    Computes hotspots from live AIS, queries the Sentinel-1 catalog for each
    hotspot bbox (~50km × 50km), and takes the most recent scene per hotspot.
    Falls back to static FALLBACK_ZONES if AIS fetch fails.
    """
    hotspots = _get_ais_hotspots(total_target)

    # Build target bboxes: either from hotspots or fallback zones
    if hotspots:
        targets = []
        for lat, lon, name in hotspots:
            bbox = [lon - HOTSPOT_HALF_LON, lat - HOTSPOT_HALF_LAT,
                    lon + HOTSPOT_HALF_LON, lat + HOTSPOT_HALF_LAT]
            targets.append({'name': name, 'bbox': bbox})
    else:
        targets = FALLBACK_ZONES[:total_target]

    logger.info("Querying Sentinel-1 catalog for %d target areas", len(targets))

    selected = []
    seen_ids = set()
    for target in targets:
        if len(selected) >= total_target:
            break
        scenes = search_sentinel1_imagery(
            config,
            _bbox_from_list(target['bbox']),
            days_back=days_back,
            zone_name=target['name'],
        )
        for s in scenes:
            sid = s.get('id')
            if not sid or sid in seen_ids:
                continue
            seen_ids.add(sid)
            s['_zone'] = target['name']
            # Override download bbox to the tight hotspot area (~50km)
            # instead of the full scene footprint (~250km). This is what
            # makes 20m resolution actually achievable within the 2500px cap.
            s['_target_bbox'] = target['bbox']
            selected.append(s)
            break  # one scene per hotspot

    logger.info("Selected %d tiles from %s",
                len(selected),
                'AIS hotspots' if hotspots else 'fallback zones')
    return selected


def _scene_bbox(tile_info: dict) -> BBox:
    """Extract a BBox from a catalog search result.

    Prefers the STAC `bbox` field (a simple [min_lon, min_lat, max_lon, max_lat]
    list) over `geometry`, which may be a complex MultiPolygon. Falls back to
    the full Arctic bbox if neither is present.
    """
    stac_bbox = tile_info.get('bbox')
    if stac_bbox and len(stac_bbox) == 4:
        min_lon, min_lat, max_lon, max_lat = stac_bbox
        # Clamp to the Arctic monitoring region — a scene may extend beyond it.
        min_lon = max(min_lon, ARCTIC_REGION['lon_min'])
        max_lon = min(max_lon, ARCTIC_REGION['lon_max'])
        min_lat = max(min_lat, ARCTIC_REGION['lat_min'])
        max_lat = min(max_lat, ARCTIC_REGION['lat_max'])
        if min_lon < max_lon and min_lat < max_lat:
            return BBox(bbox=[min_lon, min_lat, max_lon, max_lat], crs=CRS.WGS84)
    logger.warning("Scene %s missing bbox metadata — falling back to full Arctic bbox",
                   tile_info.get('id', '?'))
    return _arctic_bbox()


def _fit_dimensions(bbox: BBox, target_res_m: int) -> tuple:
    """Compute (width, height) for a bbox at a target resolution, scaling the
    resolution down if either dimension would exceed MAX_OUTPUT_DIM.

    Returns ((width, height), effective_resolution_m).

    Copernicus Data Space caps Process API output at 2500 px per side. Zone
    tiles at 100 m often exceed this (e.g. 283 km wide → 2830 px). When that
    happens we bump the resolution (meters/pixel) up until the size fits.
    """
    size = bbox_to_dimensions(bbox, resolution=target_res_m)
    eff_res = target_res_m
    if max(size) > MAX_OUTPUT_DIM:
        # Ceiling of (target_res * ratio) gives us the smallest resolution
        # that pulls both dimensions under the cap. One extra +1 for safety
        # against bbox_to_dimensions rounding edge cases.
        scale = max(size) / MAX_OUTPUT_DIM
        eff_res = int(target_res_m * scale) + 1
        size = bbox_to_dimensions(bbox, resolution=eff_res)
        # Iterate once more in case rounding still leaves a dimension over
        while max(size) > MAX_OUTPUT_DIM:
            eff_res += 1
            size = bbox_to_dimensions(bbox, resolution=eff_res)
    return size, eff_res


def download_sentinel1_tile(config: SHConfig, tile_info: dict, resolution_m: int) -> str | None:
    """Download one Sentinel-1 tile as VV+VH float32 GeoTIFF. Returns local path or None."""
    tile_id = tile_info.get('id', 'unknown')
    tile_date = tile_info.get('properties', {}).get('datetime', '')

    # Use the target bbox (hotspot ~50km) if available, otherwise the scene's
    # own bbox. Hotspot bboxes are small enough for 20m resolution within the
    # 2500px API cap; full scene bboxes (~250km) would auto-scale to ~100m.
    target_bbox = tile_info.get('_target_bbox')
    bbox = _bbox_from_list(target_bbox) if target_bbox else _scene_bbox(tile_info)
    size, eff_res = _fit_dimensions(bbox, resolution_m)
    if eff_res != resolution_m:
        logger.info(
            "  resolution auto-scaled from %dm to %dm to fit %dpx API cap",
            resolution_m, eff_res, MAX_OUTPUT_DIM,
        )
    logger.info(
        "Downloading %s (%s) — bbox %s, size %dx%d @ %dm",
        tile_id, tile_date, list(bbox), size[0], size[1], eff_res,
    )

    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: [{ bands: ["VV", "VH"], units: "LINEAR_POWER" }],
            output: { bands: 2, sampleType: "FLOAT32" }
        };
    }
    function evaluatePixel(sample) { return [sample.VV, sample.VH]; }
    """

    collection = DataCollection.SENTINEL1_IW.define_from(
        name='sentinel-1-grd',
        service_url=config.sh_base_url,
    )
    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=collection,
                time_interval=(tile_date, tile_date),
                other_args={'dataFilter': {'mosaickingOrder': 'mostRecent'}},
            )
        ],
        responses=[SentinelHubRequest.output_response('default', MimeType.TIFF)],
        bbox=bbox,
        size=size,
        config=config,
    )

    # Retry loop for transient Copernicus API errors
    for attempt in range(MAX_DOWNLOAD_RETRIES):
        try:
            tile_data = request.get_data()
            if not tile_data:
                logger.warning("Empty response on attempt %d for %s", attempt + 1, tile_id)
                continue

            # sentinelhub returns a list of numpy arrays (decoded imagery), NOT
            # raw TIFF bytes. Previously we were writing tile_data[0].tobytes()
            # which produced a float32 buffer with no TIFF header — broken for
            # any downstream reader. Use tifffile.imwrite() to produce a real
            # multi-sample GeoTIFF-compatible file.
            import tifffile  # transitively installed via sentinelhub

            timestamp_str = datetime.fromisoformat(tile_date.replace('Z', '')).strftime('%Y%m%d_%H%M%S')
            tile_filename = f"{timestamp_str}_{tile_id[:8]}.tiff"
            tile_path = TILES_DIR / tile_filename
            tifffile.imwrite(str(tile_path), tile_data[0])
            size_mb = tile_path.stat().st_size / 1024 / 1024
            logger.info("Saved %s (%.1f MB)", tile_path.name, size_mb)
            return str(tile_path)

        except Exception as exc:  # noqa: BLE001
            if attempt < MAX_DOWNLOAD_RETRIES - 1:
                backoff = RETRY_BACKOFF_SECONDS[attempt]
                logger.warning("Download attempt %d/%d failed: %s — retrying in %ds",
                               attempt + 1, MAX_DOWNLOAD_RETRIES, exc, backoff)
                time.sleep(backoff)
            else:
                logger.error("Download failed after %d attempts: %s", MAX_DOWNLOAD_RETRIES, exc)
                return None
    return None


# ============================================================================
# Thumbnail generation — SAR GeoTIFF → grayscale PNG for the dashboard viewer
# ============================================================================

def generate_thumbnail(tiff_path: str) -> str | None:
    """Convert a Sentinel-1 GRD GeoTIFF to a grayscale PNG thumbnail.

    Sentinel-1 data is FLOAT32 backscatter in linear power units (range ~0 to ~1,
    most values near zero). A raw conversion looks almost black. We:

        1. Take the VV band (first channel; VH is second)
        2. Apply log scaling (dB) to stretch the dynamic range
        3. Percentile clip to 2nd–98th for contrast
        4. Normalize to 0–255 uint8
        5. Downscale to THUMBNAIL_MAX_DIM with Lanczos resampling

    Returns the PNG path, or None on failure (logged, non-fatal).
    """
    try:
        import numpy as np
        import tifffile
        from PIL import Image
    except ImportError as exc:
        logger.error("Cannot generate thumbnails — missing dep: %s", exc)
        return None

    try:
        THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
        tiff_path_obj = Path(tiff_path)
        png_path = THUMBNAILS_DIR / (tiff_path_obj.stem + '.png')

        arr = tifffile.imread(str(tiff_path_obj))
        # SAR GRD VV+VH is stored as shape (H, W, 2) — take the VV band
        if arr.ndim == 3 and arr.shape[-1] >= 1:
            vv = arr[..., 0].astype(np.float32)
        else:
            vv = arr.astype(np.float32)

        # Guard against all-zero / all-NaN tiles
        finite = np.isfinite(vv) & (vv > 0)
        if not finite.any():
            logger.warning("Thumbnail skipped — tile has no valid SAR samples: %s", tiff_path_obj.name)
            return None

        # Log scale to dB (avoid log(0) by masking zeros to a small floor)
        db = np.where(finite, 10.0 * np.log10(np.where(vv > 0, vv, 1e-10)), -50.0)

        # Percentile clip for contrast stretch
        p_lo, p_hi = np.percentile(db[finite], [2, 98])
        if p_hi - p_lo < 1e-6:
            p_hi = p_lo + 1.0  # degenerate range guard
        clipped = np.clip(db, p_lo, p_hi)

        # Normalize to uint8 grayscale
        normalized = ((clipped - p_lo) / (p_hi - p_lo) * 255.0).astype(np.uint8)

        img = Image.fromarray(normalized, mode='L')
        img.thumbnail((THUMBNAIL_MAX_DIM, THUMBNAIL_MAX_DIM), Image.LANCZOS)
        img.save(str(png_path), 'PNG', optimize=True)

        size_kb = png_path.stat().st_size / 1024
        logger.info("Thumbnail %s (%dx%d, %.0f KB)", png_path.name, img.width, img.height, size_kb)
        return str(png_path)

    except Exception as exc:  # noqa: BLE001
        logger.warning("Thumbnail generation failed for %s: %s", tiff_path, exc)
        return None


def cleanup_old_thumbnails(days: int = TILE_RETENTION_DAYS) -> None:
    """Delete thumbnails whose timestamp is older than `days`. Mirrors cleanup_old_tiles."""
    if not THUMBNAILS_DIR.exists():
        return
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = 0
    for png_file in THUMBNAILS_DIR.glob('*.png'):
        try:
            parts = png_file.stem.split('_')[:2]
            if len(parts) != 2:
                continue
            file_time = datetime.strptime('_'.join(parts), '%Y%m%d_%H%M%S').replace(tzinfo=timezone.utc)
            if file_time < cutoff:
                png_file.unlink()
                deleted += 1
        except (ValueError, OSError):
            continue
    if deleted:
        logger.info("Cleaned up %d thumbnails older than %d days", deleted, days)


# ============================================================================
# Metadata + cleanup
# ============================================================================

def _tile_entry(tile_path: str, tile_info: dict, thumbnail_path: str | None = None) -> dict:
    """Build a serializable tile metadata entry from a downloaded (path, catalog_item) pair.

    Uses basename for `filename` — the full runner path is ephemeral and useless
    outside the GH Actions environment. The bbox is the per-scene footprint we
    actually downloaded (not the full Arctic), extracted via _scene_bbox().
    If a thumbnail was generated, its basename is included too. The zone label
    (if tile_info was tagged by select_tiles_from_zones) is persisted so the
    dashboard viewer and validator can show which high-value zone a tile came from.
    """
    bbox = _scene_bbox(tile_info)
    entry = {
        'id': tile_info.get('id', 'unknown'),
        'filename': Path(tile_path).name,
        'datetime': tile_info.get('properties', {}).get('datetime', ''),
        'instrument_mode': tile_info.get('properties', {}).get('sar:instrument_mode', ''),
        'bbox': [round(c, 4) for c in list(bbox)],  # [min_lon, min_lat, max_lon, max_lat]
    }
    if tile_info.get('_zone'):
        entry['zone'] = tile_info['_zone']
    if thumbnail_path:
        entry['thumbnail'] = Path(thumbnail_path).name
    return entry


def _parse_tile_ts(iso_ts: str) -> datetime | None:
    """Parse a tile's ISO timestamp. Returns None on failure."""
    if not iso_ts:
        return None
    try:
        return datetime.fromisoformat(iso_ts.replace('Z', '+00:00'))
    except Exception:
        return None


def _load_existing_metadata() -> dict:
    """Read the current metadata.json if it exists; return empty dict on any failure."""
    import json
    metadata_file = SATELLITE_DIR / 'metadata.json'
    if not metadata_file.exists():
        return {}
    try:
        with open(metadata_file, 'r') as f:
            return json.load(f) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read existing metadata.json, starting fresh: %s", exc)
        return {}


def save_metadata(imagery_results: list, downloaded: list, resolution_m: int) -> None:
    """Merge this run's tiles into metadata.json, keeping a rolling TILE_RETENTION_DAYS window.

    Enables downstream consumers (dashboard, detection) to see coverage from the
    last N days of runs, not just the current run.
    """
    import json
    metadata_file = SATELLITE_DIR / 'metadata.json'

    existing = _load_existing_metadata()
    old_tiles = existing.get('tiles', []) or []
    # `downloaded` is a list of (tile_path, tile_info, thumbnail_path) tuples
    new_tiles = [_tile_entry(path, info, thumb) for path, info, thumb in downloaded]

    # Merge by tile id; new entries win on conflict
    by_id: dict[str, dict] = {t['id']: t for t in old_tiles}
    for t in new_tiles:
        by_id[t['id']] = t

    # Drop tiles outside the retention window (matches on-disk TIFF cleanup)
    cutoff = datetime.now(timezone.utc) - timedelta(days=TILE_RETENTION_DAYS)
    merged: list[dict] = []
    dropped = 0
    for t in by_id.values():
        ts = _parse_tile_ts(t.get('datetime', ''))
        if ts is None or ts < cutoff:
            dropped += 1
            continue
        merged.append(t)
    merged.sort(key=lambda t: t.get('datetime', ''), reverse=True)

    metadata = {
        'last_updated': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'region': ARCTIC_REGION,
        'resolution_m': resolution_m,
        'history_window_days': TILE_RETENTION_DAYS,
        'tiles_downloaded_last_run': len(new_tiles),
        'tiles_in_history': len(merged),
        'catalog_results_last_run': len(imagery_results),
        'tiles': merged,
    }
    # Atomic write: write to temp then rename
    tmp_file = metadata_file.with_suffix('.json.tmp')
    with open(tmp_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    tmp_file.replace(metadata_file)

    logger.info(
        "Wrote %s — %d new tiles, %d in history (dropped %d older than %d days)",
        metadata_file.name, len(new_tiles), len(merged), dropped, TILE_RETENTION_DAYS,
    )


def cleanup_old_tiles(days: int = TILE_RETENTION_DAYS) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = 0
    for tile_file in TILES_DIR.glob('*.tiff'):
        try:
            parts = tile_file.stem.split('_')[:2]
            if len(parts) != 2:
                continue
            tile_time = datetime.strptime('_'.join(parts), '%Y%m%d_%H%M%S').replace(tzinfo=timezone.utc)
            if tile_time < cutoff:
                tile_file.unlink()
                deleted += 1
        except (ValueError, OSError):
            continue
    if deleted:
        logger.info("Cleaned up %d tiles older than %d days", deleted, days)


# ============================================================================
# Main
# ============================================================================

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--tiles', type=int, default=DEFAULT_TILES,
                   help=f'Number of tiles to download per run (default: {DEFAULT_TILES})')
    p.add_argument('--resolution', type=int, default=DEFAULT_RESOLUTION_M,
                   help=f'Pixel resolution in meters (default: {DEFAULT_RESOLUTION_M})')
    p.add_argument('--days-back', type=int, default=DEFAULT_DAYS_BACK,
                   help=f'Catalog search window in days (default: {DEFAULT_DAYS_BACK})')
    p.add_argument('--dry-run', action='store_true',
                   help='Authenticate and search catalog but skip downloading')
    return p.parse_args()


def main() -> int:
    args = parse_args()

    logger.info("=" * 60)
    logger.info("Arctic Satellite Imagery Collector — Sentinel-1 SAR")
    logger.info("tiles=%d resolution=%dm days_back=%d dry_run=%s",
                args.tiles, args.resolution, args.days_back, args.dry_run)
    logger.info("=" * 60)

    try:
        SATELLITE_DIR.mkdir(parents=True, exist_ok=True)
        TILES_DIR.mkdir(parents=True, exist_ok=True)

        log_quota_forecast(tiles_per_run=args.tiles, resolution_m=args.resolution)

        credentials = load_credentials()
        config = configure_sentinel_hub(credentials)

        # AIS-driven selection: fetch live vessel positions, find density
        # hotspots, request SAR tiles centered on those clusters at 20m.
        # Falls back to static zones if AIS fetch fails.
        selected = select_tiles_by_ais_hotspots(
            config, days_back=args.days_back, total_target=args.tiles,
        )
        if not selected:
            logger.warning("No imagery found in any high-value zone")
            return 0

        if args.dry_run:
            logger.info("[DRY RUN] Would download %d tiles:", len(selected))
            for i, info in enumerate(selected, start=1):
                logger.info("  %d. [%s] %s (%s)",
                            i,
                            info.get('_zone', '?'),
                            info.get('id', '?'),
                            info.get('properties', {}).get('datetime', '?'))
            logger.info("[DRY RUN] No tiles downloaded, no metadata written")
            return 0

        downloaded: list[tuple[str, dict, str | None]] = []
        for i, tile_info in enumerate(selected, start=1):
            zone = tile_info.get('_zone', '?')
            logger.info("Tile %d/%d [%s]", i, len(selected), zone)
            tile_path = download_sentinel1_tile(config, tile_info, resolution_m=args.resolution)
            if tile_path:
                thumbnail_path = generate_thumbnail(tile_path)
                downloaded.append((tile_path, tile_info, thumbnail_path))

        # `selected` is passed as imagery_results for the old per-run counter;
        # it represents "catalog results we considered in this run".
        save_metadata(selected, downloaded, resolution_m=args.resolution)
        cleanup_old_tiles()
        cleanup_old_thumbnails()

        logger.info("=" * 60)
        logger.info("Collection complete — %d/%d tiles downloaded", len(downloaded), args.tiles)
        logger.info("=" * 60)

        if len(downloaded) == 0:
            logger.error("Zero tiles downloaded despite imagery being available — treating as failure")
            return 1
        return 0

    except Exception:  # noqa: BLE001
        logger.exception("Fatal error during satellite collection")
        return 1


if __name__ == '__main__':
    sys.exit(main())
