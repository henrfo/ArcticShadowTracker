"""
Three-Tier Track Management System
Processes AIS snapshots into tiered historical tracking:
  - Tier 1 (Realtime): 0-2 hours, every update
  - Tier 2 (Tactical): 2-48 hours, 30-min samples
  - Tier 3 (Strategic): 2-7 days, events only
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict
from pathlib import Path
import json

# Shadow fleet flags of concern (convenience flags commonly used by shadow fleet)
SHADOW_FLEET_FLAGS = {
    # Primary flags (most common shadow fleet)
    'Gabon', 'Cameroon', 'Palau', 'Panama', 'Liberia',
    'Marshall Islands', 'Barbados', 'Saint Kitts and Nevis', 'Tanzania',

    # Secondary flags
    'Benin', 'Comoros', 'Equatorial Guinea', 'Saint Vincent and the Grenadines',
    'Cook Islands', 'Sierra Leone', 'Swaziland', 'Togo', 'Moldova', 'Malta',

    # Also documented
    'Belize', 'Honduras', 'Bolivia', 'Mongolia', 'Cambodia',
    'Sao Tome and Principe', 'Vanuatu', 'Antigua and Barbuda',
    'Dominica', 'Myanmar', 'Iran', 'Venezuela'
}

def load_shadow_fleet():
    """Load shadow fleet MMSI/name lists from config file.

    Returns confirmed + suspected sets separately so the classifier
    can distinguish vessels on official sanctions lists from those
    flagged by single-source intelligence.
    """
    try:
        shadow_file = Path(__file__).parent / 'shadow_fleet.json'
        with open(shadow_file, 'r') as f:
            data = json.load(f)

        confirmed_mmsi = set()
        confirmed_names = set()
        suspected_mmsi = set()
        suspected_names = set()

        # Per-vessel confidence from multi-source dedup
        for v in data.get('vessels', []):
            name = (v.get('vessel_name') or '').lower()
            mmsi = v.get('mmsi')
            confidence = v.get('confidence', 'suspected')
            if confidence == 'confirmed':
                if mmsi: confirmed_mmsi.add(str(mmsi))
                if name: confirmed_names.add(name)
            else:
                if mmsi: suspected_mmsi.add(str(mmsi))
                if name: suspected_names.add(name)

        # Legacy top-level arrays (backward compat)
        for m in data.get('shadow_fleet_mmsi', []):
            confirmed_mmsi.add(str(m))
        for n in data.get('shadow_fleet_names', []):
            confirmed_names.add(n.lower())

        return {
            'mmsi': confirmed_mmsi,
            'names': confirmed_names,
            'suspected_mmsi': suspected_mmsi,
            'suspected_names': suspected_names,
        }
    except Exception as e:
        print(f"Warning: Could not load shadow fleet config: {e}")
        return {'mmsi': set(), 'names': set(), 'suspected_mmsi': set(), 'suspected_names': set()}

def process_vessel_tracks(snapshots: List[Dict]) -> Dict:
    """
    Convert 30-min snapshots into three-tier structure

    Args:
        snapshots: List of snapshot dicts with 'timestamp' and 'vessels'

    Returns:
        Dict of vessel tracks keyed by MMSI
    """
    # Load shadow fleet config
    shadow_fleet = load_shadow_fleet()

    # 1. Flatten all snapshots into per-vessel position lists
    vessel_positions = {}

    for snapshot in snapshots:
        snapshot_time = snapshot['timestamp']

        for vessel in snapshot['vessels']:
            mmsi = vessel['mmsi']

            if mmsi not in vessel_positions:
                vessel_positions[mmsi] = {
                    'name': vessel['name'] or 'Unknown',
                    'country': vessel['country'],
                    'ship_type': vessel['ship_type'],
                    'positions': []
                }

            # Use vessel's individual AIS transmission time (msgtime), not snapshot collection time
            # Fallback to snapshot time only if vessel timestamp is missing
            vessel_timestamp = vessel.get('timestamp', snapshot_time)

            vessel_positions[mmsi]['positions'].append({
                'timestamp': vessel_timestamp,  # Individual vessel AIS transmission time
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

        # Check if vessel is in confirmed shadow fleet list (multi-source)
        vessel_name = data['name'] or 'Unknown'  # Ensure name is never None
        is_shadow_confirmed = (mmsi in shadow_fleet['mmsi'] or
                              vessel_name.lower() in shadow_fleet['names'])

        # Suspected: single-source registry entry OR flag of convenience
        is_shadow_suspected = (not is_shadow_confirmed and (
            mmsi in shadow_fleet.get('suspected_mmsi', set()) or
            vessel_name.lower() in shadow_fleet.get('suspected_names', set()) or
            data['country'] in SHADOW_FLEET_FLAGS
        ))

        # Check if vessel is a buoy (based on name - includes common misspelling "BOUY")
        vessel_name_upper = vessel_name.upper()
        is_buoy = 'BUOY' in vessel_name_upper or 'BOUY' in vessel_name_upper

        vessel_tracks[mmsi] = {
            'name': vessel_name,
            'country': data['country'],
            'ship_type': data['ship_type'],
            'is_shadow_fleet': is_shadow_confirmed,        # Confirmed from curated list
            'is_suspected_shadow': is_shadow_suspected,    # Flag-based suspicion
            'is_buoy': is_buoy,                            # Buoy detection
            'priority_level': classify_priority(data['country'], data['ship_type'],
                                               is_shadow_confirmed, is_shadow_suspected, is_buoy),
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

def classify_priority(country: str, ship_type: str = '',
                     is_shadow_confirmed: bool = False,
                     is_shadow_suspected: bool = False,
                     is_buoy: bool = False) -> str:
    """
    Classify vessel priority level based on country, ship type, and shadow fleet status

    Args:
        country: Vessel country from MMSI
        ship_type: Type of vessel (e.g., 'Military', 'Law Enforcement')
        is_shadow_confirmed: Whether vessel is in confirmed shadow fleet list
        is_shadow_suspected: Whether vessel flies shadow fleet flag
        is_buoy: Whether vessel is a buoy

    Returns:
        Priority level: 'high', 'medium', or 'low'
    """
    # Buoys = lowest priority
    if is_buoy:
        return 'low'

    # Confirmed shadow fleet vessels = highest priority
    if is_shadow_confirmed:
        return 'high'

    # Russian/Chinese vessels = high priority
    if country in ['Russia', 'China']:
        return 'high'

    # Suspected shadow fleet (by flag) = medium priority
    if is_shadow_suspected:
        return 'medium'

    # Norwegian military/law enforcement = high priority
    if country == 'Norway':
        ship_type_lower = ship_type.lower()
        if 'military' in ship_type_lower or 'law enforcement' in ship_type_lower:
            return 'high'
        else:
            return 'low'  # Civilian Norwegian vessels

    # All others = medium priority
    return 'medium'
