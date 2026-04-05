#!/usr/bin/env python3
"""
AIS Anomaly Detection - Arctic Shadow Tracker
Detects suspicious vessel behavior from AIS snapshots

Phase 1: Core detection (gaps, impossible speeds, loitering, rendezvous)
Analyzes 277 monitored vessels (Russia, China, Shadow Fleet)
"""

import json
import math
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.track_manager import SHADOW_FLEET_FLAGS

# =============================================================================
# CONFIGURATION
# =============================================================================

# Data directories
BASE_DIR = Path(__file__).parent.parent.parent
SNAPSHOTS_DIR = BASE_DIR / 'data' / 'snapshots'
ANOMALIES_DIR = BASE_DIR / 'data' / 'anomalies'
ANOMALIES_DIR.mkdir(parents=True, exist_ok=True)

# Monitored vessel categories (277 vessels total)
MONITORED_COUNTRIES = ['Russia', 'China']

# Detection thresholds
SPEED_LIMITS = {
    'Cargo': 30,
    'Tanker': 20,
    'Fishing': 15,
    'Passenger': 35,
    'default': 40
}
MAX_TRANSMISSION_GAP_MINUTES = 30
LOITERING_RADIUS_KM = 5
LOITERING_DURATION_HOURS = 6
RENDEZVOUS_PROXIMITY_KM = 1

# Norwegian EEZ boundary (simple bounding box for "near border" detection)
NORWEGIAN_EEZ_BOUNDS = {
    'lat_min': 56.0,
    'lat_max': 81.0,
    'lon_min': -5.0,
    'lon_max': 35.0
}
BORDER_PROXIMITY_KM = 50  # Flag gaps within 50km of border

# Empirical coverage-edge map — learned from historical anomaly positions by
# scripts/analyze_coverage_boundary.py. Gaps whose last_position falls inside
# one of these cells are reclassified as 'left_coverage' (expected signal loss
# at the edge of BarentsWatch coverage) rather than 'transmission_gap'.
COVERAGE_EDGE_FILE = BASE_DIR / 'data' / 'coverage_edge_cells.json'


def _load_coverage_edge_cells():
    """Load the empirical coverage-edge cells once, returning (set, cell_size).

    Returns (empty_set, default_size) if the file is missing — the detector
    then falls through to the old behaviour (all gaps are transmission_gap).
    """
    try:
        with open(COVERAGE_EDGE_FILE, 'r') as f:
            payload = json.load(f)
        cells = {tuple(c) for c in payload.get('edge_cells', [])}
        cell_size = float(payload.get('cell_size_deg', 0.1))
        return cells, cell_size
    except FileNotFoundError:
        print(f"[coverage-edge] {COVERAGE_EDGE_FILE} not found — no reclassification")
        return set(), 0.1
    except Exception as exc:  # noqa: BLE001
        print(f"[coverage-edge] failed to load edge cells: {exc}")
        return set(), 0.1


_COVERAGE_EDGE_CELLS, _COVERAGE_CELL_SIZE = _load_coverage_edge_cells()


