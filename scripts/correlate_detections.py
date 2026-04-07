#!/usr/bin/env python3
"""
Correlate CFAR SAR detections with AIS vessel positions.

Reads scripts/detect_vessels_cfar.py output (detections.json) and fetches
vessel_tracks.json from gh-pages. For each detection:

    - If an AIS position exists within ±60 min and ≤2 km haversine distance,
      the detection is MATCHED — it validates a known vessel (true positive,
      good signal for recall measurement).
    - If no AIS match, the detection becomes a DARK VESSEL candidate and is
      emitted as an anomaly entry.

Output: data/anomalies/dark_vessels.json. Committed to main by
satellite_monitor.yml. Flask's /api/anomalies merges it with the main
gh-pages anomalies.json at request time, so the two pipelines stay
decoupled and can't clobber each other.

Usage:
    python scripts/correlate_detections.py
    python scripts/correlate_detections.py --vessel-tracks ./tracks.json
    python scripts/correlate_detections.py --radius-km 3 --window-min 90
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
DETECTIONS_PATH = DATA_DIR / 'satellite_imagery' / 'detections.json'
DARK_VESSELS_DIR = DATA_DIR / 'anomalies'
DARK_VESSELS_PATH = DARK_VESSELS_DIR / 'dark_vessels.json'

DEFAULT_VESSEL_TRACKS_URL = "https://henrfo.github.io/ArcticShadowTracker/vessel_tracks.json"
DEFAULT_SEARCH_RADIUS_KM = 2.0
DEFAULT_SEARCH_WINDOW_MIN = 60


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('correlate-detections')


# ============================================================================
# Loading
# ============================================================================

def load_detections() -> dict:
    if not DETECTIONS_PATH.exists():
        logger.error("%s not found — run detect_vessels_cfar.py first", DETECTIONS_PATH)
        sys.exit(1)
    with open(DETECTIONS_PATH, 'r') as f:
        return json.load(f)


def load_vessel_tracks(source: str) -> dict:
    if source.startswith(('http://', 'https://')):
        if requests is None:
            logger.error("requests not installed — pass a local --vessel-tracks path")
            sys.exit(2)
        logger.info("Fetching vessel tracks from %s", source)
        r = requests.get(source, timeout=30)
        r.raise_for_status()
        return r.json()
    path = Path(source)
    if not path.exists():
        logger.error("vessel tracks file not found: %s", path)
        sys.exit(2)
    logger.info("Reading local vessel tracks from %s", path)
    with open(path, 'r') as f:
        return json.load(f)


def parse_iso(ts: str):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except Exception:
        return None


# ============================================================================
# Spatial/temporal matching
# ============================================================================

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers."""
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def find_nearest_ais(detection_lat: float, detection_lon: float,
                     detection_dt: datetime,
                     vessels: dict,
                     radius_km: float,
                     window_min: int) -> dict | None:
    """Return the closest-in-distance AIS vessel position within
    (radius_km, ±window_min) of the detection, or None.

    Scans all tier points of all vessels. Short-circuits when a match is
    found well below the radius (< 0.5 km) to avoid unnecessary work.
    """
    window = timedelta(minutes=window_min)
    best_km = float('inf')
    best_match = None

    for mmsi, v in vessels.items():
        tiers = v.get('tiers') or {}
        for tier_name in ('realtime', 'tactical', 'strategic'):
            for p in tiers.get(tier_name, []) or []:
                plat = p.get('lat')
                plon = p.get('lon')
                pt_dt = parse_iso(p.get('timestamp', ''))
                if plat is None or plon is None or pt_dt is None:
                    continue
                if abs(pt_dt - detection_dt) > window:
                    continue
                d_km = haversine_km(detection_lat, detection_lon, plat, plon)
                if d_km > radius_km:
                    continue
                if d_km < best_km:
                    best_km = d_km
                    best_match = {
                        'mmsi': mmsi,
                        'vessel_name': v.get('name'),
                        'country': v.get('country'),
                        'ship_type': v.get('ship_type'),
                        'distance_km': round(d_km, 3),
                        'timestamp': p.get('timestamp'),
                        'speed': p.get('speed'),
                    }
                    if best_km < 0.5:  # good enough, stop searching this vessel
                        break
        if best_km < 0.5:
            break

    return best_match


# ============================================================================
# Correlation → dark_vessel anomaly records
# ============================================================================

def _format_time(iso: str) -> str:
    dt = parse_iso(iso)
    if dt is None:
        return 'Unknown'
    return dt.strftime('%b %d, %H:%M')


