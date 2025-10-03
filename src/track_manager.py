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
            'risk_level': classify_risk(data['country']),
            'tiers': tiers
        }

    return vessel_tracks

def build_three_tiers(positions: List[Dict]) -> Dict:
    """
    Split positions into three tiers based on age

    Args:
        positions: Chronologically sorted list of position dicts

    Returns:
        Dict with 'realtime', 'tactical', 'strategic' keys
    """
    now = datetime.now(timezone.utc)

    # Tier 1: Last 2 hours (all points)
    tier1 = [p for p in positions if age_hours(p['timestamp'], now) <= 2]

    # Tier 2: 2-48 hours (sample to 30-min intervals)
    tier2_candidates = [p for p in positions if 2 < age_hours(p['timestamp'], now) <= 48]
    tier2 = sample_to_interval(tier2_candidates, minutes=30)

    # Tier 3: 2-7 days (events only)
    tier3_candidates = [p for p in positions if 48 < age_hours(p['timestamp'], now) <= 168]  # 7 days
    tier3 = extract_strategic_events(tier3_candidates)

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

def extract_strategic_events(positions: List[Dict]) -> List[Dict]:
    """
    Extract only significant events from position history

    Events:
    - Course change >45 degrees
    - Speed change >5 knots
    - Stop (speed <1 knot after moving)
    - Resume (speed >=1 knot after stop)
    - Daily bookends (first and last position of each day)

    Args:
        positions: List of position dicts

    Returns:
        List of event positions with 'event' field
    """
    if not positions:
        return []

    events = []

    # Detect event-based positions
    for i in range(1, len(positions)):
        prev = positions[i - 1]
        curr = positions[i]

        # Course change >45 degrees
        course_delta = abs(curr['course'] - prev['course'])
        if course_delta > 45 and course_delta < 315:  # Avoid 360-wrap false positives
            events.append({
                **curr,
                'event': 'course_change',
                'delta': round(course_delta, 1)
            })

        # Speed change >5 knots
        speed_delta = abs(curr['speed'] - prev['speed'])
        if speed_delta > 5:
            events.append({
                **curr,
                'event': 'speed_change',
                'delta': round(speed_delta, 1)
            })

        # Stop (vessel slowing to <1 knot)
        if curr['speed'] < 1 and prev['speed'] >= 1:
            events.append({
                **curr,
                'event': 'stop'
            })

        # Resume (vessel accelerating from <1 knot)
        if curr['speed'] >= 1 and prev['speed'] < 1:
            events.append({
                **curr,
                'event': 'resume'
            })

    # Add daily bookends (first and last position of each day)
    daily_bookends = get_daily_bookends(positions)
    events.extend(daily_bookends)

    # Remove duplicates and sort by timestamp
    seen_timestamps = set()
    unique_events = []

    for event in sorted(events, key=lambda e: e['timestamp']):
        if event['timestamp'] not in seen_timestamps:
            unique_events.append(event)
            seen_timestamps.add(event['timestamp'])

    return unique_events

def get_daily_bookends(positions: List[Dict]) -> List[Dict]:
    """
    Get first and last position of each day

    Args:
        positions: List of position dicts

    Returns:
        List of bookend positions with 'event' field
    """
    if not positions:
        return []

    bookends = []
    positions_by_date = {}

    # Group positions by date
    for pos in positions:
        date_str = datetime.fromisoformat(pos['timestamp'].replace('Z', '')).strftime('%Y-%m-%d')

        if date_str not in positions_by_date:
            positions_by_date[date_str] = []

        positions_by_date[date_str].append(pos)

    # Get first and last of each day
    for date_str, day_positions in positions_by_date.items():
        if len(day_positions) > 0:
            first = day_positions[0]
            last = day_positions[-1]

            bookends.append({**first, 'event': 'day_start'})

            if first['timestamp'] != last['timestamp']:
                bookends.append({**last, 'event': 'day_end'})

    return bookends

def classify_risk(country: str) -> str:
    """
    Classify vessel risk level based on country

    Args:
        country: Vessel country from MMSI

    Returns:
        Risk level: 'high', 'medium', or 'low'
    """
    if country in ['Russia', 'China']:
        return 'high'
    elif country == 'Norway':
        return 'low'
    else:
        return 'medium'
