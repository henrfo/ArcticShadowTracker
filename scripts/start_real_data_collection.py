#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Real Data Collection Starter
Simple script to initialize real data collection for Arctic surveillance.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

def main():
    parser = argparse.ArgumentParser(description='Start real data collection for Arctic surveillance')
    parser.add_argument('--days', type=int, default=7, help='Number of days to backfill (default: 7)')
    parser.add_argument('--mode', choices=['demo', 'backfill', 'current'], default='demo', 
                       help='Collection mode: demo (sample data), backfill (historical), current (today only)')
    parser.add_argument('--sources', nargs='+', default=['ais', 'sar'], 
                       choices=['ais', 'sar', 'all'], help='Data sources to collect')
    
    args = parser.parse_args()
    
    print("🌊 Arctic Shadow Tracker - Real Data Collection")
    print("=" * 50)
    print(f"📅 Mode: {args.mode}")
    print(f"📊 Sources: {', '.join(args.sources)}")
    if args.mode == 'backfill':
        print(f"🔄 Backfill period: {args.days} days")
    print()
    
    if args.mode == 'demo':
        print("🎯 DEMO MODE: Creating sample data for testing")
        create_sample_data()
        
    elif args.mode == 'backfill':
        print(f"🔄 BACKFILL MODE: Collecting {args.days} days of historical data")
        run_historical_backfill(args.days, args.sources)
        
    elif args.mode == 'current':
        print("📡 CURRENT MODE: Collecting today's data")
        run_current_collection(args.sources)
    
    print("\n✅ Data collection complete!")
    print("🚀 Ready to run: jupyter notebook notebooks/operational/arctic_surveillance_dashboard.ipynb")

def create_sample_data():
    """Create sample data for testing"""
    print("📁 Creating sample AIS and SAR data...")
    
    # Create data directories
    ais_dir = project_root / 'data' / 'ais'
    satellite_dir = project_root / 'data' / 'satellite'
    ais_dir.mkdir(parents=True, exist_ok=True)
    satellite_dir.mkdir(parents=True, exist_ok=True)
    
    # Sample AIS data
    sample_ais = [
        {
            'mmsi': '257001234',
            'latitude': 78.20,
            'longitude': 15.60,
            'speed': 12.5,
            'course': 45.0,
            'timestamp': datetime.now().isoformat(),
            'vessel_name': 'ARCTIC_EXPLORER',
            'vessel_type': 'Research',
            'source': 'SAMPLE'
        },
        {
            'mmsi': '257005678', 
            'latitude': 71.10,
            'longitude': 25.80,
            'speed': 8.2,
            'course': 180.0,
            'timestamp': datetime.now().isoformat(),
            'vessel_name': 'BARENTS_FISHER',
            'vessel_type': 'Fishing',
            'source': 'SAMPLE'
        },
        {
            'mmsi': '257009999',
            'latitude': 74.00,
            'longitude': 30.00,
            'speed': 15.1,
            'course': 270.0,
            'timestamp': datetime.now().isoformat(),
            'vessel_name': 'SUSPICIOUS_VESSEL',
            'vessel_type': 'Unknown',
            'source': 'SAMPLE'
        }
    ]
    
    # Save AIS data
    import json
    import pandas as pd
    
    with open(ais_dir / 'sample_arctic_ais.json', 'w') as f:
        json.dump(sample_ais, f, indent=2)
    
    pd.DataFrame(sample_ais).to_csv(ais_dir / 'sample_arctic_ais.csv', index=False)
    
    # Sample SAR data placeholders
    sar_samples = [
        {
            'product_name': 'S1A_IW_GRDH_1SDV_20250918T060000_20250918T060025_Arctic',
            'center_location': [78.2, 15.6],
            'description': 'Sentinel-1A Arctic SAR data',
            'created_time': datetime.now().isoformat()
        },
        {
            'product_name': 'S1B_IW_GRDH_1SDV_20250918T120000_20250918T120025_Barents',
            'center_location': [71.0, 25.0],
            'description': 'Sentinel-1B Barents Sea SAR data', 
            'created_time': datetime.now().isoformat()
        }
    ]
    
    for sar_sample in sar_samples:
        filename = f"{sar_sample['product_name']}.SAFE.placeholder"
        with open(satellite_dir / filename, 'w') as f:
            json.dump(sar_sample, f, indent=2)
    
    print(f"   ✅ Created {len(sample_ais)} AIS sample records")
    print(f"   ✅ Created {len(sar_samples)} SAR sample files")
    print(f"   📂 AIS data: {ais_dir}")
    print(f"   📂 SAR data: {satellite_dir}")

def run_historical_backfill(days, sources):
    """Run historical data backfill"""
    try:
        if 'ais' in sources or 'all' in sources:
            print("📡 Collecting historical AIS data...")
            from utils.real_ais_collector import RealAISCollector
            
            ais_collector = RealAISCollector()
            
            for i in range(days):
                target_date = datetime.now() - timedelta(days=i)
                print(f"   📅 Collecting AIS data for {target_date.strftime('%Y-%m-%d')}")
                
                ais_data = ais_collector.fetch_historical_data(
                    start_date=target_date,
                    end_date=target_date + timedelta(days=1)
                )
                
                if ais_data:
                    print(f"      ✅ Found {len(ais_data)} AIS records")
                else:
                    print(f"      ⚠️ No AIS data available")
        
        if 'sar' in sources or 'all' in sources:
            print("\n🛰️ Collecting historical SAR data...")
            from utils.real_sentinel_collector import RealSentinelCollector
            
            sentinel_collector = RealSentinelCollector()
            
            for i in range(days):
                target_date = datetime.now() - timedelta(days=i)
                print(f"   📅 Searching SAR data for {target_date.strftime('%Y-%m-%d')}")
                
                sar_products = sentinel_collector.search_sentinel1_products(
                    start_date=target_date,
                    end_date=target_date + timedelta(days=1),
                    max_results=10
                )
                
                if sar_products:
                    print(f"      ✅ Found {len(sar_products)} SAR products")
                    # Download first product as sample
                    if i == 0:  # Only download latest day to save bandwidth
                        sentinel_collector.download_product(sar_products[0])
                else:
                    print(f"      ⚠️ No SAR data available")
                    
    except ImportError as e:
        print(f"❌ Real data collection modules not available: {e}")
        print("💡 Falling back to sample data creation...")
        create_sample_data()

def run_current_collection(sources):
    """Collect current day data"""
    try:
        if 'ais' in sources or 'all' in sources:
            print("📡 Collecting current AIS data...")
            from utils.real_ais_collector import RealAISCollector
            
            ais_collector = RealAISCollector()
            ais_data = ais_collector.fetch_current_data()
            
            if ais_data:
                print(f"   ✅ Collected {len(ais_data)} current AIS records")
            else:
                print("   ⚠️ No current AIS data available")
        
        if 'sar' in sources or 'all' in sources:
            print("\n🛰️ Collecting current SAR data...")
            from utils.real_sentinel_collector import RealSentinelCollector
            
            sentinel_collector = RealSentinelCollector()
            today = datetime.now()
            
            sar_products = sentinel_collector.search_sentinel1_products(
                start_date=today - timedelta(hours=12),
                end_date=today,
                max_results=10
            )
            
            if sar_products:
                print(f"   ✅ Found {len(sar_products)} recent SAR products")
            else:
                print("   ⚠️ No recent SAR data available")
                
    except ImportError as e:
        print(f"❌ Real data collection modules not available: {e}")
        print("💡 Falling back to sample data creation...")
        create_sample_data()

if __name__ == "__main__":
    main()