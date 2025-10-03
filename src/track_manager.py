"""
Three-Tier Track Management System
Processes AIS snapshots into tiered historical tracking:
  - Tier 1 (Realtime): 0-2 hours, every update
  - Tier 2 (Tactical): 2-48 hours, 30-min samples
  - Tier 3 (Strategic): 2-7 days, events only
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict

def process_vessel_tracks(snapshots: List[Dict]) -> Dict:
    """
    Convert 30-min snapshots into three-tier structure

    Args:
        snapshots: List of snapshot dicts with 'timestamp' and 'vessels'

    Returns:
        Dict of vessel tracks keyed by MMSI
    """
    # 1. Flatten all snapshots into per-vessel position lists
    vessel_positions = {}

    for snapshot in snapshots:
        snapshot_time = snapshot['timestamp']

        for vessel in snapshot['vessels']:
            mmsi = vessel['mmsi']

            if mmsi not in vessel_positions:
                vessel_positions[mmsi] = {
                    'name': vessel['name'],
                    'country': vessel['country'],
                    'ship_type': vessel['ship_type'],
                    'positions': []
                }

            vessel_positions[mmsi]['positions'].append({
                'timestamp': snapshot_time,
                'lat': vessel['latitude'],
                'lon': vessel['longitude'],
                'speed': vessel['speed'],
                'course': vessel['course']
            })

    # 2. Build three-tier structure for each vessel
    vessel_tracks = {}

    for mmsi, data in vessel_positions.items():
        positions = data['positions']
        positions.sort(key=lambda p: p['timestamp'])  # Ensure chronological order

        tiers = build_three_tiers(positions)

        vessel_tracks[mmsi] = {
            'name': data['name'],
            'country': data['country'],
            'ship_type': data['ship_type'],
            'priority_level': classify_priority(data['country'], data['ship_type']),
            'tiers': tiers
        }

    return vessel_tracks

def build_three_tiers(positions: List[Dict]) -> Dict:
    """
    Split positions into three tiers based on age with continuity at boundaries

    Args:
        positions: Chronologically sorted list of position dicts

    Returns:
        Dict with 'realtime', 'tactical', 'strategic' keys
    """
    now = datetime.now(timezone.utc)

    # Tier 1: Last 2 hours (all points)
    tier1 = [p for p in positions if age_hours(p['timestamp'], now) <= 2]

    # Tier 2: 2-48 hours (sample to 30-min intervals)
    # Include last tier1 point as first point for continuity
    tier2_candidates = [p for p in positions if 2 < age_hours(p['timestamp'], now) <= 48]
    tier2 = sample_to_interval(tier2_candidates, minutes=30)

    # Prepend last tier1 point to tier2 for continuity (NO sorting - keeps bridge at start)
    if tier1 and tier2:
        tier2 = [tier1[-1]] + tier2

    # Tier 3: 2-7 days (daily samples)
    # Include last tier2 point as first point for continuity
    tier3_candidates = [p for p in positions if 48 < age_hours(p['timestamp'], now) <= 168]  # 7 days
    tier3 = extract_strategic_tier(tier3_candidates)

    # Prepend last tier2 point to tier3 for continuity (NO sorting - keeps bridge at start)
    if tier2 and tier3:
        tier3 = [tier2[-1]] + tier3
    elif tier1 and tier3 and not tier2:
        # If no tier2, connect tier1 directly to tier3
        tier3 = [tier1[-1]] + tier3

    return {
        'realtime': tier1,
        'tactical': tier2,
        'strategic': tier3
    }

def age_hours(timestamp_str: str, now: datetime) -> float:
    """Calculate age of timestamp in hours"""
    ts = datetime.fromisoformat(timestamp_str.replace('Z', '')).replace(tzinfo=timezone.utc)
    return (now - ts).total_seconds() / 3600

def sample_to_interval(positions: List[Dict], minutes: int) -> List[Dict]:
    """
    Downsample positions to specified interval (e.g., one point every 30 minutes)

    Args:
        positions: List of position dicts
        minutes: Sampling interval in minutes

    Returns:
        Downsampled list of positions
    """
    if not positions:
        return []

    sampled = []
    interval_delta = timedelta(minutes=minutes)
    last_sampled_time = None

    for pos in positions:
        pos_time = datetime.fromisoformat(pos['timestamp'].replace('Z', ''))

        if last_sampled_time is None or (pos_time - last_sampled_time) >= interval_delta:
            sampled.append(pos)
            last_sampled_time = pos_time

    return sampled

def extract_strategic_tier(positions: List[Dict]) -> List[Dict]:
    """
    Simple daily sampling for strategic tier (2-7 days)
    Returns last position of each day

    Note: Event detection (course changes, speed changes, stops)
    will be handled by separate risk_detection module in the future.

    Args:
        positions: List of position dicts (chronologically sorted)

    Returns:
        List of daily sampled positions (no event classification)
    """
    if not positions:
        return []

    positions_by_date = {}

    # Group positions by date, keep last position of each day
    for pos in positions:
        date_str = datetime.fromisoformat(pos['timestamp'].replace('Z', '')).strftime('%Y-%m-%d')
        positions_by_date[date_str] = pos  # Overwrites with latest position for that day

    # Return in chronological order
    return sorted(positions_by_date.values(), key=lambda p: p['timestamp'])

def classify_priority(country: str, ship_type: str = '') -> str:
    """
    Classify vessel priority level based on country and ship type

    Args:
        country: Vessel country from MMSI
        ship_type: Type of vessel (e.g., 'Military', 'Law Enforcement')

    Returns:
        Priority level: 'high', 'medium', or 'low'
    """
    if country in ['Russia', 'China']:
        return 'high'
    elif country == 'Norway':
        # Norwegian military/law enforcement = high priority (same as Russia/China)
        ship_type_lower = ship_type.lower()
        if 'military' in ship_type_lower or 'law enforcement' in ship_type_lower:
            return 'high'
        else:
            return 'low'  # Civilian Norwegian vessels
    else:
        return 'medium'
