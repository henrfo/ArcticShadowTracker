#!/usr/bin/env python3
"""
CFAR (Constant False Alarm Rate) vessel detection for Sentinel-1 SAR tiles.

At our collection resolution (100–114 m/pixel) ships appear as 1–3 bright
pixels against a darker ocean background. This is the regime where CFAR,
not ML, is the right tool. See docs/SAR_MODEL_RESEARCH.md for the reasoning.

Algorithm (dB-space for a more Gaussian noise distribution):
    1. Read VV band from the tile's float32 GeoTIFF
    2. Convert to dB:  db = 10 * log10(max(vv, eps))
    3. Compute local mean + std via vectorized uniform_filter on db and db²
    4. Threshold:  db > mean + ALPHA * std
    5. Morphological opening to kill single-pixel speckle
    6. Connected-component labelling (scipy.ndimage.label)
    7. Per-blob: size filter, centroid, dB-confidence, pixel-to-lat/lon
    8. Emit JSON detections.json with a rolling 14-day history

Runs inside satellite_monitor.yml after collect_satellite.py downloads tiles.
Complexity: O(H*W) via uniform_filter — a 2500x2500 tile finishes in ~2 s.

Usage:
    python scripts/detect_vessels_cfar.py                # all tiles in metadata
    python scripts/detect_vessels_cfar.py --tile <name>  # one tile by filename
    python scripts/detect_vessels_cfar.py --alpha 15 --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import numpy as np
    import tifffile
    from scipy.ndimage import median_filter, label, binary_opening, find_objects
except ImportError as exc:
    print(f"ERROR: missing dependency: {exc}", file=sys.stderr)
    print("Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(2)


# ============================================================================
# Config
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
SATELLITE_DIR = DATA_DIR / 'satellite_imagery'
TILES_DIR = SATELLITE_DIR / 'tiles'
METADATA_PATH = SATELLITE_DIR / 'metadata.json'
DETECTIONS_PATH = SATELLITE_DIR / 'detections.json'

# Rolling history matches on-disk tile retention (14 days)
HISTORY_RETENTION_DAYS = 14

# --- Tunable CFAR parameters (median-based robust variant) ----------------
#
# We use a MEDIAN filter for the local background and Median Absolute
# Deviation (MAD) for the local dispersion instead of classical
# mean+std. Rationale: a bright ship contaminates its own neighborhood
# and inflates mean-based std (verified during development), making the
# target mask itself. Median is naturally robust to outliers below the
# 50% occupancy threshold, so a 2–4 pixel target in a 15×15 window
# (225 samples, 1.8%) doesn't bias the background estimate. This is the
# standard CFAR-on-median formulation from the SAR processing literature.
BACKGROUND_CELLS = 15      # odd square window for median + MAD
ALPHA = 5.0                # multiplier on robust std (MAD × 1.4826)
MIN_BLOB_PIXELS = 1        # min connected-component size
MAX_BLOB_PIXELS = 20       # blobs bigger than this are probably land/ice
MIN_CONFIDENCE_DB = 4.0    # drop detections weaker than this in dB over median
MAX_BACKGROUND_DB = -25.0  # reject detections on bright backgrounds (land/coast/ice)


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('cfar-detector')


# ============================================================================
# Core CFAR
# ============================================================================

def _read_vv_band(tiff_path: Path) -> np.ndarray:
    """Load VV band from a multi-band Sentinel-1 GRD GeoTIFF as float32."""
    arr = tifffile.imread(str(tiff_path))
    if arr.ndim == 3 and arr.shape[-1] >= 1:
        vv = arr[..., 0]
    else:
        vv = arr
    return vv.astype(np.float32)


def _to_db(vv: np.ndarray) -> np.ndarray:
    """Linear-power to dB with a noise floor that avoids log(0)."""
    eps = 1e-10
    return 10.0 * np.log10(np.maximum(vv, eps)).astype(np.float32)


def _local_stats(db: np.ndarray, window: int) -> tuple:
    """Robust local background + dispersion via median + MAD.

    Returns (bg, robust_std) both shape-matching db. The MAD-derived
    robust std is scaled by 1.4826 to match Gaussian std for unbiased
    comparability with classical CFAR α values.

    Two median_filter passes — the expensive step. At 2500×2500 with
    window=15 this takes ~2–4 seconds per tile on a GH Actions runner.
    Still well under our per-tile budget.
    """
    bg = median_filter(db, size=window, mode='reflect')
    abs_dev = np.abs(db - bg)
    mad = median_filter(abs_dev, size=window, mode='reflect')
    robust_std = (1.4826 * mad).astype(np.float32)
    # Floor robust_std to avoid divide-by-zero in confidence calc for
    # perfectly uniform local regions (open ocean, glassy seas)
    robust_std = np.maximum(robust_std, 0.5)
    return bg, robust_std


def _severity_from_confidence(conf_db: float) -> str:
    if conf_db >= 16:
        return 'critical'
    if conf_db >= 12:
        return 'high'
    if conf_db >= 8:
        return 'medium'
    return 'low'


def _pixel_to_latlon(row: int, col: int, bbox: list, h: int, w: int) -> tuple:
    """Convert (row, col) pixel coordinates to (lat, lon) using the tile bbox.

    bbox is [min_lon, min_lat, max_lon, max_lat]. Row 0 is the NORTHERN edge
    (max_lat) in standard raster convention. Assumes linear interpolation,
    which is accurate enough for our ~250 km tiles.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    lat = max_lat - (row + 0.5) * (max_lat - min_lat) / h
    lon = min_lon + (col + 0.5) * (max_lon - min_lon) / w
    return lat, lon


