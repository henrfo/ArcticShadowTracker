#!/usr/bin/env python3
"""
Simple AIS Stale Detection - MVP

Detects vessels that haven't updated their AIS position in hours.
No over-engineering, just simple time-based detection.
"""

import json
import csv
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
DATA_DIR = Path('arctic_intelligence')
STALE_THRESHOLD_HOURS = 3  # Alert if no updates for 3+ hours
CRITICAL_THRESHOLD_HOURS = 6  # Critical alert for 6+ hours

def load_vessel_history():
    """Load vessel history data"""
    history_file = DATA_DIR / 'vessel_history.json'
    if history_file.exists():
        with open(history_file, 'r') as f:
            return json.load(f)
    return {}

def get_last_update_time(vessel_data):
    """Get the most recent timestamp from vessel positions"""
    positions = vessel_data.get('positions', [])
    if not positions:
        return None
    
    latest_timestamp = None
    for pos in positions:
        try:
            timestamp = datetime.fromisoformat(pos['timestamp'])
            if latest_timestamp is None or timestamp > latest_timestamp:
                latest_timestamp = timestamp
        except:
            continue
    
    return latest_timestamp

def detect_stale_vessels():
    """Simple detection of vessels with stale AIS data and static positions"""
    print("🔍 Arctic Shadow Tracker - Stale AIS Detection")
    print("=" * 50)
    
    history = load_vessel_history()
    current_time = datetime.now()
    
    stale_vessels = []
    critical_vessels = []
    static_vessels = []
    
    for mmsi, vessel_data in history.items():
        vessel_name = vessel_data.get('name', 'Unknown')
        last_update = get_last_update_time(vessel_data)
        
        if last_update is None:
            continue
        
        hours_stale = (current_time - last_update).total_seconds() / 3600
        
        # Determine country for priority
        country = 'Unknown'
        if mmsi.startswith('273'):
            country = 'Russia 🇷🇺'
        elif mmsi.startswith(('412', '413', '414')):
            country = 'China 🇨🇳'
        elif mmsi.startswith(('257', '258', '259')):
            country = 'Norway 🇳🇴'
        
        # Check for static position (same coordinates repeated)
        positions = vessel_data.get('positions', [])
        unique_positions = set()
        for pos in positions:
            unique_positions.add((pos.get('latitude'), pos.get('longitude')))
        
        is_static = len(positions) >= 5 and len(unique_positions) == 1
        
        # Priority flagging: Only Russian/Chinese static vessels are suspicious (not Norwegian)
        is_priority_vessel = mmsi.startswith('273') or mmsi.startswith(('412', '413', '414'))
        
        if is_static and is_priority_vessel:
            static_vessels.append({
                'mmsi': mmsi,
                'name': vessel_name,
                'country': country,
                'hours_stale': round(hours_stale, 1),
                'last_update': last_update.strftime('%Y-%m-%d %H:%M:%S'),
                'position_count': len(positions),
                'priority': 'STATIC_SUSPICIOUS'
            })
        
        # Check if stale (no updates)
        if hours_stale >= CRITICAL_THRESHOLD_HOURS:
            critical_vessels.append({
                'mmsi': mmsi,
                'name': vessel_name,
                'country': country,
                'hours_stale': round(hours_stale, 1),
                'last_update': last_update.strftime('%Y-%m-%d %H:%M:%S'),
                'priority': 'CRITICAL'
            })
        elif hours_stale >= STALE_THRESHOLD_HOURS:
            stale_vessels.append({
                'mmsi': mmsi,
                'name': vessel_name,
                'country': country,
                'hours_stale': round(hours_stale, 1),
                'last_update': last_update.strftime('%Y-%m-%d %H:%M:%S'),
                'priority': 'WARNING'
            })
    
    # Sort by hours stale (most stale first)
    critical_vessels.sort(key=lambda x: x['hours_stale'], reverse=True)
    stale_vessels.sort(key=lambda x: x['hours_stale'], reverse=True)
    static_vessels.sort(key=lambda x: x['position_count'], reverse=True)
    
    # Display results
    print(f"\n🚨 CRITICAL - No AIS updates for {CRITICAL_THRESHOLD_HOURS}+ hours:")
    if critical_vessels:
        for vessel in critical_vessels:
            print(f"  {vessel['country']} {vessel['name']} (MMSI: {vessel['mmsi']})")
            print(f"    ⏰ Last update: {vessel['last_update']} ({vessel['hours_stale']}h ago)")
            print()
    else:
        print("  ✅ No critical vessels detected")
    
    print(f"\n⚠️  WARNING - No AIS updates for {STALE_THRESHOLD_HOURS}+ hours:")
    if stale_vessels:
        for vessel in stale_vessels[:10]:  # Show top 10
            print(f"  {vessel['country']} {vessel['name']} (MMSI: {vessel['mmsi']})")
            print(f"    ⏰ Last update: {vessel['last_update']} ({vessel['hours_stale']}h ago)")
            print()
        if len(stale_vessels) > 10:
            print(f"  ... and {len(stale_vessels) - 10} more vessels")
    else:
        print("  ✅ No stale vessels detected")
    
    print(f"\n🔴 SUSPICIOUS - Priority vessels broadcasting static positions:")
    if static_vessels:
        for vessel in static_vessels:
            print(f"  {vessel['country']} {vessel['name']} (MMSI: {vessel['mmsi']})")
            print(f"    📍 Broadcasting same position {vessel['position_count']} times")
            print(f"    ⏰ Latest: {vessel['last_update']} ({vessel['hours_stale']}h ago)")
            print()
    else:
        print("  ✅ No suspicious static vessels detected")
    
    # Save results to CSV
    all_alerts = critical_vessels + stale_vessels + static_vessels
    if all_alerts:
        csv_file = DATA_DIR / 'stale_ais_alerts.csv'
        with open(csv_file, 'w', newline='') as f:
            # Include position_count field for static vessels
            fieldnames = ['mmsi', 'name', 'country', 'hours_stale', 'last_update', 'priority', 'position_count']
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(all_alerts)
        print(f"\n💾 Results saved to: {csv_file}")
    
    # Summary
    total_vessels = len(history)
    total_alerts = len(all_alerts)
    print(f"\n📊 SUMMARY:")
    print(f"  Total vessels: {total_vessels}")
    print(f"  Critical alerts: {len(critical_vessels)}")
    print(f"  Warning alerts: {len(stale_vessels)}")
    print(f"  Static suspicious: {len(static_vessels)}")
    print(f"  Total alert rate: {(total_alerts/total_vessels*100):.1f}%")
    
    return all_alerts

