#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Real-Time Dashboard
Simple Flask server with auto-refreshing vessel map
"""

from flask import Flask, render_template, jsonify, make_response, send_from_directory, abort
from pathlib import Path
import json
import logging
import sys
import requests
from datetime import datetime, timezone
from functools import wraps

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.track_manager import process_vessel_tracks
from src.map_generator import generate_focused_map

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('arctic-shadow-tracker')

# Data directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
SNAPSHOTS_DIR = DATA_DIR / 'snapshots'
OUTPUTS_DIR = BASE_DIR / 'outputs'

# GitHub Pages URLs for data (updated every 5 minutes by GitHub Actions)
GITHUB_PAGES_VESSELS_URL = "https://henrfo.github.io/ArcticShadowTracker/vessel_tracks.json"
GITHUB_PAGES_ANOMALIES_URL = "https://henrfo.github.io/ArcticShadowTracker/data/anomalies/anomalies.json"

# Data freshness threshold — pipeline runs every 5 min, allow 6x tolerance
STALE_THRESHOLD_MINUTES = 30

# In-memory cache of the rendered Folium map HTML. Keyed on the ISO timestamp
# of the underlying vessel snapshot, so it auto-invalidates as soon as new data
# is published on gh-pages. Regeneration takes ~12s for ~5k vessels; every
# subsequent request inside the same 5-min window returns the cached HTML.
_map_cache = {'html': None, 'raw_last_update': None}

# Short-TTL cache for load_vessel_data() so we don't round-trip to GitHub Pages
# on every request. The upstream pipeline only publishes every ~5 minutes, so
# 30 seconds is plenty fresh — trades ~30s of staleness for a ~6s speedup per
# request. Map cache above chains on top of this.
_data_cache = {'result': None, 'fetched_at': 0.0}
DATA_TTL_SECONDS = 30

# SAR satellite coverage metadata — read from data/satellite_imagery/metadata.json
# which is updated daily by the satellite_monitor.yml workflow. Cached by file
# mtime so changes from new workflow runs are picked up automatically without
# needing a restart. Each anomaly is enriched with any nearby SAR passes.
_sar_cache = {'data': None, 'mtime': 0.0, 'loaded_at': 0.0}
SAR_CACHE_TTL_SECONDS = 60
SAR_TIME_WINDOW_HOURS = 12  # ± window for "nearby" SAR passes on an anomaly

# Dark-vessel anomalies — written by scripts/correlate_detections.py inside
# the satellite_monitor.yml workflow. Lives in a separate file from the
# main anomalies.json to avoid clobbering between the two workflows.
# /api/anomalies merges both at request time.
_dark_vessels_cache = {'data': None, 'mtime': 0.0, 'loaded_at': 0.0}


def add_cors_headers(response):
    """Add CORS headers to response"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