def _is_coverage_edge(lat, lon):
    """Return True if (lat, lon) falls inside a known coverage-edge cell."""
    if not _COVERAGE_EDGE_CELLS:
        return False
    size = _COVERAGE_CELL_SIZE
    key = (
        round((lat // size) * size, 4),
        round((lon // size) * size, 4),
    )
    return key in _COVERAGE_EDGE_CELLS

# Corrupt MMSI patterns
INVALID_MMSI_PATTERNS = [
    '000000000', '111111111', '123456789', '999999999',
    '000000001', '111111112'
]

# =============================================================================
# DATA QUALITY & VALIDATION
# =============================================================================

def is_valid_position(lat, lon, mmsi):
    """
    Validate AIS position data

    Returns:
        bool: True if position is valid
    """
    # Check coordinate ranges
    if lat > 90 or lat < -90 or lon > 180 or lon < -180:
        return False

    # Filter default/invalid positions
    if (lat, lon) == (0, 0) or (lat, lon) == (91, 181):
        return False

    # Check for corrupt MMSI
    mmsi_str = str(mmsi)
    if mmsi_str in INVALID_MMSI_PATTERNS:
        return False

    return True

def is_monitored_vessel(vessel):
    """Check if vessel should be monitored for anomalies"""
    country = vessel.get('country', '')

    # Monitor Russia/China vessels
    if country in MONITORED_COUNTRIES:
        return True

    # Monitor shadow fleet flags
    if country in SHADOW_FLEET_FLAGS:
        return True

    return False

# =============================================================================
# DISTANCE & SPEED CALCULATIONS
# =============================================================================

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate great circle distance between two points in kilometers

    Args:
        lat1, lon1: First position (degrees)
        lat2, lon2: Second position (degrees)

    Returns:
        float: Distance in kilometers
    """
    R = 6371  # Earth radius in km

    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))

    return R * c

def calculate_speed_knots(pos1, pos2):
    """
    Calculate speed between two positions in knots

    Args:
        pos1, pos2: Position dicts with 'lat', 'lon', 'timestamp'

    Returns:
        float: Speed in knots, or None if invalid
    """
    # Calculate distance
    distance_km = haversine_distance(
        pos1['lat'], pos1['lon'],
        pos2['lat'], pos2['lon']
    )

    # Calculate time delta
    time1 = datetime.fromisoformat(pos1['timestamp'].replace('Z', ''))
    time2 = datetime.fromisoformat(pos2['timestamp'].replace('Z', ''))
    time_delta_hours = abs((time2 - time1).total_seconds() / 3600)

    if time_delta_hours == 0:
        return None

    # Speed in knots (1 knot = 1.852 km/h)
    speed_kmh = distance_km / time_delta_hours
    speed_knots = speed_kmh / 1.852

    return speed_knots

def is_near_border(lat, lon):
    """
    Check if position is near Norwegian EEZ boundary

    Returns:
        bool: True if within BORDER_PROXIMITY_KM of boundary
    """
    # Simple bounding box check (will upgrade to shapefile later)
    bounds = NORWEGIAN_EEZ_BOUNDS

    # Calculate distance to nearest boundary edge
    dist_to_north = abs(lat - bounds['lat_max'])
    dist_to_south = abs(lat - bounds['lat_min'])
    dist_to_east = abs(lon - bounds['lon_max'])
    dist_to_west = abs(lon - bounds['lon_min'])

    # Convert to km (rough approximation: 1 degree ≈ 111km)
    min_dist_km = min(dist_to_north, dist_to_south, dist_to_east, dist_to_west) * 111

    return min_dist_km <= BORDER_PROXIMITY_KM

# =============================================================================
# DATA LOADING
# =============================================================================

def load_recent_snapshots(days_back=7):
    """
    Load AIS snapshots from last N days, filtered to monitored vessels

    Returns:
        list: Snapshots with only monitored vessels
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    snapshots = []

    for snapshot_file in sorted(SNAPSHOTS_DIR.glob('*.json')):
        try:
            # Parse timestamp from filename
            timestamp_str = snapshot_file.stem
            snapshot_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M').replace(tzinfo=timezone.utc)

            if snapshot_time >= cutoff:
                with open(snapshot_file, 'r') as f:
                    snapshot = json.load(f)

                    # Filter to monitored vessels only
                    monitored_vessels = [
                        v for v in snapshot.get('vessels', [])
                        if is_monitored_vessel(v) and
                           is_valid_position(v.get('latitude', 0), v.get('longitude', 0), v.get('mmsi', ''))
                    ]

                    if monitored_vessels:
                        snapshot['vessels'] = monitored_vessels
                        snapshots.append(snapshot)
        except (ValueError, json.JSONDecodeError):
            continue

    return snapshots

def group_by_vessel(snapshots):
    """
    Group positions by MMSI for per-vessel analysis

    Returns:
        dict: {mmsi: {'info': {...}, 'positions': [...]}}
    """
    vessels = defaultdict(lambda: {'info': None, 'positions': []})

    for snapshot in snapshots:
        for vessel in snapshot['vessels']:
            mmsi = vessel['mmsi']

            # Store vessel metadata (from first encounter)
            if vessels[mmsi]['info'] is None:
                vessels[mmsi]['info'] = {
                    'mmsi': mmsi,
                    'name': vessel.get('name', 'Unknown'),
                    'country': vessel.get('country', 'Unknown'),
                    'ship_type': vessel.get('ship_type', 'Unknown')
                }

            # Add position
            vessels[mmsi]['positions'].append({
                'timestamp': vessel.get('timestamp', snapshot['timestamp']),
                'lat': vessel['latitude'],
                'lon': vessel['longitude'],
                'speed': vessel.get('speed', 0),
                'course': vessel.get('course', 0)
            })

    # Sort positions chronologically
    for mmsi in vessels:
        vessels[mmsi]['positions'].sort(key=lambda p: p['timestamp'])

    return dict(vessels)

# =============================================================================
# ANOMALY DETECTION ALGORITHMS
# =============================================================================

def detect_transmission_gaps(vessels_data):
    """
    Detect suspicious AIS transmission gaps (>30 minutes)

    Args:
        vessels_data: Dict from group_by_vessel()

    Returns:
        list: Anomaly records
    """
    anomalies = []

    for mmsi, data in vessels_data.items():
        positions = data['positions']
        vessel_info = data['info']

        if len(positions) < 2:
            continue

        for i in range(1, len(positions)):
            prev_pos = positions[i-1]
            curr_pos = positions[i]

            # Calculate time gap
            time1 = datetime.fromisoformat(prev_pos['timestamp'].replace('Z', ''))
            time2 = datetime.fromisoformat(curr_pos['timestamp'].replace('Z', ''))
            gap_minutes = (time2 - time1).total_seconds() / 60

            if gap_minutes > MAX_TRANSMISSION_GAP_MINUTES:
                last_lat = prev_pos['lat']
                last_lon = prev_pos['lon']
                near_border = is_near_border(last_lat, last_lon)

                # Empirical coverage-edge check: if the vessel's last seen
                # position falls in a cell where gaps are known to cluster
                # (learned from historical data by analyze_coverage_boundary.py),
                # this is an expected boundary exit, not a suspicious signal loss.
                in_coverage_edge = _is_coverage_edge(last_lat, last_lon)

                if in_coverage_edge:
                    anomaly_type = 'left_coverage'
                    severity = 'low'  # informational; hidden by default in the dashboard
                else:
                    anomaly_type = 'transmission_gap'
                    # Severity is primarily a function of gap duration; near_border
                    # remains as a tiebreaker that can still escalate genuine gaps
                    # in real border zones (not coverage-edge cells).
                    if gap_minutes > 180:  # >3 hours
                        severity = 'critical' if near_border else 'high'
                    elif gap_minutes > 60:  # >1 hour
                        severity = 'high' if near_border else 'medium'
                    else:
                        severity = 'medium' if near_border else 'low'

                anomalies.append({
                    'mmsi': mmsi,
                    'vessel_name': vessel_info['name'],
                    'country': vessel_info['country'],
                    'anomaly_type': anomaly_type,
                    'severity': severity,
                    'detected_at': curr_pos['timestamp'],
                    'details': {
                        'gap_duration_minutes': round(gap_minutes, 1),
                        'gap_start': prev_pos['timestamp'],
                        'gap_end': curr_pos['timestamp'],
                        'last_position': {
                            'lat': round(last_lat, 4),
                            'lon': round(last_lon, 4),
                        },
                        'near_border': near_border,
                        'coverage_edge': in_coverage_edge,
                    }
                })

    return anomalies

def detect_impossible_speeds(vessels_data):
    """
    Detect physically impossible vessel speeds (vessel-type specific)

    Args:
        vessels_data: Dict from group_by_vessel()

    Returns:
        list: Anomaly records
    """
    anomalies = []

    for mmsi, data in vessels_data.items():
        positions = data['positions']
        vessel_info = data['info']

        # Get speed limit for vessel type
        ship_type = vessel_info['ship_type']
        max_speed = SPEED_LIMITS.get(ship_type.split()[0], SPEED_LIMITS['default'])

        if len(positions) < 2:
            continue

        for i in range(1, len(positions)):
            prev_pos = positions[i-1]
            curr_pos = positions[i]

            # Calculate speed
            speed = calculate_speed_knots(prev_pos, curr_pos)

            if speed and speed > max_speed:
                # Determine severity
                speed_excess = speed - max_speed
                if speed_excess > 50:
                    severity = 'critical'
                elif speed_excess > 20:
                    severity = 'high'
                elif speed_excess > 10:
                    severity = 'medium'
                else:
                    severity = 'low'

                anomalies.append({
                    'mmsi': mmsi,
                    'vessel_name': vessel_info['name'],
                    'country': vessel_info['country'],
                    'anomaly_type': 'impossible_speed',
                    'severity': severity,
                    'detected_at': curr_pos['timestamp'],
                    'details': {
                        'calculated_speed_knots': round(speed, 1),
                        'max_allowed_knots': max_speed,
                        'vessel_type': ship_type,
                        'distance_km': round(haversine_distance(
                            prev_pos['lat'], prev_pos['lon'],
                            curr_pos['lat'], curr_pos['lon']
                        ), 2),
                        'time_delta_minutes': round((
                            datetime.fromisoformat(curr_pos['timestamp'].replace('Z', '')) -
                            datetime.fromisoformat(prev_pos['timestamp'].replace('Z', ''))
                        ).total_seconds() / 60, 1),
                        'positions': [
                            {
                                'lat': round(prev_pos['lat'], 4),
                                'lon': round(prev_pos['lon'], 4),
                                'time': prev_pos['timestamp']
                            },
                            {
                                'lat': round(curr_pos['lat'], 4),
                                'lon': round(curr_pos['lon'], 4),
                                'time': curr_pos['timestamp']
                            }
                        ]
                    }
                })

    return anomalies

def detect_loitering(vessels_data):
    """
    Detect vessels loitering in one area (within 5km for >6 hours)

    Args:
        vessels_data: Dict from group_by_vessel()

    Returns:
        list: Anomaly records
    """
    anomalies = []

    for mmsi, data in vessels_data.items():
        positions = data['positions']
        vessel_info = data['info']

        if len(positions) < 10:  # Need enough points to detect loitering
            continue

        # Check each position as potential loiter center
        for i in range(len(positions) - 5):
            center_pos = positions[i]
            center_time = datetime.fromisoformat(center_pos['timestamp'].replace('Z', ''))

            # Count positions within radius and timeframe
            loiter_positions = []
            for j in range(i, len(positions)):
                pos = positions[j]
                pos_time = datetime.fromisoformat(pos['timestamp'].replace('Z', ''))

                # Check if within timeframe
                if (pos_time - center_time).total_seconds() / 3600 > LOITERING_DURATION_HOURS:
                    break

                # Check if within radius
                distance = haversine_distance(
                    center_pos['lat'], center_pos['lon'],
                    pos['lat'], pos['lon']
                )

                if distance <= LOITERING_RADIUS_KM:
                    loiter_positions.append(pos)

            # If loitered for minimum duration, flag it
            if len(loiter_positions) >= 10:  # Roughly 5 hours at 30-min intervals
                duration_hours = (
                    datetime.fromisoformat(loiter_positions[-1]['timestamp'].replace('Z', '')) -
                    datetime.fromisoformat(loiter_positions[0]['timestamp'].replace('Z', ''))
                ).total_seconds() / 3600

                if duration_hours >= LOITERING_DURATION_HOURS:
                    anomalies.append({
                        'mmsi': mmsi,
                        'vessel_name': vessel_info['name'],
                        'country': vessel_info['country'],
                        'anomaly_type': 'loitering',
                        'severity': 'medium',
                        'detected_at': loiter_positions[-1]['timestamp'],
                        'details': {
                            'duration_hours': round(duration_hours, 1),
                            'radius_km': LOITERING_RADIUS_KM,
                            'center_position': {
                                'lat': round(center_pos['lat'], 4),
                                'lon': round(center_pos['lon'], 4)
                            },
                            'start_time': loiter_positions[0]['timestamp'],
                            'end_time': loiter_positions[-1]['timestamp'],
                            'position_count': len(loiter_positions)
                        }
                    })
                    break  # Only report first loitering incident per vessel

    return anomalies

def detect_rendezvous(vessels_data):
    """
    Detect vessels meeting mid-ocean (within 1km proximity)

    Args:
        vessels_data: Dict from group_by_vessel()

    Returns:
        list: Anomaly records
    """
    anomalies = []
    vessel_list = list(vessels_data.items())

    # Compare all vessel pairs (277 vessels = 38k comparisons)
    for i in range(len(vessel_list)):
        for j in range(i + 1, len(vessel_list)):
            mmsi1, data1 = vessel_list[i]
            mmsi2, data2 = vessel_list[j]

            # Find overlapping timestamps
            times1 = {pos['timestamp']: pos for pos in data1['positions']}
            times2 = {pos['timestamp']: pos for pos in data2['positions']}

            common_times = set(times1.keys()) & set(times2.keys())

            for timestamp in common_times:
                pos1 = times1[timestamp]
                pos2 = times2[timestamp]

                distance = haversine_distance(
                    pos1['lat'], pos1['lon'],
                    pos2['lat'], pos2['lon']
                )

                if distance <= RENDEZVOUS_PROXIMITY_KM:
                    anomalies.append({
                        'mmsi': f"{mmsi1},{mmsi2}",
                        'vessel_name': f"{data1['info']['name']} & {data2['info']['name']}",
                        'country': f"{data1['info']['country']},{data2['info']['country']}",
                        'anomaly_type': 'rendezvous',
                        'severity': 'high',
                        'detected_at': timestamp,
                        'details': {
                            'vessel1': {
                                'mmsi': mmsi1,
                                'name': data1['info']['name'],
                                'country': data1['info']['country'],
                                'position': {
                                    'lat': round(pos1['lat'], 4),
                                    'lon': round(pos1['lon'], 4)
                                }
                            },
                            'vessel2': {
                                'mmsi': mmsi2,
                                'name': data2['info']['name'],
                                'country': data2['info']['country'],
                                'position': {
                                    'lat': round(pos2['lat'], 4),
                                    'lon': round(pos2['lon'], 4)
                                }
                            },
                            'distance_km': round(distance, 2)
                        }
                    })

    return anomalies

# =============================================================================
# MAIN PIPELINE
# =============================================================================

def analyze_anomalies(days_back=7):
    """
    Main anomaly detection pipeline

    Returns:
        dict: Analysis results with all detected anomalies
    """
    print("=== AIS Anomaly Detection ===")
    print(f"Loading snapshots from last {days_back} days...")

    # Load and filter data
    snapshots = load_recent_snapshots(days_back)
    print(f"  Found {len(snapshots)} snapshots")

    # Group by vessel
    vessels = group_by_vessel(snapshots)
    print(f"  Filtered to {len(vessels)} monitored vessels")

    # Calculate total positions
    total_positions = sum(len(v['positions']) for v in vessels.values())
    print(f"  Validated {total_positions:,} position records")

    print("\nRunning detection algorithms...")

    # Run all detection algorithms
    gap_anomalies = detect_transmission_gaps(vessels)
    print(f"  ✓ Transmission gaps: {len(gap_anomalies)} anomalies")

    speed_anomalies = detect_impossible_speeds(vessels)
    print(f"  ✓ Impossible speeds: {len(speed_anomalies)} anomalies")

    loiter_anomalies = detect_loitering(vessels)
    print(f"  ✓ Loitering: {len(loiter_anomalies)} anomalies")

    rendezvous_anomalies = detect_rendezvous(vessels)
    print(f"  ✓ Rendezvous: {len(rendezvous_anomalies)} anomalies")

    # Combine all anomalies
    all_anomalies = gap_anomalies + speed_anomalies + loiter_anomalies + rendezvous_anomalies

    # Calculate statistics
    severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for anomaly in all_anomalies:
        severity_counts[anomaly['severity']] += 1

    results = {
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'analysis_period_days': days_back,
        'vessels_analyzed': len(vessels),
        'total_positions': total_positions,
        'anomalies_detected': len(all_anomalies),
        'anomalies': all_anomalies,
        'statistics': {
            'transmission_gaps': len(gap_anomalies),
            'impossible_speeds': len(speed_anomalies),
            'loitering': len(loiter_anomalies),
            'rendezvous': len(rendezvous_anomalies)
        },
        'severity_breakdown': severity_counts
    }

    return results

def save_results_to_json(results):
    """Save anomaly detection results to single rolling JSON file"""
    json_file = ANOMALIES_DIR / 'anomalies.json'

    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)

    return json_file

def save_results_to_csv(results):
    """
    Save anomaly detection results to rolling CSV file with 14-day retention

    CSV format: timestamp, mmsi, vessel_name, country, anomaly_type,
                severity, detected_at, details_json

    Auto-prunes rows older than 14 days on each run.
    """
    csv_file = ANOMALIES_DIR / 'anomalies.csv'
    retention_days = 14
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)

    # Read existing data (if file exists)
    existing_rows = []
    if csv_file.exists():
        with open(csv_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Parse timestamp and filter old data
                row_time = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                if row_time >= cutoff_time:
                    existing_rows.append(row)

    # Convert new anomalies to CSV rows
    new_rows = []
    timestamp = results['timestamp']
    for anomaly in results['anomalies']:
        new_rows.append({
            'timestamp': timestamp,
            'mmsi': str(anomaly['mmsi']),
            'vessel_name': anomaly['vessel_name'],
            'country': anomaly['country'],
            'anomaly_type': anomaly['anomaly_type'],
            'severity': anomaly['severity'],
            'detected_at': anomaly['detected_at'],
            'details_json': json.dumps(anomaly['details'])
        })

    # Combine and write all data
    all_rows = existing_rows + new_rows

    fieldnames = ['timestamp', 'mmsi', 'vessel_name', 'country', 'anomaly_type',
                  'severity', 'detected_at', 'details_json']

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    pruned_count = len(existing_rows) - sum(1 for row in existing_rows if row in all_rows)

    return csv_file, len(new_rows), pruned_count

def main():
    """CLI execution"""
    import time
    start_time = time.time()

    # Run analysis
    results = analyze_anomalies(days_back=7)

    # Save results to JSON (for API/web dashboard)
    json_file = save_results_to_json(results)

    # Save results to rolling CSV (for analysis/debugging)
    csv_file, new_count, pruned_count = save_results_to_csv(results)

    # Print summary
    print(f"\nTotal anomalies detected: {results['anomalies_detected']}")
    print(f"Severity breakdown: {results['severity_breakdown']['critical']} critical, "
          f"{results['severity_breakdown']['high']} high, "
          f"{results['severity_breakdown']['medium']} medium, "
          f"{results['severity_breakdown']['low']} low")

    print(f"\nSaved JSON to: {json_file}")
    print(f"Saved CSV to: {csv_file}")
    print(f"  Added {new_count} new anomalies")
    print(f"  Pruned {pruned_count} old records (>14 days)")
    print(f"Analysis completed in {time.time() - start_time:.1f} seconds")

if __name__ == '__main__':
    main()
