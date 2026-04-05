#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Real-Time Dashboard
Simple Flask server with auto-refreshing vessel map
"""

from flask import Flask, render_template, jsonify, make_response
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


def load_vessel_data():
    """Load pre-processed vessel track data from GitHub Pages or local file.

    Priority:
        1. Try GitHub Pages (for cloud deployment)
        2. Fallback to local bootstrap file data/vessel_tracks.json
    """
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

    return {'vessels': vessel_tracks, 'stats': stats}


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
    """Generate and return map HTML"""
    data = load_vessel_data()

    if not data['vessels']:
        return "<div>No vessel data available</div>"

    map_obj = generate_focused_map(data['vessels'])
    # Use get_root().render() to produce a plain HTML document.
    # _repr_html_() wraps the map in a Jupyter-style srcdoc iframe, which creates
    # a nested-iframe situation where postMessage from the dashboard can't reach
    # the actual map window. .render() returns the raw HTML directly.
    response = make_response(map_obj.get_root().render())
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

    all_anomalies = data.get('anomalies', []) or []
    all_anomalies.sort(key=lambda x: x.get('detected_at', ''), reverse=True)
    all_anomalies = all_anomalies[:100]

    for anomaly in all_anomalies:
        if 'detected_at' in anomaly:
            try:
                dt = datetime.fromisoformat(anomaly['detected_at'].replace('Z', '+00:00'))
                anomaly['formatted_time'] = dt.strftime('%b %d, %H:%M')
            except Exception:
                anomaly['formatted_time'] = "Unknown"

    response = make_response(jsonify({'anomalies': all_anomalies, 'total': len(all_anomalies)}))
    return no_cache(response)


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
