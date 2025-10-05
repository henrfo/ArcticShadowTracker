#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Real-Time Dashboard
Simple Flask server with auto-refreshing vessel map
"""

from flask import Flask, render_template, jsonify
from pathlib import Path
import json
import sys
import requests
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.track_manager import process_vessel_tracks
from src.map_generator import generate_focused_map

app = Flask(__name__)

# Data directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
SNAPSHOTS_DIR = DATA_DIR / 'snapshots'
OUTPUTS_DIR = BASE_DIR / 'outputs'

# GitHub Pages URL for vessel data (updated every 5 minutes by GitHub Actions)
GITHUB_PAGES_DATA_URL = "https://henrfo.github.io/ArcticShadowTracker/vessel_tracks.json"

def load_vessel_data():
    """Load pre-processed vessel track data from GitHub Pages or local file

    This file is updated by GitHub Actions every 5 minutes and contains
    fully processed three-tier tracks with shadow fleet classification.

    Priority:
    1. Try GitHub Pages (for cloud deployment)
    2. Fallback to local file (for development)
    """

    # Try fetching from GitHub Pages first (cloud deployment)
    try:
        print(f"Fetching vessel data from GitHub Pages...")
        response = requests.get(GITHUB_PAGES_DATA_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"Successfully fetched data from GitHub Pages")
    except Exception as e:
        # Fallback to local file (development mode)
        print(f"GitHub Pages fetch failed: {e}, using local file")
        tracks_file = DATA_DIR / 'vessel_tracks.json'

        if not tracks_file.exists():
            return {
                'vessels': {},
                'stats': {
                    'total': 0,
                    'russian': 0,
                    'chinese': 0,
                    'norwegian': 0,
                    'norwegian_military': 0,
                    'shadow_fleet': 0,
                    'suspected_shadow': 0,
                    'buoy': 0,
                    'other': 0,
                    'last_update': 'No data'
                }
            }

        with open(tracks_file, 'r') as f:
            data = json.load(f)

    vessel_tracks = data.get('vessels', {})
    last_update = data.get('last_updated')

    # Calculate stats (same logic as before)
    russian_count = sum(1 for v in vessel_tracks.values() if v['country'] == 'Russia')
    chinese_count = sum(1 for v in vessel_tracks.values() if v['country'] == 'China')

    norwegian_military_count = sum(1 for v in vessel_tracks.values()
                                   if v['country'] == 'Norway' and
                                   ('military' in v['ship_type'].lower() or
                                    'law enforcement' in v['ship_type'].lower()))

    norwegian_count = sum(1 for v in vessel_tracks.values()
                         if v['country'] == 'Norway' and
                         'military' not in v['ship_type'].lower() and
                         'law enforcement' not in v['ship_type'].lower())

    shadow_fleet_count = sum(1 for v in vessel_tracks.values() if v.get('is_shadow_fleet', False))

    suspected_shadow_count = sum(1 for v in vessel_tracks.values()
                                if v.get('is_suspected_shadow', False))

    buoy_count = sum(1 for v in vessel_tracks.values() if v.get('is_buoy', False))

    other_count = sum(1 for v in vessel_tracks.values()
                     if v['country'] not in ['Russia', 'China', 'Norway']
                     and not v.get('is_shadow_fleet', False)
                     and not v.get('is_suspected_shadow', False)
                     and not v.get('is_buoy', False))

    # Format timestamp as "Xh Ym ago" instead of raw ISO format
    if last_update:
        try:
            # Parse ISO timestamp
            dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))

            # Calculate time ago
            now = datetime.now(timezone.utc)
            time_diff = now - dt.replace(tzinfo=timezone.utc)
            hours_ago = int(time_diff.total_seconds() / 3600)
            mins_ago = int((time_diff.total_seconds() % 3600) / 60)

            if hours_ago > 24:
                days_ago = hours_ago // 24
                formatted_update = f"{days_ago}d {hours_ago % 24}h ago"
            elif hours_ago > 0:
                formatted_update = f"{hours_ago}h {mins_ago}m ago"
            else:
                formatted_update = f"{mins_ago}m ago"
        except Exception:
            formatted_update = "Unknown"
    else:
        formatted_update = "No data"

    return {
        'vessels': vessel_tracks,
        'stats': {
            'total': len(vessel_tracks),
            'russian': russian_count,
            'chinese': chinese_count,
            'norwegian': norwegian_count,
            'norwegian_military': norwegian_military_count,
            'shadow_fleet': shadow_fleet_count,
            'suspected_shadow': suspected_shadow_count,
            'buoy': buoy_count,
            'other': other_count,
            'last_update': formatted_update  # Now shows "4h 23m ago" instead of ISO timestamp
        }
    }

@app.route('/')
def dashboard():
    """Serve the main dashboard page"""
    data = load_vessel_data()
    return render_template('dashboard.html',
                         stats=data['stats'])

@app.route('/api/vessels')
def api_vessels():
    """API endpoint for vessel data"""
    data = load_vessel_data()
    return jsonify(data)

@app.route('/api/map')
def api_map():
    """Generate and return map HTML"""
    data = load_vessel_data()

    if not data['vessels']:
        return "<div>No vessel data available</div>"

    # Generate map using existing map_generator
    map_obj = generate_focused_map(data['vessels'])

    # Return map HTML
    return map_obj._repr_html_()

@app.route('/health')
def health():
    """Health check endpoint for Fly.io"""
    return jsonify({'status': 'healthy', 'service': 'Arctic Shadow Tracker'}), 200

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    print("Starting Arctic Shadow Tracker Dashboard...")
    print(f"Dashboard will be available at: http://localhost:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)
