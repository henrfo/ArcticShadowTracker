#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Real-Time Dashboard
Simple Flask server with auto-refreshing vessel map
"""

from flask import Flask, render_template, jsonify
from pathlib import Path
import json
import sys
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

def load_vessel_data():
    """Load pre-processed vessel track data from vessel_tracks.json

    This file is updated by GitHub Actions every 30 minutes and contains
    fully processed three-tier tracks with shadow fleet classification.
    """
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
                'other': 0,
                'last_update': None
            }
        }

    # Load pre-processed vessel tracks (GitHub Actions already ran process_vessel_tracks)
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

    other_count = sum(1 for v in vessel_tracks.values()
                     if v['country'] not in ['Russia', 'China', 'Norway']
                     and not v.get('is_shadow_fleet', False)
                     and not v.get('is_suspected_shadow', False))

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
            'other': other_count,
            'last_update': last_update
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

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    print("Starting Arctic Shadow Tracker Dashboard...")
    print(f"Dashboard will be available at: http://localhost:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)