def correlate(tile_records: list, vessels: dict,
              radius_km: float, window_min: int) -> tuple:
    """Walk per-tile CFAR detections, match vs AIS, split into
    (dark_vessel anomaly records, match stats).
    """
    anomalies: list = []
    total_detections = 0
    matched_count = 0

    for record in tile_records:
        tile_dt = parse_iso(record.get('tile_datetime', ''))
        for det in record.get('detections', []) or []:
            total_detections += 1
            lat = det.get('lat')
            lon = det.get('lon')
            if lat is None or lon is None or tile_dt is None:
                continue

            match = find_nearest_ais(lat, lon, tile_dt, vessels,
                                     radius_km=radius_km, window_min=window_min)

            # Enrich detection in-place with match status
            if match is not None:
                matched_count += 1
                det['matched_ais'] = True
                det['nearest_ais_km'] = match['distance_km']
                det['matched_vessel'] = {
                    'mmsi': match['mmsi'],
                    'name': match.get('vessel_name'),
                    'country': match.get('country'),
                }
                continue  # Known vessel — not a dark vessel

            det['matched_ais'] = False
            det['nearest_ais_km'] = None
            det['matched_vessel'] = None

            # No AIS within radius — emit dark_vessel anomaly
            anomalies.append({
                'anomaly_type': 'dark_vessel',
                'severity': det.get('severity') or 'high',
                'mmsi': None,
                'vessel_name': 'Unknown',
                'country': 'Unknown',
                'detected_at': record.get('tile_datetime'),
                'formatted_time': _format_time(record.get('tile_datetime', '')),
                'details': {
                    'detection': {
                        'lat': lat,
                        'lon': lon,
                        'confidence_db': det.get('confidence_db'),
                        'intensity_db': det.get('intensity_db'),
                        'estimated_length_m': det.get('estimated_length_m'),
                        'blob_size_pixels': det.get('blob_size_pixels'),
                    },
                    'tile_id': record.get('tile_id'),
                    'tile_zone': record.get('zone'),
                    'tile_datetime': record.get('tile_datetime'),
                    'nearest_ais_km': None,
                    'search_radius_km': radius_km,
                    'ais_search_window_min': window_min,
                    # Duplicate into last_position so the existing
                    # _anomaly_position() helper in app.py picks it up for
                    # SAR coverage enrichment and map panning.
                    'last_position': {'lat': lat, 'lon': lon},
                },
                'description': (
                    f"Vessel detected on SAR with no AIS signal within "
                    f"{radius_km:g} km "
                    f"(confidence {det.get('confidence_db')}σ, "
                    f"~{det.get('estimated_length_m')} m)"
                ),
            })

    # Newest first
    anomalies.sort(key=lambda a: a.get('detected_at', ''), reverse=True)
    return anomalies, total_detections, matched_count


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--vessel-tracks', default=DEFAULT_VESSEL_TRACKS_URL,
                    help='URL or local path to vessel_tracks.json')
    ap.add_argument('--radius-km', type=float, default=DEFAULT_SEARCH_RADIUS_KM,
                    help=f'AIS match radius km (default: {DEFAULT_SEARCH_RADIUS_KM})')
    ap.add_argument('--window-min', type=int, default=DEFAULT_SEARCH_WINDOW_MIN,
                    help=f'AIS match time window minutes ± (default: {DEFAULT_SEARCH_WINDOW_MIN})')
    ap.add_argument('--dry-run', action='store_true',
                    help='Run correlation but do not write dark_vessels.json')
    args = ap.parse_args()

    logger.info("=" * 60)
    logger.info("AIS-SAR correlation — radius %.1f km, window ±%d min",
                args.radius_km, args.window_min)
    logger.info("=" * 60)

    det_payload = load_detections()
    tile_records = det_payload.get('tiles', []) or []
    total_before = det_payload.get('total_detections_in_history', 0)
    logger.info("Loaded detections for %d tiles (total %d detections)",
                len(tile_records), total_before)

    tracks = load_vessel_tracks(args.vessel_tracks)
    vessels = tracks.get('vessels') or {}
    logger.info("Loaded %d vessels from AIS tracks (last_updated: %s)",
                len(vessels), tracks.get('last_updated'))

    anomalies, total_detections, matched = correlate(
        tile_records, vessels,
        radius_km=args.radius_km,
        window_min=args.window_min,
    )
    dark_candidates = total_detections - matched

    logger.info("=" * 60)
    logger.info("Results:")
    logger.info("  Total detections:       %d", total_detections)
    logger.info("  Matched to AIS:         %d", matched)
    logger.info("  Dark vessel candidates: %d", dark_candidates)
    logger.info("=" * 60)

    if args.dry_run:
        logger.info("[DRY RUN] Not writing dark_vessels.json")
        return 0

    DARK_VESSELS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        'last_updated': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'source': 'satellite_monitor.yml CFAR correlation',
        'tiles_analyzed': len(tile_records),
        'total_detections': total_detections,
        'matched_to_ais': matched,
        'dark_vessel_candidates': dark_candidates,
        'search_radius_km': args.radius_km,
        'ais_search_window_min': args.window_min,
        'anomalies': anomalies,
    }
    tmp = DARK_VESSELS_PATH.with_suffix('.json.tmp')
    with open(tmp, 'w') as f:
        json.dump(payload, f, indent=2)
    tmp.replace(DARK_VESSELS_PATH)
    logger.info("Wrote %s — %d dark vessel anomalies", DARK_VESSELS_PATH, len(anomalies))

    # Write enriched detections back (now includes matched_ais, nearest_ais_km,
    # matched_vessel per detection). The tile_records list was mutated in-place
    # by correlate().
    det_payload['correlated_at'] = payload['last_updated']
    det_payload['matched_to_ais'] = matched
    det_payload['dark_vessel_candidates'] = dark_candidates
    tmp_det = DETECTIONS_PATH.with_suffix('.json.tmp')
    with open(tmp_det, 'w') as f:
        json.dump(det_payload, f, indent=2)
    tmp_det.replace(DETECTIONS_PATH)
    logger.info("Wrote enriched %s — %d matched, %d dark", DETECTIONS_PATH, matched, dark_candidates)
    return 0


if __name__ == '__main__':
    sys.exit(main())
