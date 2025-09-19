#!/usr/bin/env python3
"""
Convert Arctic Shadow Tracker JSON data to CSV format
Based on real BarentsWatch data structure from barentswatch_test_v2.ipynb
"""

import json
import pandas as pd
from datetime import datetime
from pathlib import Path

def load_intelligence_data():
    """Load existing JSON intelligence data"""
    data_dir = Path('arctic_intelligence')
    
    # Find latest intelligence file
    intelligence_files = list(data_dir.glob('intelligence_*.json'))
    if not intelligence_files:
        print("❌ No intelligence files found")
        return None, None, None
    
    latest_file = max(intelligence_files)
    print(f"📊 Loading data from: {latest_file}")
    
    with open(latest_file, 'r') as f:
        data = json.load(f)
    
    # Extract data from latest collection
    latest_collection = data['collections'][-1]
    vessels = latest_collection['vessels']
    dark_vessels = latest_collection['dark_vessels']
    cable_alerts = latest_collection['cable_alerts']
    
    return vessels, dark_vessels, cable_alerts

def filter_foreign_vessels(vessels):
    """Filter out Norwegian vessels based on MMSI and name patterns"""
    norwegian_mmsi_patterns = ['257', '258', '259']
    norwegian_patterns = [
        'NO ', 'NORGE', 'NORSK', 'BERGEN', 'OSLO', 'STAVANGER', 
        'TROMSOE', 'TROMSO', 'HAVILA', 'HURTIGRUTEN', 'FJORD', 
        'STIND', 'FISK', 'FROST', 'POLAR', 'KVAL', 'SUND', 
        'BORG', 'HOLM', 'NESS', 'VIK', 'HAUG', 'STRAND'
    ]
    
    foreign_vessels = []
    norwegian_count = 0
    
    for vessel in vessels:
        mmsi = str(vessel.get('mmsi', ''))
        name = vessel.get('name', '').upper()
        
        # Check MMSI patterns
        is_norwegian = any(mmsi.startswith(pattern) for pattern in norwegian_mmsi_patterns)
        
        # Check name patterns
        if not is_norwegian:
            is_norwegian = any(pattern in name for pattern in norwegian_patterns)
        
        if not is_norwegian:
            foreign_vessels.append(vessel)
        else:
            norwegian_count += 1
    
    print(f"✅ Filtered to {len(foreign_vessels)} foreign vessels")
    print(f"🇳🇴 Excluded {norwegian_count} Norwegian vessels")
    
    return foreign_vessels

def create_vessel_positions_csv(vessels):
    """Create vessel_positions.csv from vessel data"""
    if not vessels:
        print("❌ No vessel data to convert")
        return
    
    # Convert to DataFrame with proper column mapping
    vessel_data = []
    for vessel in vessels:
        row = {
            'timestamp': vessel['timestamp'],
            'mmsi': vessel['mmsi'],
            'name': vessel['name'],
            'latitude': vessel['latitude'],
            'longitude': vessel['longitude'],
            'speed': vessel['speed'],
            'course': vessel['course'],
            'vessel_type': vessel['vessel_type']
        }
        vessel_data.append(row)
    
    df = pd.DataFrame(vessel_data)
    
    # Create CSV file
    csv_file = 'vessel_positions.csv'
    
    # Create header if file doesn't exist
    if not Path(csv_file).exists():
        df.to_csv(csv_file, index=False)
        print(f"✅ Created {csv_file} with {len(df)} vessels")
    else:
        df.to_csv(csv_file, mode='a', header=False, index=False)
        print(f"✅ Appended {len(df)} vessels to {csv_file}")

def create_dark_vessel_events_csv(dark_vessels):
    """Create dark_vessel_events.csv from dark vessel data"""
    if not dark_vessels:
        print("ℹ️  No dark vessel events to convert")
        return
    
    # Convert to DataFrame
    dark_data = []
    for vessel in dark_vessels:
        row = {
            'detection_timestamp': vessel['detection_time'],
            'mmsi': vessel['mmsi'],
            'name': vessel['name'],
            'last_seen_timestamp': vessel['last_seen'],
            'hours_silent': vessel['hours_since_seen'],
            'last_latitude': vessel['last_position'][0],
            'last_longitude': vessel['last_position'][1],
            'last_speed': vessel['last_speed'],
            'last_course': None,  # Not in current data structure
            'status': vessel['status']
        }
        dark_data.append(row)
    
    df = pd.DataFrame(dark_data)
    
    # Create CSV file
    csv_file = 'dark_vessel_events.csv'
    
    if not Path(csv_file).exists():
        df.to_csv(csv_file, index=False)
        print(f"✅ Created {csv_file} with {len(df)} dark vessel events")
    else:
        df.to_csv(csv_file, mode='a', header=False, index=False)
        print(f"✅ Appended {len(df)} dark vessel events to {csv_file}")

