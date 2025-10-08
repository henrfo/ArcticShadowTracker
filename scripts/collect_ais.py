#!/usr/bin/env python3
"""
Arctic AIS Collector - GitHub Actions Compatible
Collects Arctic vessel data every 30 minutes for shadow fleet detection
Implements three-tier historical tracking
"""

import os
import sys
import json
import requests
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import reference data
from src.mmsi_country_reference import MMSI_COUNTRY_MAP
from src.ais_ship_types import get_ship_type
from src.track_manager import process_vessel_tracks
from src.map_generator import generate_focused_map

# Norway coverage (full country + Svalbard)
ARCTIC_REGION = {
    'lat_min': 57.0,   # Southern Norway coast
    'lat_max': 82.0,   # All of Svalbard
    'lon_min': 4.0,    # Western Norway coast
    'lon_max': 32.0    # Eastern Norway/Russian border
}

# Data directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
SNAPSHOTS_DIR = DATA_DIR / 'snapshots'
OUTPUTS_DIR = BASE_DIR / 'outputs'

# Ensure directories exist
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

def load_credentials():
    """Load API credentials from environment variables or config.yaml"""
    # GitHub Actions: use environment variables
    client_secret = os.getenv('BARENTSWATCH_CLIENT_SECRET')
    if client_secret:
        print("Using credentials from environment variables")
        return {
            'client_id': 'henrikformoe@gmail.com:ArcticShadowTrackerAIS',
            'client_secret': client_secret
        }

    # Local development: use config.yaml
    config_path = BASE_DIR / 'config.yaml'
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            print("Using credentials from config.yaml")
            return {
                'client_id': config['barentswatch']['client_id'],
                'client_secret': config['barentswatch']['client_secret']
            }
    except FileNotFoundError:
        raise Exception("No config.yaml found and BARENTSWATCH_CLIENT_SECRET not set")

def get_barentswatch_token(client_id, client_secret):
    """Get access token for BarentsWatch API"""
    response = requests.post(
        'https://id.barentswatch.no/connect/token',
        data={
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'ais',
            'grant_type': 'client_credentials'
        },
        timeout=30
    )

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f"Failed to get token: {response.text}")

def fetch_ais_data(token):
    """Fetch AIS data from BarentsWatch and filter for Arctic vessels"""
    print("Fetching AIS data from BarentsWatch...")

    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    url = "https://live.ais.barentswatch.no/v1/latest/combined"

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    all_vessels = response.json()
    print(f"  Total vessels received: {len(all_vessels)}")

    # Filter for Arctic vessels (all countries)
    target_vessels = []
    collection_time = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    for v in all_vessels:
        lat = v.get('latitude', 0)
        lon = v.get('longitude', 0)

        # Arctic region filter
        if not (ARCTIC_REGION['lat_min'] <= lat <= ARCTIC_REGION['lat_max'] and
                ARCTIC_REGION['lon_min'] <= lon <= ARCTIC_REGION['lon_max']):
            continue

        mmsi = str(v.get('mmsi', ''))
        mmsi_prefix = mmsi[:3]
        country = MMSI_COUNTRY_MAP.get(mmsi_prefix, 'Unknown')

        # Use vessel's individual AIS transmission time (msgtime from BarentsWatch API)
        # Format: "2023-04-21T01:40:34.8259595+00:00" -> convert to ISO with Z
        vessel_msgtime = v.get('msgtime')
        if vessel_msgtime:
            # Parse and convert to UTC with Z suffix
            try:
                dt = datetime.fromisoformat(vessel_msgtime.replace('+00:00', ''))
                vessel_timestamp = dt.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
            except (ValueError, AttributeError):
                vessel_timestamp = collection_time  # Fallback to collection time
        else:
            vessel_timestamp = collection_time  # Fallback if msgtime missing

        # Collect ALL Arctic vessels (no country filter)
        target_vessels.append({
            'timestamp': vessel_timestamp,  # Individual vessel AIS transmission time
            'mmsi': mmsi,
            'name': v.get('name', 'Unknown'),
            'country': country,
            'latitude': lat,
            'longitude': lon,
            'speed': v.get('speedOverGround') or 0,
            'course': v.get('courseOverGround') or 0,
            'ship_type': get_ship_type(v.get('shipType', 0)),
            'ship_type_code': v.get('shipType', 0)
        })

    russian_count = sum(1 for v in target_vessels if v['country'] == 'Russia')
    chinese_count = sum(1 for v in target_vessels if v['country'] == 'China')
    norwegian_count = sum(1 for v in target_vessels if v['country'] == 'Norway')
    other_count = len(target_vessels) - russian_count - chinese_count - norwegian_count

    print(f"  Found {len(target_vessels)} vessels in Arctic")
    print(f"    - Russian: {russian_count}")
    print(f"    - Chinese: {chinese_count}")
    print(f"    - Norwegian: {norwegian_count}")
    print(f"    - Other: {other_count}")

    return target_vessels, collection_time

