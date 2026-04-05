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

# Arctic monitoring region (matches AIS coverage zone).
ARCTIC_REGION = {
    'lat_min': 65.0,
    'lat_max': 82.0,
    'lon_min': 0.0,
    'lon_max': 40.0,
}

# Defaults (overridable via CLI)
DEFAULT_TILES = 5
DEFAULT_RESOLUTION_M = 100
DEFAULT_DAYS_BACK = 7

# Retention / quota constants
TILE_RETENTION_DAYS = 14
MONTHLY_PU_BUDGET = 30_000
PU_WARNING_THRESHOLD = 0.83   # warn at 83% of monthly budget

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

def search_sentinel1_imagery(config: SHConfig, days_back: int) -> list:
    """Search the Copernicus catalog for Sentinel-1 IW GRD tiles in the Arctic bbox."""
    logger.info("Searching Sentinel-1 catalog (last %d days, Arctic bbox)", days_back)
    bbox = _arctic_bbox()
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
    logger.info("Found %d Sentinel-1 images in window", len(results))
    return results


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


def download_sentinel1_tile(config: SHConfig, tile_info: dict, resolution_m: int) -> str | None:
    """Download one Sentinel-1 tile as VV+VH float32 GeoTIFF. Returns local path or None."""
    tile_id = tile_info.get('id', 'unknown')
    tile_date = tile_info.get('properties', {}).get('datetime', '')

    # Use the scene's own bbox (not full Arctic) to keep PU cost bounded.
    bbox = _scene_bbox(tile_info)
    size = bbox_to_dimensions(bbox, resolution=resolution_m)
    logger.info(
        "Downloading %s (%s) — bbox %s, size %dx%d",
        tile_id, tile_date, list(bbox), size[0], size[1],
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

            timestamp_str = datetime.fromisoformat(tile_date.replace('Z', '')).strftime('%Y%m%d_%H%M%S')
            tile_filename = f"{timestamp_str}_{tile_id[:8]}.tiff"
            tile_path = TILES_DIR / tile_filename
            with open(tile_path, 'wb') as f:
                f.write(tile_data[0])
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
# Metadata + cleanup
# ============================================================================

def save_metadata(imagery_results: list, downloaded: list, resolution_m: int) -> None:
    import json
    metadata_file = SATELLITE_DIR / 'metadata.json'
    metadata = {
        'last_updated': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'region': ARCTIC_REGION,
        'resolution_m': resolution_m,
        'total_images_available': len(imagery_results),
        'images_downloaded': len(downloaded),
        'tiles': [
            {
                'path': path,
                'id': info.get('id', 'unknown'),
                'datetime': info.get('properties', {}).get('datetime', ''),
                'instrument_mode': info.get('properties', {}).get('sar:instrument_mode', ''),
            }
            for path, info in downloaded
        ],
    }
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    logger.info("Wrote %s", metadata_file.name)


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

        imagery_results = search_sentinel1_imagery(config, days_back=args.days_back)
        if not imagery_results:
            logger.warning("No imagery found for this region + time window")
            return 0

        if args.dry_run:
            logger.info("[DRY RUN] Would download %d of %d available tiles:",
                        min(args.tiles, len(imagery_results)), len(imagery_results))
            for i, info in enumerate(imagery_results[: args.tiles], start=1):
                logger.info("  %d. %s (%s)", i, info.get('id', '?'),
                            info.get('properties', {}).get('datetime', '?'))
            logger.info("[DRY RUN] No tiles downloaded, no metadata written")
            return 0

        downloaded: list[tuple[str, dict]] = []
        for i, tile_info in enumerate(imagery_results[: args.tiles], start=1):
            logger.info("Tile %d/%d", i, min(args.tiles, len(imagery_results)))
            tile_path = download_sentinel1_tile(config, tile_info, resolution_m=args.resolution)
            if tile_path:
                downloaded.append((tile_path, tile_info))

        save_metadata(imagery_results, downloaded, resolution_m=args.resolution)
        cleanup_old_tiles()

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