def detect_vessels_in_tile(tile_meta: dict, alpha: float) -> list:
    """Run CFAR on a single tile. Returns a list of detection dicts."""
    filename = tile_meta.get('filename')
    bbox = tile_meta.get('bbox')
    tile_id = tile_meta.get('id')
    if not filename or not bbox:
        logger.warning("Tile %s missing filename or bbox — skipping", tile_id)
        return []

    tiff_path = TILES_DIR / filename
    if not tiff_path.exists():
        logger.warning("Tile file not found: %s — skipping", tiff_path)
        return []

    try:
        vv = _read_vv_band(tiff_path)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to read %s: %s", filename, exc)
        return []

    h, w = vv.shape[:2]
    logger.info("CFAR on %s  (%dx%d, α=%.1f)", filename, w, h, alpha)

    db = _to_db(vv)
    mean, std = _local_stats(db, BACKGROUND_CELLS)

    # Threshold in dB space
    with np.errstate(invalid='ignore'):
        target_mask = db > (mean + alpha * std)

    # Kill single-pixel speckle, keep 2+ connected bright pixels
    target_mask = binary_opening(target_mask, structure=np.ones((2, 2), dtype=bool))

    # Connected components → blobs
    blobs, n_blobs = label(target_mask)
    if n_blobs == 0:
        logger.info("  no candidate blobs")
        return []

    # Per-blob stats: size, centroid, mean dB, background stats at centroid
    # Vectorized via np.bincount on labels
    flat_labels = blobs.ravel()
    flat_db = db.ravel()
    flat_mean = mean.ravel()
    flat_std = std.ravel()

    sizes = np.bincount(flat_labels, minlength=n_blobs + 1)
    sum_db = np.bincount(flat_labels, weights=flat_db, minlength=n_blobs + 1)
    sum_mean = np.bincount(flat_labels, weights=flat_mean, minlength=n_blobs + 1)
    sum_std = np.bincount(flat_labels, weights=flat_std, minlength=n_blobs + 1)

    # Per-blob bounding boxes in pixel coords (slice objects)
    blob_slices = find_objects(blobs)  # list[tuple[slice, slice]], indexed 0..n_blobs-1

    # Centroids: need row/col per label. Use np.argwhere — fine since most
    # blobs are tiny at 1–3 pixels.
    rows, cols = np.nonzero(blobs)
    blob_ids = blobs[rows, cols]
    # Group by label id
    sum_rows = np.bincount(blob_ids, weights=rows, minlength=n_blobs + 1)
    sum_cols = np.bincount(blob_ids, weights=cols, minlength=n_blobs + 1)

    resolution_m = tile_meta.get('effective_resolution_m') or tile_meta.get('resolution_m') or 100

    detections = []
    for bid in range(1, n_blobs + 1):
        size = int(sizes[bid])
        if size < MIN_BLOB_PIXELS or size > MAX_BLOB_PIXELS:
            continue
        centroid_row = sum_rows[bid] / size
        centroid_col = sum_cols[bid] / size
        mean_intensity_db = float(sum_db[bid] / size)
        bg_mean_db = float(sum_mean[bid] / size)
        bg_std_db = float(sum_std[bid] / size)
        if bg_std_db < 1e-6:
            # Degenerate: uniform local neighborhood (shouldn't happen on real SAR)
            continue
        confidence_db = (mean_intensity_db - bg_mean_db) / bg_std_db
        if confidence_db < MIN_CONFIDENCE_DB:
            continue
        # Bright local background = land/coast/ice, not open water
        if bg_mean_db > MAX_BACKGROUND_DB:
            continue

        lat, lon = _pixel_to_latlon(int(centroid_row), int(centroid_col), bbox, h, w)

        # Rough vessel length: diameter in pixels × resolution.
        # sqrt(pixels) is a reasonable diameter proxy for blobby shapes.
        diameter_px = float(np.sqrt(size))
        est_length_m = round(diameter_px * resolution_m, 0)

        # Pixel and geographic bounding box for this blob
        row_sl, col_sl = blob_slices[bid - 1]  # find_objects is 0-indexed
        bbox_px = [int(col_sl.start), int(row_sl.start),
                   int(col_sl.stop), int(row_sl.stop)]
        sw_lat, sw_lon = _pixel_to_latlon(row_sl.stop, col_sl.start, bbox, h, w)
        ne_lat, ne_lon = _pixel_to_latlon(row_sl.start, col_sl.stop, bbox, h, w)
        bbox_geo = [round(sw_lon, 5), round(sw_lat, 5),
                    round(ne_lon, 5), round(ne_lat, 5)]

        detections.append({
            'lat': round(float(lat), 5),
            'lon': round(float(lon), 5),
            'intensity_db': round(mean_intensity_db, 2),
            'background_mean_db': round(bg_mean_db, 2),
            'background_std_db': round(bg_std_db, 2),
            'confidence_db': round(float(confidence_db), 2),
            'blob_size_pixels': size,
            'estimated_length_m': est_length_m,
            'bbox_pixels': bbox_px,
            'bbox_geo': bbox_geo,
            'severity': _severity_from_confidence(float(confidence_db)),
            'tile_id': tile_id,
            'tile_datetime': tile_meta.get('datetime'),
            'tile_zone': tile_meta.get('zone'),
        })

    detections.sort(key=lambda d: d['confidence_db'], reverse=True)
    logger.info("  %d candidate blobs → %d detections after filters",
                n_blobs, len(detections))
    return detections