def no_cache(response):
    """Attach no-cache headers so clients never see stale stats."""
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def cors_enabled(f):
    """Decorator to add CORS headers to routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        return add_cors_headers(response)
    return decorated_function


def _empty_stats(last_update=None, stale_reason='No data available'):
    return {
        'total': 0,
        'russian': 0,
        'chinese': 0,
        'norwegian': 0,
        'norwegian_military': 0,
        'shadow_fleet': 0,
        'suspected_shadow': 0,
        'buoy': 0,
        'other': 0,
        'last_update': last_update or 'No data',
        'raw_last_update': None,
        'minutes_since_update': None,
        'is_stale': True,
        'stale_reason': stale_reason,
    }


def _format_age(minutes):
    """Format a duration in minutes as a human-readable 'X ago' string."""
    if minutes is None:
        return 'Unknown'
    if minutes < 1:
        return 'just now'
    if minutes < 60:
        return f"{int(minutes)}m ago"
    hours = minutes / 60
    if hours < 24:
        h = int(hours)
        m = int(minutes - h * 60)
        return f"{h}h {m}m ago"
    days = hours / 24
    d = int(days)
    h = int(hours - d * 24)
    return f"{d}d {h}h ago"


def _classify_vessels(vessel_tracks):
    """Count vessels into mutually exclusive buckets.

    Classification priority (each vessel counted exactly once):
        1. buoy
        2. shadow_fleet
        3. suspected_shadow
        4. norwegian_military  (Norway + military/law enforcement ship_type)
        5. russian             (pure: country == Russia, no flags above)
        6. chinese             (pure: country == China,  no flags above)
        7. norwegian           (pure: country == Norway,  no flags above)
        8. other               (everything else)
    """
    counts = {
        'buoy': 0,
        'shadow_fleet': 0,
        'suspected_shadow': 0,
        'norwegian_military': 0,
        'russian': 0,
        'chinese': 0,
        'norwegian': 0,
        'other': 0,
    }
    for v in vessel_tracks.values():
        if v.get('is_buoy'):
            counts['buoy'] += 1
            continue
        if v.get('is_shadow_fleet'):
            counts['shadow_fleet'] += 1
            continue
        if v.get('is_suspected_shadow'):
            counts['suspected_shadow'] += 1
            continue
        country = v.get('country') or ''
        ship_type = (v.get('ship_type') or '').lower()
        if country == 'Norway' and ('military' in ship_type or 'law enforcement' in ship_type):
            counts['norwegian_military'] += 1
            continue
        if country == 'Russia':
            counts['russian'] += 1
        elif country == 'China':
            counts['chinese'] += 1
        elif country == 'Norway':
            counts['norwegian'] += 1
        else:
            counts['other'] += 1
    return counts


def _compute_freshness(raw_last_update):
    """Return (minutes_since_update, pretty_age, is_stale, stale_reason)."""
    if not raw_last_update:
        return None, 'No data', True, 'No last_updated timestamp in data'
    try:
        dt = datetime.fromisoformat(raw_last_update.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        minutes = (now - dt).total_seconds() / 60
        pretty = _format_age(minutes)
        is_stale = minutes > STALE_THRESHOLD_MINUTES
        reason = f"Data is {pretty} (threshold: {STALE_THRESHOLD_MINUTES}m)" if is_stale else ''
        return minutes, pretty, is_stale, reason
    except Exception as exc:  # noqa: BLE001
        return None, 'Unknown', True, f'Could not parse last_updated: {exc}'


# ============================================================================
# SAR coverage — match anomalies to nearby Sentinel-1 passes
# ============================================================================

def _load_sar_metadata():
    """Load data/satellite_imagery/metadata.json with mtime-based cache invalidation.

    The file is written by scripts/collect_satellite.py after each workflow run.
    Cache is keyed on the file's mtime so new workflow deploys invalidate it
    automatically without needing a Flask restart.
    """
    import time as _time
    path = DATA_DIR / 'satellite_imagery' / 'metadata.json'
    if not path.exists():
        return {'tiles': []}
    try:
        mtime = path.stat().st_mtime
        now = _time.monotonic()
        cached = _sar_cache['data']
        if (cached is not None
                and _sar_cache['mtime'] == mtime
                and (now - _sar_cache['loaded_at']) < SAR_CACHE_TTL_SECONDS):
            return cached
        with open(path, 'r') as f:
            data = json.load(f)
        _sar_cache['data'] = data
        _sar_cache['mtime'] = mtime
        _sar_cache['loaded_at'] = now
        return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load SAR metadata: %s", exc)
        return {'tiles': []}


def _load_dark_vessels():
    """Load data/anomalies/dark_vessels.json with mtime-based cache invalidation.

    This file is written by scripts/correlate_detections.py inside the daily
    satellite_monitor.yml workflow. api_anomalies() merges its contents with
    the main anomalies.json stream from gh-pages at request time.
    """
    import time as _time
    path = DATA_DIR / 'anomalies' / 'dark_vessels.json'
    if not path.exists():
        return {'anomalies': []}
    try:
        mtime = path.stat().st_mtime
        now = _time.monotonic()
        cached = _dark_vessels_cache['data']
        if (cached is not None
                and _dark_vessels_cache['mtime'] == mtime
                and (now - _dark_vessels_cache['loaded_at']) < SAR_CACHE_TTL_SECONDS):
            return cached
        with open(path, 'r') as f:
            data = json.load(f)
        _dark_vessels_cache['data'] = data
        _dark_vessels_cache['mtime'] = mtime
        _dark_vessels_cache['loaded_at'] = now
        return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load dark_vessels.json: %s", exc)
        return {'anomalies': []}


def _anomaly_position(anomaly):
    """Extract a (lat, lon) for an anomaly, matching the dashboard's pan logic.

    Checks details.last_position, then details.center_position, then the last
    element of details.positions[]. Returns (None, None) for rendezvous and
    any other anomaly type without embedded coordinates.
    """
    details = (anomaly or {}).get('details') or {}
    last = details.get('last_position') or {}
    if last.get('lat') is not None and last.get('lon') is not None:
        return last['lat'], last['lon']
    center = details.get('center_position') or {}
    if center.get('lat') is not None and center.get('lon') is not None:
        return center['lat'], center['lon']
    positions = details.get('positions')
    if isinstance(positions, list) and positions:
        p = positions[-1]
        if isinstance(p, dict) and p.get('lat') is not None and p.get('lon') is not None:
            return p['lat'], p['lon']
    return None, None


def _sar_coverage_for(lat, lon, iso_ts, window_hours=SAR_TIME_WINDOW_HOURS):
    """Return up to 3 nearest Sentinel-1 passes that covered (lat, lon) within
    ±window_hours of iso_ts.

    Each entry: {tile_id, filename, datetime, bbox, delta_minutes}.
    Sorted closest-pass-first by abs(delta_minutes).
    """
    if lat is None or lon is None or not iso_ts:
        return []
    try:
        target = datetime.fromisoformat(iso_ts.replace('Z', '+00:00'))
    except Exception:
        return []
    metadata = _load_sar_metadata()
    hits = []
    for t in metadata.get('tiles', []) or []:
        bbox = t.get('bbox')
        if not bbox or len(bbox) != 4:
            continue
        min_lon, min_lat, max_lon, max_lat = bbox
        if not (min_lon <= lon <= max_lon and min_lat <= lat <= max_lat):
            continue
        try:
            tile_ts = datetime.fromisoformat((t.get('datetime') or '').replace('Z', '+00:00'))
        except Exception:
            continue
        delta_min = (tile_ts - target).total_seconds() / 60
        if abs(delta_min) > window_hours * 60:
            continue
        hits.append({
            'tile_id': t.get('id'),
            'filename': t.get('filename'),
            'datetime': t.get('datetime'),
            'bbox': bbox,
            'delta_minutes': round(delta_min, 0),
        })
    hits.sort(key=lambda h: abs(h['delta_minutes']))
    return hits[:3]


def load_vessel_data():
    """Load pre-processed vessel track data from GitHub Pages or local file.

    Returns a cached result if called within DATA_TTL_SECONDS of the last fetch.
    Upstream only publishes every ~5 min, so a 30-second TTL is plenty fresh
    and eliminates per-request GitHub Pages round-trips.

    Priority:
        1. Try GitHub Pages (for cloud deployment)
        2. Fallback to local bootstrap file data/vessel_tracks.json
    """
    import time as _time
    now = _time.monotonic()
    if _data_cache['result'] is not None and (now - _data_cache['fetched_at']) < DATA_TTL_SECONDS:
        return _data_cache['result']

    data = None
    source = None
    fetch_error = None

    # Primary: GitHub Pages
    try:
        logger.info("Fetching vessel data from GitHub Pages...")
        response = requests.get(GITHUB_PAGES_VESSELS_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        source = 'github-pages'
        logger.info("Fetched vessel data from GitHub Pages")
    except Exception as exc:  # noqa: BLE001
        fetch_error = str(exc)
        logger.warning("GitHub Pages fetch failed: %s — falling back to local file", fetch_error)

    # Fallback: local file, then committed fixture
    if data is None:
        # 1. Real collected data (gitignored; written by scripts/collect_ais.py)
        # 2. Committed dev fixture (checked in; small representative sample)
        candidates = [
            (DATA_DIR / 'vessel_tracks.json', 'local-file'),
            (DATA_DIR / 'fixtures' / 'vessel_tracks.json', 'local-fixture'),
        ]
        for path, label in candidates:
            if not path.exists():
                continue
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                source = label
                logger.warning("Using %s at %s", label, path)
                break
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to read %s: %s", path, exc)

    if data is None:
        return {
            'vessels': {},
            'stats': _empty_stats(
                stale_reason=f"GitHub Pages unreachable and no local bootstrap. Error: {fetch_error}",
            ),
        }

    vessel_tracks = data.get('vessels', {}) or {}
    raw_last_update = data.get('last_updated')

    counts = _classify_vessels(vessel_tracks)
    minutes, pretty_age, is_stale, stale_reason = _compute_freshness(raw_last_update)

    # If we fell back to a local file, surface that in the reason too
    if source in ('local-file', 'local-fixture'):
        is_stale = True
        label = 'fixture' if source == 'local-fixture' else 'local file'
        stale_reason = (
            f"Serving local {label} — GitHub Pages unreachable "
            f"({fetch_error or 'unknown error'}). Data age: {pretty_age}."
        )

    stats = {
        'total': len(vessel_tracks),
        **counts,
        'last_update': pretty_age,
        'raw_last_update': raw_last_update,
        'minutes_since_update': round(minutes, 1) if minutes is not None else None,
        'is_stale': bool(is_stale),
        'stale_reason': stale_reason or '',
        'source': source,
    }

    # Sanity check: buckets sum to total (assertion disabled in prod, logged instead)
    bucket_sum = sum(counts.values())
    if bucket_sum != stats['total']:
        logger.error(
            "Stats mismatch: bucket sum %d != total %d (counts=%s)",
            bucket_sum, stats['total'], counts,
        )

    result = {'vessels': vessel_tracks, 'stats': stats}
    _data_cache['result'] = result
    _data_cache['fetched_at'] = _time.monotonic()
    return result


@app.route('/')
def dashboard():
    """Serve the main dashboard page"""
    data = load_vessel_data()
    return render_template('dashboard.html', stats=data['stats'])


@app.route('/api/vessels')
@cors_enabled
def api_vessels():
    """API endpoint for vessel data"""
    data = load_vessel_data()
    response = make_response(jsonify(data))
    return no_cache(response)


@app.route('/api/map')
@cors_enabled
def api_map():
    """Generate and return map HTML, with in-memory caching keyed on snapshot ISO timestamp."""
    data = load_vessel_data()
    snapshot_ts = data['stats'].get('raw_last_update')

    # Cache hit: the snapshot timestamp matches the one we already rendered — return instantly.
    if _map_cache['html'] and _map_cache['raw_last_update'] == snapshot_ts:
        logger.info("Map cache HIT for snapshot %s", snapshot_ts)
        response = make_response(_map_cache['html'])
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return no_cache(response)

    if not data['vessels']:
        return "<div>No vessel data available</div>"

    # Cache miss: regenerate and store. Use get_root().render() for plain HTML
    # (not the Jupyter srcdoc wrapper from _repr_html_()) so postMessage from
    # the dashboard iframe can reach the map window.
    logger.info("Map cache MISS for snapshot %s — regenerating", snapshot_ts)
    map_obj = generate_focused_map(data['vessels'])
    html = map_obj.get_root().render()

    _map_cache['html'] = html
    _map_cache['raw_last_update'] = snapshot_ts

    response = make_response(html)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return no_cache(response)


@app.route('/api/anomalies')
@cors_enabled
def api_anomalies():
    """API endpoint for recent anomaly detections from GitHub Pages"""
    try:
        logger.info("Fetching anomaly data from GitHub Pages...")
        response = requests.get(GITHUB_PAGES_ANOMALIES_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Anomaly fetch from GitHub Pages failed: %s — using local fallback", exc)
        anomalies_file = DATA_DIR / 'anomalies' / 'anomalies.json'
        if not anomalies_file.exists():
            return no_cache(make_response(jsonify({'anomalies': [], 'total': 0})))
        with open(anomalies_file, 'r') as f:
            data = json.load(f)

    main_anomalies = data.get('anomalies', []) or []
    main_anomalies.sort(key=lambda x: x.get('detected_at', ''), reverse=True)
    main_anomalies = main_anomalies[:100]

    # Merge dark_vessel anomalies written by the daily satellite_monitor.yml
    # pipeline. Separate file avoids clobbering between the two workflows.
    # Dark vessels are naturally ~12-24h "older" than the continuous AIS stream
    # (daily cron vs 5-min cron), so we cap main_anomalies and dark_anomalies
    # INDEPENDENTLY before merging — otherwise dark vessels get crowded out.
    dark_data = _load_dark_vessels()
    dark_anomalies = dark_data.get('anomalies', []) or []
    dark_anomalies.sort(key=lambda x: x.get('detected_at', ''), reverse=True)
    dark_anomalies = dark_anomalies[:50]  # top 50 dark vessels by recency

    all_anomalies = main_anomalies + dark_anomalies
    all_anomalies.sort(key=lambda x: x.get('detected_at', ''), reverse=True)

    # Preload SAR metadata once for the whole batch (cached by mtime anyway)
    _load_sar_metadata()

    for anomaly in all_anomalies:
        if 'detected_at' in anomaly:
            try:
                dt = datetime.fromisoformat(anomaly['detected_at'].replace('Z', '+00:00'))
                anomaly['formatted_time'] = dt.strftime('%b %d, %H:%M')
            except Exception:
                anomaly['formatted_time'] = "Unknown"

        # Attach nearby Sentinel-1 passes if we have coverage for this vessel's
        # last known position within ±SAR_TIME_WINDOW_HOURS of the anomaly time.
        # Rendezvous and other position-less anomalies get an empty list.
        lat, lon = _anomaly_position(anomaly)
        anomaly['sar_coverage'] = _sar_coverage_for(
            lat, lon,
            anomaly.get('detected_at') or (anomaly.get('details') or {}).get('gap_start'),
        )

    response = make_response(jsonify({'anomalies': all_anomalies, 'total': len(all_anomalies)}))
    return no_cache(response)


@app.route('/api/satellite-tiles')
@cors_enabled
def api_satellite_tiles():
    """Return the current SAR tile history for the dashboard satellite viewer.

    Each tile entry includes a `thumbnail_url` field (served by this Flask app)
    so the frontend can render it directly without needing to know the on-disk
    layout. Tiles are returned newest-first.
    """
    metadata = _load_sar_metadata()
    tiles_out = []
    for t in metadata.get('tiles', []) or []:
        thumb = t.get('thumbnail')
        tiles_out.append({
            'id': t.get('id'),
            'filename': t.get('filename'),
            'datetime': t.get('datetime'),
            'bbox': t.get('bbox'),
            'instrument_mode': t.get('instrument_mode'),
            'zone': t.get('zone'),
            'thumbnail_url': f'/satellite-thumbnails/{thumb}' if thumb else None,
        })
    body = {
        'last_updated': metadata.get('last_updated'),
        'history_window_days': metadata.get('history_window_days'),
        'count': len(tiles_out),
        'tiles': tiles_out,
    }
    return no_cache(make_response(jsonify(body)))


@app.route('/analysis-view')
def analysis_view():
    """Serve the standalone full-screen SAR Analysis View page.

    The page fetches /api/satellite-tiles and /api/vessels on load and
    renders SAR tiles as Leaflet ImageOverlays with AIS markers overlaid
    (filtered to ±60 min of any visible tile's acquisition time).
    """
    return render_template('analysis.html')


@app.route('/satellite-thumbnails/<path:filename>')
def satellite_thumbnail(filename):
    """Serve a generated SAR thumbnail PNG from data/satellite_imagery/thumbnails/.

    These PNGs are committed to the repo by the satellite_monitor.yml workflow
    after each collection run, so they're always present wherever the Flask
    app is deployed. Served with a short browser cache since filenames are
    content-addressed by timestamp + tile-id.
    """
    thumbnails_dir = DATA_DIR / 'satellite_imagery' / 'thumbnails'
    # send_from_directory prevents path traversal (`..` etc.)
    if not (thumbnails_dir / filename).exists():
        abort(404)
    response = make_response(send_from_directory(str(thumbnails_dir), filename))
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response


@app.route('/health')
def health():
    """Health check endpoint. Returns 503 if vessel data is stale."""
    data = load_vessel_data()
    stats = data['stats']
    body = {
        'service': 'Arctic Shadow Tracker',
        'is_stale': stats.get('is_stale', True),
        'minutes_since_update': stats.get('minutes_since_update'),
        'last_update': stats.get('last_update'),
        'source': stats.get('source'),
    }
    if stats.get('is_stale'):
        body['status'] = 'stale'
        body['reason'] = stats.get('stale_reason', '')
        return jsonify(body), 503
    body['status'] = 'healthy'
    return jsonify(body), 200


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    logger.info("Starting Arctic Shadow Tracker Dashboard on port %d", port)
    app.run(debug=False, host='0.0.0.0', port=port)