def check_specific_vessel(mmsi):
    """Check specific vessel by MMSI"""
    history = load_vessel_history()
    vessel_data = history.get(mmsi)
    
    if not vessel_data:
        print(f"❌ Vessel {mmsi} not found in history")
        return
    
    vessel_name = vessel_data.get('name', 'Unknown')
    positions = vessel_data.get('positions', [])
    
    print(f"\n🔍 Vessel Details: {vessel_name} (MMSI: {mmsi})")
    print("-" * 40)
    
    if not positions:
        print("❌ No position data available")
        return
    
    print(f"📊 Total positions recorded: {len(positions)}")
    
    # Check timestamps
    timestamps = []
    for pos in positions:
        try:
            timestamps.append(datetime.fromisoformat(pos['timestamp']))
        except:
            continue
    
    if timestamps:
        latest = max(timestamps)
        earliest = min(timestamps)
        hours_stale = (datetime.now() - latest).total_seconds() / 3600
        
        print(f"⏰ Latest update: {latest.strftime('%Y-%m-%d %H:%M:%S')} ({hours_stale:.1f}h ago)")
        print(f"📅 Earliest record: {earliest.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if position is static
        if len(set((pos['latitude'], pos['longitude']) for pos in positions)) == 1:
            print(f"🚨 WARNING: All {len(positions)} positions are identical (static)")
        else:
            print(f"✅ Position varies across {len(positions)} records")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Check specific vessel
        mmsi = sys.argv[1]
        check_specific_vessel(mmsi)
    else:
        # Run full detection
        detect_stale_vessels()