# ============================================================================
# History + I/O
# ============================================================================

def _load_existing_detections() -> dict:
    if not DETECTIONS_PATH.exists():
        return {}
    try:
        with open(DETECTIONS_PATH, 'r') as f:
            return json.load(f) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read %s, starting fresh: %s", DETECTIONS_PATH, exc)
        return {}


def _parse_ts(iso: str):
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace('Z', '+00:00'))
    except Exception:
        return None


def _merge_history(old_tiles: list, new_tiles: list) -> list:
    """Merge per-tile detection records by tile_id; drop entries older than the
    retention window. New entries override old ones on conflict.
    """
    by_id = {t.get('tile_id'): t for t in old_tiles if t.get('tile_id')}
    for t in new_tiles:
        tid = t.get('tile_id')
        if tid:
            by_id[tid] = t
    cutoff = datetime.now(timezone.utc) - timedelta(days=HISTORY_RETENTION_DAYS)
    merged = []
    for t in by_id.values():
        ts = _parse_ts(t.get('tile_datetime', ''))
        if ts and ts >= cutoff:
            merged.append(t)
    merged.sort(key=lambda t: t.get('tile_datetime', ''), reverse=True)
    return merged


def save_detections(per_tile_records: list, dry_run: bool = False) -> None:
    """Persist per-tile detection results with rolling history."""
    existing = _load_existing_detections()
    merged = _merge_history(existing.get('tiles', []) or [], per_tile_records)

    total_detections = sum(len(t.get('detections', []) or []) for t in merged)
    payload = {
        'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'algorithm': 'CFAR (scipy.ndimage uniform_filter)',
        'params': {
            'variant': 'median-MAD robust CFAR',
            'alpha': ALPHA,
            'background_cells': BACKGROUND_CELLS,
            'min_blob_pixels': MIN_BLOB_PIXELS,
            'max_blob_pixels': MAX_BLOB_PIXELS,
            'min_confidence_db': MIN_CONFIDENCE_DB,
        },
        'history_window_days': HISTORY_RETENTION_DAYS,
        'tiles_in_history': len(merged),
        'total_detections_in_history': total_detections,
        'tiles': merged,
    }

    if dry_run:
        logger.info("[DRY RUN] Would write %s with %d tiles and %d detections",
                    DETECTIONS_PATH.name, len(merged), total_detections)
        return

    tmp = DETECTIONS_PATH.with_suffix('.json.tmp')
    with open(tmp, 'w') as f:
        json.dump(payload, f, indent=2)
    tmp.replace(DETECTIONS_PATH)
    logger.info("Wrote %s — %d tiles, %d detections",
                DETECTIONS_PATH.name, len(merged), total_detections)