def save_snapshot(vessels, timestamp):
    """Save current snapshot to data/snapshots/"""
    timestamp_str = datetime.fromisoformat(timestamp.replace('Z', '')).strftime('%Y%m%d_%H%M')
    snapshot_file = SNAPSHOTS_DIR / f"{timestamp_str}.json"

    # Count vessels by country
    country_counts = {}
    for v in vessels:
        country = v['country']
        country_counts[country] = country_counts.get(country, 0) + 1

    snapshot = {
        'timestamp': timestamp,
        'vessel_count': len(vessels),
        'by_country': country_counts,
        'vessels': vessels
    }

    with open(snapshot_file, 'w') as f:
        json.dump(snapshot, f, indent=2)

    print(f"Snapshot saved: {snapshot_file.name}")
    return snapshot_file

def load_recent_snapshots(hours=168):  # 7 days = 168 hours
    """Load all snapshots from the last N hours"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    snapshots = []

    for snapshot_file in sorted(SNAPSHOTS_DIR.glob('*.json')):
        # Parse timestamp from filename: YYYYMMDD_HHMM.json
        try:
            timestamp_str = snapshot_file.stem  # Remove .json
            snapshot_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M').replace(tzinfo=timezone.utc)

            if snapshot_time >= cutoff:
                with open(snapshot_file, 'r') as f:
                    snapshots.append(json.load(f))
        except (ValueError, json.JSONDecodeError) as e:
            print(f"Warning: Skipping invalid snapshot file: {snapshot_file.name} ({e})")
            continue

    print(f"Loaded {len(snapshots)} snapshots from last {hours} hours")
    return snapshots

def cleanup_old_snapshots(days=7):
    """Delete snapshot files older than N days"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted_count = 0

    for snapshot_file in SNAPSHOTS_DIR.glob('*.json'):
        try:
            timestamp_str = snapshot_file.stem
            snapshot_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M').replace(tzinfo=timezone.utc)

            if snapshot_time < cutoff:
                snapshot_file.unlink()
                deleted_count += 1
        except (ValueError, OSError):
            continue

    if deleted_count > 0:
        print(f"Cleaned up {deleted_count} old snapshots (>{days} days)")

def save_vessel_tracks(tracks):
    """Save processed vessel tracks to data/vessel_tracks.json"""
    tracks_file = DATA_DIR / 'vessel_tracks.json'

    output = {
        'last_updated': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'vessel_count': len(tracks),
        'vessels': tracks
    }

    with open(tracks_file, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Vessel tracks saved: {tracks_file.name}")

def main():
    """Main collection pipeline"""
    print("=" * 60)
    print("Arctic AIS Collector - Three-Tier Intelligence System")
    print("=" * 60)
    print()

    try:
        # 1. Get credentials and token
        credentials = load_credentials()
        token = get_barentswatch_token(credentials['client_id'], credentials['client_secret'])
        print("Got BarentsWatch API token")
        print()

        # 2. Fetch current AIS data
        vessels, timestamp = fetch_ais_data(token)
        print()

        # 3. Save snapshot
        save_snapshot(vessels, timestamp)
        print()

        # 4. Load recent snapshots (last 7 days)
        snapshots = load_recent_snapshots(hours=168)
        print()

        # 5. Build three-tier tracks
        print("Processing three-tier vessel tracks...")
        vessel_tracks = process_vessel_tracks(snapshots)
        print(f"  Processed {len(vessel_tracks)} vessel track histories")
        print()

        # 6. Save processed tracks
        save_vessel_tracks(vessel_tracks)
        print()

        # 7. Generate focused map with tracks
        print("Generating interactive map with focus mode...")
        map_obj = generate_focused_map(vessel_tracks)

        # Save to outputs/index.html (GitHub Pages)
        map_file = OUTPUTS_DIR / 'index.html'
        map_obj.save(str(map_file))
        print(f"  Map saved: {map_file}")
        print()

        # 8. Cleanup old snapshots
        cleanup_old_snapshots(days=7)
        print()

        print("=" * 60)
        print("Collection complete!")
        print(f"  Vessels tracked: {len(vessel_tracks)}")
        print(f"  Snapshots available: {len(snapshots)}")
        print(f"  Dashboard: {map_file}")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        raise

if __name__ == "__main__":
    main()
