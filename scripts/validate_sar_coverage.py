#!/usr/bin/env python3
"""
validate_sar_coverage.py — ground-truth vessel count per Sentinel-1 SAR tile.

Before building a vessel detection model, we need to know what we expect to
see in each SAR tile. This script answers: "for tile X captured at time T,
which AIS-broadcasting vessels were inside its footprint within ±30 minutes?"

That list is the ground truth for detection accuracy measurement. A detector
should find at least these vessels (maybe more — dark vessels not in AIS).
If it misses known AIS vessels, its recall is broken. If it finds everything
plus extras, those extras are candidate dark vessels.

Data sources:
    - data/satellite_imagery/metadata.json  (tile bboxes + timestamps)
    - Vessel tracks JSON from one of:
        1. A local path via --vessel-tracks (for offline / cached)
        2. https://henrfo.github.io/ArcticShadowTracker/vessel_tracks.json (default)

Usage:
    python scripts/validate_sar_coverage.py
    python scripts/validate_sar_coverage.py --tile-id S1C_IW_GRDH_1SDV_20260405T172903...
    python scripts/validate_sar_coverage.py --vessel-tracks ./tracks.json --window-min 30
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

BASE_DIR = Path(__file__).resolve().parent.parent
METADATA_PATH = BASE_DIR / 'data' / 'satellite_imagery' / 'metadata.json'

DEFAULT_VESSEL_TRACKS_URL = "https://henrfo.github.io/ArcticShadowTracker/vessel_tracks.json"
# 60 minutes covers a typical vessel displacement of ~15 km at cruising speed,
# comparable to per-scene bbox precision. Wider than 30m because 30m was too
# tight — the first validation run just barely missed a ship at +37m.
DEFAULT_WINDOW_MINUTES = 60


# ----------------------------------------------------------------------------
# Loading helpers
# ----------------------------------------------------------------------------

def load_metadata() -> dict:
    if not METADATA_PATH.exists():
        print(f"ERROR: {METADATA_PATH} does not exist. Run the satellite workflow first.",
              file=sys.stderr)
        sys.exit(2)
    with open(METADATA_PATH, 'r') as f:
        return json.load(f)


def load_vessel_tracks(source: str) -> dict:
    """Fetch vessel tracks from a URL or read a local JSON file."""
    if source.startswith(('http://', 'https://')):
        if requests is None:
            print("ERROR: requests library missing. Use --vessel-tracks <local-path> instead.",
                  file=sys.stderr)
            sys.exit(2)
        print(f"Fetching vessel tracks from {source}...", file=sys.stderr)
        r = requests.get(source, timeout=30)
        r.raise_for_status()
        return r.json()
    path = Path(source)
    if not path.exists():
        print(f"ERROR: vessel tracks file not found: {path}", file=sys.stderr)
        sys.exit(2)
    with open(path, 'r') as f:
        return json.load(f)


def parse_iso(ts: str) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except Exception:
        return None


# ----------------------------------------------------------------------------
# Spatial + temporal matching
# ----------------------------------------------------------------------------

def point_in_bbox(lat: float, lon: float, bbox: list) -> bool:
    """bbox = [min_lon, min_lat, max_lon, max_lat]"""
    min_lon, min_lat, max_lon, max_lat = bbox
    return min_lon <= lon <= max_lon and min_lat <= lat <= max_lat


def vessel_match(vessel: dict, tile_bbox: list, tile_dt: datetime,
                 window_minutes: int) -> dict | None:
    """Return a match record if any of the vessel's AIS points fell inside
    tile_bbox within ±window_minutes of tile_dt. Uses the point closest in
    time to the tile as the representative position.
    """
    tiers = vessel.get('tiers', {})
    all_points = []
    for tier_name in ('realtime', 'tactical', 'strategic'):
        for p in tiers.get(tier_name, []) or []:
            all_points.append(p)
    if not all_points:
        return None

    window = timedelta(minutes=window_minutes)
    best = None
    best_abs_delta = None
    for p in all_points:
        lat = p.get('lat')
        lon = p.get('lon')
        if lat is None or lon is None:
            continue
        if not point_in_bbox(lat, lon, tile_bbox):
            continue
        pt_dt = parse_iso(p.get('timestamp', ''))
        if pt_dt is None:
            continue
        delta = pt_dt - tile_dt
        if abs(delta) > window:
            continue
        abs_d = abs(delta.total_seconds())
        if best_abs_delta is None or abs_d < best_abs_delta:
            best_abs_delta = abs_d
            best = {
                'lat': lat,
                'lon': lon,
                'timestamp': p.get('timestamp'),
                'speed': p.get('speed'),
                'course': p.get('course'),
                'delta_seconds': int(delta.total_seconds()),
            }
    return best


# ----------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------

def classify_vessel(v: dict) -> str:
    """Short label for grouping results."""
    if v.get('is_buoy'):
        return 'buoy'
    if v.get('is_shadow_fleet'):
        return 'shadow'
    if v.get('is_suspected_shadow'):
        return 'suspected'
    country = v.get('country') or 'Unknown'
    ship_type = (v.get('ship_type') or '').lower()
    if country == 'Norway' and ('military' in ship_type or 'law enforcement' in ship_type):
        return 'norway_mil'
    return country.lower() if country != 'Unknown' else 'other'


def format_delta_short(sec: int) -> str:
    sign = '+' if sec >= 0 else '-'
    a = abs(sec)
    if a < 60:
        return f'{sign}{a}s'
    if a < 3600:
        return f'{sign}{a // 60}m{a % 60:02d}s'
    return f'{sign}{a // 3600}h{(a % 3600) // 60:02d}m'


def format_bbox(bbox: list) -> str:
    return (f'lon [{bbox[0]:.2f}, {bbox[2]:.2f}], '
            f'lat [{bbox[1]:.2f}, {bbox[3]:.2f}]')


def validate_tile(tile: dict, vessels: dict, window_minutes: int) -> dict:
    tile_id = tile.get('id', 'unknown')
    tile_dt = parse_iso(tile.get('datetime', ''))
    bbox = tile.get('bbox')

    if tile_dt is None or not bbox:
        return {
            'tile': tile,
            'error': 'Missing datetime or bbox',
            'matches': [],
        }

    matches = []
    for mmsi, v in vessels.items():
        hit = vessel_match(v, bbox, tile_dt, window_minutes)
        if hit:
            matches.append({
                'mmsi': mmsi,
                'name': v.get('name', 'Unknown'),
                'country': v.get('country', 'Unknown'),
                'ship_type': v.get('ship_type', 'Unknown'),
                'category': classify_vessel(v),
                **hit,
            })

    # Sort by absolute time delta (closest in time first)
    matches.sort(key=lambda m: abs(m.get('delta_seconds', 0)))
    return {'tile': tile, 'matches': matches}


def print_report(results: list, window_minutes: int) -> None:
    print()
    print('=' * 78)
    print(f'SAR tile coverage validation — AIS ground truth (±{window_minutes}m window)')
    print('=' * 78)

    total_matches = 0
    for idx, result in enumerate(results, start=1):
        tile = result['tile']
        matches = result.get('matches', [])
        total_matches += len(matches)
        tile_id = (tile.get('id') or '')[:55]
        tile_time = tile.get('datetime', '')
        bbox = tile.get('bbox', [0, 0, 0, 0])

        print()
        print(f'Tile {idx}: {tile_id}')
        print(f'    captured:     {tile_time}')
        print(f'    footprint:    {format_bbox(bbox)}')
        print(f'    thumbnail:    {tile.get("thumbnail") or "(none)"}')
        print(f'    EXPECTED AIS VESSELS: {len(matches)}')

        if matches:
            # Bucket by category
            by_cat = {}
            for m in matches:
                by_cat.setdefault(m['category'], 0)
                by_cat[m['category']] += 1
            bucket_str = ', '.join(f'{k}={v}' for k, v in sorted(by_cat.items()))
            print(f'    by category:  {bucket_str}')
            print()
            print('    Nearest-in-time samples (first 10):')
            for m in matches[:10]:
                delta = format_delta_short(m.get('delta_seconds', 0))
                speed = m.get('speed')
                speed_str = f'{speed:4.1f} kts' if isinstance(speed, (int, float)) else '   -   '
                name = (m.get('name') or '')[:30]
                cat = m.get('category', '?')
                print(f'      [{delta:>8}]  mmsi {m["mmsi"]:>9}  {speed_str}  '
                      f'lat {m["lat"]:+6.2f} lon {m["lon"]:+6.2f}  '
                      f'[{cat}]  {name}')
        else:
            print('    (no matching AIS vessels — tile is over open ocean or outside the '
                  f'{window_minutes}-min window)')

    print()
    print('=' * 78)
    print(f'TOTAL expected AIS vessels across {len(results)} tiles: {total_matches}')
    print('=' * 78)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--vessel-tracks', default=DEFAULT_VESSEL_TRACKS_URL,
                    help='URL or local path to vessel_tracks.json (default: gh-pages)')
    ap.add_argument('--tile-id', default=None,
                    help='Limit validation to a single tile by full id')
    ap.add_argument('--window-min', type=int, default=DEFAULT_WINDOW_MINUTES,
                    help=f'Time window in minutes (default: {DEFAULT_WINDOW_MINUTES})')
    args = ap.parse_args()

    metadata = load_metadata()
    all_tiles = metadata.get('tiles', []) or []
    if not all_tiles:
        print("No tiles in metadata.json. Run the satellite workflow first.", file=sys.stderr)
        return 1

    if args.tile_id:
        tiles = [t for t in all_tiles if t.get('id') == args.tile_id]
        if not tiles:
            print(f"Tile id not found: {args.tile_id}", file=sys.stderr)
            return 1
    else:
        tiles = all_tiles

    tracks = load_vessel_tracks(args.vessel_tracks)
    vessels = tracks.get('vessels', {}) or {}
    tracks_updated = tracks.get('last_updated', 'unknown')
    print(f"Loaded {len(vessels):,} vessels from vessel_tracks (last_updated: {tracks_updated})",
          file=sys.stderr)

    results = [validate_tile(t, vessels, args.window_min) for t in tiles]
    print_report(results, args.window_min)
    return 0


if __name__ == '__main__':
    sys.exit(main())