# ============================================================================
# Main
# ============================================================================

def load_metadata() -> dict:
    if not METADATA_PATH.exists():
        logger.error("%s does not exist — run collect_satellite.py first", METADATA_PATH)
        sys.exit(1)
    with open(METADATA_PATH, 'r') as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tile', default=None, help='Restrict to one tile by filename')
    ap.add_argument('--alpha', type=float, default=ALPHA,
                    help=f'CFAR threshold multiplier (default: {ALPHA})')
    ap.add_argument('--dry-run', action='store_true',
                    help='Run detection but do not write detections.json')
    args = ap.parse_args()

    metadata = load_metadata()
    tiles = metadata.get('tiles', []) or []
    if args.tile:
        tiles = [t for t in tiles if t.get('filename') == args.tile]
        if not tiles:
            logger.error("No metadata entry found for tile filename %s", args.tile)
            return 1

    logger.info("=" * 60)
    logger.info("CFAR vessel detection — %d tiles, α=%.1f", len(tiles), args.alpha)
    logger.info("=" * 60)

    per_tile_records: list = []
    for tile_meta in tiles:
        detections = detect_vessels_in_tile(tile_meta, alpha=args.alpha)
        per_tile_records.append({
            'tile_id': tile_meta.get('id'),
            'filename': tile_meta.get('filename'),
            'tile_datetime': tile_meta.get('datetime'),
            'zone': tile_meta.get('zone'),
            'bbox': tile_meta.get('bbox'),
            'detection_count': len(detections),
            'detections': detections,
        })

    total = sum(len(r['detections']) for r in per_tile_records)
    logger.info("=" * 60)
    logger.info("Detection complete — %d total detections across %d tiles",
                total, len(per_tile_records))
    if total > 0:
        per_zone = {}
        for r in per_tile_records:
            z = r.get('zone') or 'unknown'
            per_zone[z] = per_zone.get(z, 0) + r['detection_count']
        for z, c in sorted(per_zone.items()):
            logger.info("  %s: %d", z, c)
    logger.info("=" * 60)

    save_detections(per_tile_records, dry_run=args.dry_run)
    return 0


if __name__ == '__main__':
    sys.exit(main())
