#!/usr/bin/env python3
"""
Simple analysis of CSV data for Arctic Shadow Tracker
Demonstrates how easy the CSV schemas are for pandas analysis and dashboard generation
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

def analyze_vessel_positions():
    """Analyze vessel position data"""
    print("📊 VESSEL POSITION ANALYSIS")
    print("=" * 50)
    
    try:
        df = pd.read_csv('vessel_positions.csv', parse_dates=['timestamp'])
        
        print(f"✅ Loaded {len(df)} vessel positions")
        print(f"🚢 Unique vessels: {df['mmsi'].nunique()}")
        print(f"📅 Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # Speed analysis
        print(f"\n🏃 Speed Analysis:")
        print(f"   • Average speed: {df['speed'].mean():.1f} knots")
        print(f"   • Max speed: {df['speed'].max():.1f} knots")
        print(f"   • Vessels at anchor (speed < 1): {(df['speed'] < 1).sum()}")
        print(f"   • Fast vessels (speed > 15): {(df['speed'] > 15).sum()}")
        
        # Geographic distribution
        print(f"\n🌍 Geographic Distribution:")
        print(f"   • Latitude range: {df['latitude'].min():.2f}° to {df['latitude'].max():.2f}°")
        print(f"   • Longitude range: {df['longitude'].min():.2f}° to {df['longitude'].max():.2f}°")
        
        # Arctic regions
        svalbard = df[df['latitude'] >= 76.0]
        barents = df[(df['latitude'] >= 72.0) & (df['latitude'] < 76.0)]
        north_norway = df[(df['latitude'] >= 68.0) & (df['latitude'] < 72.0)]
        
        print(f"   • Svalbard waters (≥76°N): {len(svalbard)} vessels")
        print(f"   • Barents Sea (72-76°N): {len(barents)} vessels") 
        print(f"   • North Norway (68-72°N): {len(north_norway)} vessels")
        
        # Vessel types
        print(f"\n🛳️ Vessel Types (top 5):")
        type_counts = df['vessel_type'].value_counts().head()
        for vtype, count in type_counts.items():
            print(f"   • Type {vtype}: {count} vessels")
        
        return df
        
    except FileNotFoundError:
        print("❌ vessel_positions.csv not found")
        return None

def analyze_cable_alerts():
    """Analyze cable proximity alerts"""
    print("\n🔌 CABLE PROXIMITY ANALYSIS")
    print("=" * 50)
    
    try:
        df = pd.read_csv('cable_alerts.csv', parse_dates=['timestamp'])
        
        print(f"✅ Loaded {len(df)} cable alerts")
        
        # Alert distribution by cable
        print(f"\n📍 Alerts by Cable System:")
        cable_counts = df['cable_name'].value_counts()
        for cable, count in cable_counts.items():
            print(f"   • {cable}: {count} alerts")
        
        # Alert severity
        print(f"\n⚠️ Alert Severity:")
        severity_counts = df['cable_status'].value_counts()
        for severity, count in severity_counts.items():
            print(f"   • {severity}: {count} alerts")
        
        # Distance analysis
        print(f"\n📏 Distance Analysis:")
        print(f"   • Closest approach: {df['distance_km'].min():.2f} km")
        print(f"   • Average distance: {df['distance_km'].mean():.2f} km")
        print(f"   • Alerts < 5km: {(df['distance_km'] < 5).sum()}")
        print(f"   • Alerts < 2km: {(df['distance_km'] < 2).sum()}")
        
        # Most frequent vessels near cables
        print(f"\n🚢 Vessels with Most Cable Alerts:")
        vessel_counts = df['vessel_name'].value_counts().head()
        for vessel, count in vessel_counts.items():
            print(f"   • {vessel}: {count} alerts")
        
        return df
        
    except FileNotFoundError:
        print("❌ cable_alerts.csv not found")
        return None

def analyze_daily_summary():
    """Analyze daily summary trends"""
    print("\n📈 DAILY SUMMARY ANALYSIS")
    print("=" * 50)
    
    try:
        df = pd.read_csv('daily_summary.csv', parse_dates=['date'])
        
        print(f"✅ Loaded {len(df)} daily summaries")
        
        if len(df) > 0:
            latest = df.iloc[-1]
            print(f"\n📅 Latest Summary ({latest['date'].strftime('%Y-%m-%d')}):")
            print(f"   • Total vessels tracked: {latest['total_vessels']}")
            print(f"   • Foreign vessels: {latest['foreign_vessels']}")
            print(f"   • Dark vessel events: {latest['dark_vessel_events']}")
            print(f"   • Cable alerts: {latest['cable_alerts']}")
            print(f"   • Critical alerts: {latest['critical_alerts']}")
            
            print(f"\n🌊 Regional Distribution:")
            print(f"   • Svalbard waters: {latest['svalbard_vessels']} vessels")
            print(f"   • Barents Sea: {latest['barents_vessels']} vessels")
            print(f"   • North Norway: {latest['north_norway_vessels']} vessels")
        
        return df
        
    except FileNotFoundError:
        print("❌ daily_summary.csv not found")
        return None

def check_dark_vessels():
    """Check for dark vessel events"""
    print("\n🌑 DARK VESSEL ANALYSIS")
    print("=" * 50)
    
    try:
        df = pd.read_csv('dark_vessel_events.csv', parse_dates=['detection_timestamp', 'last_seen_timestamp'])
        
        print(f"✅ Loaded {len(df)} dark vessel events")
        
        if len(df) > 0:
            print(f"\n🚨 Recent Dark Vessels:")
            for _, vessel in df.iterrows():
                print(f"   • {vessel['name']} (MMSI: {vessel['mmsi']})")
                print(f"     Last seen: {vessel['last_seen_timestamp']}")
                print(f"     Silent for: {vessel['hours_silent']:.1f} hours")
                print(f"     Status: {vessel['status']}")
        else:
            print("✅ No dark vessel events detected")
        
        return df
        
    except FileNotFoundError:
        print("ℹ️  No dark vessel events file found")
        return None

def generate_intelligence_brief():
    """Generate a simple intelligence briefing"""
    print("\n" + "=" * 70)
    print("🛰️ ARCTIC SHADOW TRACKER - INTELLIGENCE BRIEF")
    print("=" * 70)
    print(f"📅 Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load all data
    vessels_df = analyze_vessel_positions()
    alerts_df = analyze_cable_alerts()
    summary_df = analyze_daily_summary()
    dark_df = check_dark_vessels()
    
    # Generate key insights
    print(f"\n🎯 KEY INSIGHTS:")
    
    if vessels_df is not None:
        high_speed = vessels_df[vessels_df['speed'] > 20]
        if len(high_speed) > 0:
            print(f"   • {len(high_speed)} vessels traveling >20 knots (potentially suspicious)")
        
        northern_vessels = vessels_df[vessels_df['latitude'] > 78]
        if len(northern_vessels) > 0:
            print(f"   • {len(northern_vessels)} vessels in far northern waters (>78°N)")
    
    if alerts_df is not None:
        critical_close = alerts_df[(alerts_df['cable_status'] == 'CRITICAL') & 
                                 (alerts_df['distance_km'] < 3)]
        if len(critical_close) > 0:
            print(f"   • {len(critical_close)} vessels extremely close (<3km) to CRITICAL cables")
    
    if dark_df is not None and len(dark_df) > 0:
        print(f"   • {len(dark_df)} dark vessel events require investigation")
    
    print(f"\n✅ Intelligence brief complete")
    print(f"📊 CSV data is ready for dashboard generation and further analysis")

def main():
    """Main analysis function"""
    print("🔍 Analyzing Arctic Shadow Tracker CSV data...")
    
    # Check if CSV files exist
    csv_files = ['vessel_positions.csv', 'cable_alerts.csv', 'daily_summary.csv']
    missing_files = [f for f in csv_files if not Path(f).exists()]
    
    if missing_files:
        print(f"❌ Missing CSV files: {missing_files}")
        print("Run convert_to_csv.py first to create CSV files")
        return
    
    # Generate intelligence brief
    generate_intelligence_brief()

if __name__ == "__main__":
    main()