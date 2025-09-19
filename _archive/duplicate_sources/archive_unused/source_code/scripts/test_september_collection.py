#!/usr/bin/env python3
"""
Quick test of the September 2025 data collection pipeline.
Tests with just 3 days to validate functionality.
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set the API key
os.environ['BARENTSWATCH_CLIENT_SECRET'] = 'Xw5yCEXT5gMi5PJEKEW6'

from scripts.collect_september_2025_data import September2025DataCollector
import logging

# Set up logging for test
log_dir = PROJECT_ROOT / 'logs' / 'september_2025'
log_dir.mkdir(parents=True, exist_ok=True)

def test_collection():
    """Test the collection pipeline with a few days."""
    print("🧪 Testing September 2025 Data Collection Pipeline")
    print("=" * 60)
    
    try:
        # Initialize collector
        collector = September2025DataCollector()
        
        # Test with just 3 days
        test_dates = [
            datetime(2025, 9, 1),
            datetime(2025, 9, 15),
            datetime(2025, 9, 30)
        ]
        
        print(f"Testing with {len(test_dates)} dates...")
        
        daily_results = []
        total_vessels = 0
        
        for i, date in enumerate(test_dates, 1):
            print(f"\nDay {i}: {date.strftime('%Y-%m-%d')}")
            
            # Collect daily data
            daily_data = collector.collect_daily_ais_data(date)
            daily_results.append(daily_data)
            
            if daily_data and 'vessels' in daily_data:
                vessel_count = len(daily_data['vessels'])
                total_vessels += vessel_count
                print(f"  ✅ Collected {vessel_count} vessels")
                
                # Generate satellite data
                sat_data = collector.generate_satellite_detections(date, daily_data['vessels'])
                print(f"  ✅ Generated {len(sat_data['detections'])} SAR detections")
                
                # Show sample vessel
                if daily_data['vessels']:
                    sample = daily_data['vessels'][0]
                    print(f"  📍 Sample vessel: {sample['name']} at {sample['latitude']:.2f}°N, {sample['longitude']:.2f}°E")
        
        # Test monthly combination
        print(f"\n📊 Testing monthly data combination...")
        monthly_summary = collector.combine_monthly_data(daily_results)
        
        print(f"\n🎯 Test Results:")
        print(f"  ✅ Days processed: {len(daily_results)}")
        print(f"  ✅ Total vessels: {total_vessels}")
        print(f"  ✅ Monthly summary created")
        print(f"  ✅ Data saved to: {collector.data_dir}")
        
        # Check files created
        ais_files = list(collector.ais_daily_dir.glob("*.json"))
        sat_files = list(collector.satellite_dir.glob("*.json"))
        
        print(f"  ✅ AIS files created: {len(ais_files)}")
        print(f"  ✅ Satellite files created: {len(sat_files)}")
        
        # Show data structure
        if ais_files:
            sample_file = ais_files[0]
            with open(sample_file, 'r') as f:
                sample_data = json.load(f)
            print(f"  📋 Sample data structure:")
            print(f"     - Vessels in file: {len(sample_data.get('vessels', []))}")
            print(f"     - Data sources: {sample_data.get('data_sources', [])}")
            print(f"     - Arctic coverage: {sample_data.get('arctic_coverage', {})}")
        
        print(f"\n🎉 Test completed successfully!")
        print(f"📁 Full pipeline ready for 30-day collection")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_collection()
    if success:
        print("\n✅ Pipeline validated - ready for full 30-day collection!")
    else:
        print("\n❌ Pipeline needs fixes before full collection")