def create_cable_alerts_csv(cable_alerts):
    """Create cable_alerts.csv from cable alert data"""
    if not cable_alerts:
        print("ℹ️  No cable alerts to convert")
        return
    
    # Convert to DataFrame
    alert_data = []
    for alert in cable_alerts:
        row = {
            'timestamp': alert['timestamp'],
            'vessel_mmsi': alert['vessel_mmsi'],
            'vessel_name': alert['vessel_name'],
            'cable_id': alert['cable_id'],
            'cable_name': alert['cable_name'],
            'distance_km': alert['distance_km'],
            'alert_threshold': alert['alert_threshold'],
            'cable_status': alert['cable_status'],
            'vessel_latitude': alert['vessel_position'][0],
            'vessel_longitude': alert['vessel_position'][1]
        }
        alert_data.append(row)
    
    df = pd.DataFrame(alert_data)
    
    # Create CSV file
    csv_file = 'cable_alerts.csv'
    
    if not Path(csv_file).exists():
        df.to_csv(csv_file, index=False)
        print(f"✅ Created {csv_file} with {len(df)} cable alerts")
    else:
        df.to_csv(csv_file, mode='a', header=False, index=False)
        print(f"✅ Appended {len(df)} cable alerts to {csv_file}")

def create_daily_summary_csv(vessels, dark_vessels, cable_alerts):
    """Create daily_summary.csv with aggregated statistics"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Count vessel types by region (simplified)
    svalbard_count = sum(1 for v in vessels if v['latitude'] >= 76.0)
    barents_count = sum(1 for v in vessels if 72.0 <= v['latitude'] < 76.0)
    north_norway_count = sum(1 for v in vessels if 68.0 <= v['latitude'] < 72.0)
    
    # Count alert types
    critical_alerts = sum(1 for a in cable_alerts if a['cable_status'] == 'CRITICAL')
    high_alerts = sum(1 for a in cable_alerts if a['cable_status'] == 'HIGH')
    
    summary_data = {
        'date': today,
        'total_collections': 1,  # This collection
        'total_vessels': len(vessels),
        'foreign_vessels': len(vessels),  # Already filtered
        'norwegian_filtered': 0,  # Already filtered out
        'dark_vessel_events': len(dark_vessels),
        'cable_alerts': len(cable_alerts),
        'critical_alerts': critical_alerts,
        'high_alerts': high_alerts,
        'svalbard_vessels': svalbard_count,
        'barents_vessels': barents_count,
        'north_norway_vessels': north_norway_count
    }
    
    df = pd.DataFrame([summary_data])
    
    # Create CSV file
    csv_file = 'daily_summary.csv'
    
    if not Path(csv_file).exists():
        df.to_csv(csv_file, index=False)
        print(f"✅ Created {csv_file} with daily summary")
    else:
        # Check if today's data already exists
        existing_df = pd.read_csv(csv_file)
        if today not in existing_df['date'].values:
            df.to_csv(csv_file, mode='a', header=False, index=False)
            print(f"✅ Added today's summary to {csv_file}")
        else:
            print(f"ℹ️  Today's summary already exists in {csv_file}")

def main():
    """Main conversion function"""
    print("🔄 Converting JSON intelligence data to CSV format...")
    print("=" * 60)
    
    # Load data
    vessels, dark_vessels, cable_alerts = load_intelligence_data()
    if vessels is None:
        return
    
    # Filter foreign vessels
    foreign_vessels = filter_foreign_vessels(vessels)
    
    # Create CSV files
    create_vessel_positions_csv(foreign_vessels)
    create_dark_vessel_events_csv(dark_vessels)
    create_cable_alerts_csv(cable_alerts)
    create_daily_summary_csv(foreign_vessels, dark_vessels, cable_alerts)
    
    print("\n" + "=" * 60)
    print("✅ CSV conversion completed!")
    print("\n📊 CSV Files Created:")
    print("   • vessel_positions.csv - Real-time AIS positions (foreign vessels only)")
    print("   • dark_vessel_events.csv - Vessels that turned off AIS")
    print("   • cable_alerts.csv - Proximity alerts to submarine cables")
    print("   • daily_summary.csv - Aggregated daily statistics")
    
    print("\n🔍 Sample Analysis:")
    
    # Show sample analysis
    try:
        df = pd.read_csv('vessel_positions.csv')
        print(f"   • {len(df)} total vessel positions tracked")
        print(f"   • {df['mmsi'].nunique()} unique vessels")
        print(f"   • Speed range: {df['speed'].min():.1f} - {df['speed'].max():.1f} knots")
        print(f"   • Most common vessel type: {df['vessel_type'].mode().values[0]}")
    except:
        pass

if __name__ == "__main__":
    main()