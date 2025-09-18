#!/usr/bin/env python3
"""
Full 30-Day September 2025 Arctic Maritime Data Collection
Production-ready script for dashboard deployment.

This script collects complete September 2025 data:
- Real BarentsWatch Historic AIS data for Norwegian Arctic waters
- Realistic Sentinel-1 SAR detection files
- Dashboard-ready CSV and JSON formats
- Comprehensive monthly analysis

Usage:
    export BARENTSWATCH_CLIENT_SECRET="Xw5yCEXT5gMi5PJEKEW6"
    python scripts/run_full_september_collection.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.collect_september_2025_data import September2025DataCollector

def main():
    """Run the complete 30-day data collection."""
    print("🚀 ARCTIC SHADOW TRACKER - September 2025 Data Collection")
    print("=" * 70)
    print("🎯 Mission: Collect 30 days of real Arctic maritime data")
    print("📊 Target: Production dashboard deployment")
    print("🌊 Coverage: Norwegian Arctic waters, Svalbard, Barents Sea")
    print("📡 Sources: BarentsWatch Historic AIS + Sentinel-1 SAR")
    print("=" * 70)
    
    # Check environment variable
    if not os.getenv('BARENTSWATCH_CLIENT_SECRET'):
        print("❌ ERROR: BARENTSWATCH_CLIENT_SECRET environment variable not set")
        print("💡 Please run: export BARENTSWATCH_CLIENT_SECRET=\"Xw5yCEXT5gMi5PJEKEW6\"")
        return 1
    
    try:
        # Initialize and run collector
        collector = September2025DataCollector()
        results = collector.run_complete_collection()
        
        print("\n🎉 MISSION COMPLETE - September 2025 Data Collection")
        print("=" * 70)
        print(f"✅ Collection Duration: {results['collection_duration']}")
        print(f"✅ Days Processed: {results['days_processed']}/30")
        print(f"✅ Total Vessels: {results['total_vessels_collected']}")
        print(f"✅ Real Data Days: {results['real_data_days']}/30")
        print(f"✅ Data Quality: {results['data_quality_score']*100:.1f}%")
        print("\n📁 Data Locations:")
        for name, path in results['output_directories'].items():
            print(f"   {name}: {path}")
        
        print("\n🚀 Ready for Dashboard Deployment!")
        print("📊 Use data from: data/september_2025/")
        print("📈 CSV files ready for immediate visualization")
        print("🗃️  JSON files contain full metadata and analysis")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Collection failed: {e}")
        print("💡 Check your API credentials and network connection")
        return 1

if __name__ == "__main__":
    exit(main())