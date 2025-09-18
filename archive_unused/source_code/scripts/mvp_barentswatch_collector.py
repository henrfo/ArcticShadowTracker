#!/usr/bin/env python3
"""
MVP BarentsWatch AIS Data Collector
Simple script that fetches actual AIS data from BarentsWatch and saves to timestamped files.
No databases, no fancy processing - just prove we can get real data.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import json
import logging
from datetime import datetime
from pathlib import Path
from utils.barentswatch_collector import BarentsWatchCollector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """MVP data collection - prove we can get real Arctic vessel data."""
    print("🇳🇴 MVP BarentsWatch AIS Data Collector")
    print("=" * 50)
    
    # Create output directory
    output_dir = Path('data/mvp_pipeline/barentswatch')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize collector
    collector = BarentsWatchCollector()
    
    # Generate timestamp for this run
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Collection log
    collection_log = {
        'timestamp': datetime.now().isoformat(),
        'source': 'barentswatch_official',
        'status': 'started',
        'vessels_collected': 0,
        'regions_processed': 0,
        'errors': []
    }
    
    try:
        # Test authentication first
        logger.info("Testing BarentsWatch authentication...")
        if not collector.auth.test_connection():
            error_msg = "BarentsWatch authentication failed"
            logger.error(error_msg)
            collection_log['status'] = 'failed'
            collection_log['errors'].append(error_msg)
            
            # Save failure log
            log_file = output_dir / f"barentswatch_failed_{timestamp}.json"
            with open(log_file, 'w') as f:
                json.dump(collection_log, f, indent=2)
            
            print(f"❌ Authentication failed - see {log_file}")
            print("\n💡 Setup instructions:")
            print("1. Visit: https://developer.barentswatch.no/")
            print("2. Register application")
            print("3. Set environment variable: export BARENTSWATCH_CLIENT_SECRET='your_secret'")
            return
        
        logger.info("✅ Authentication successful")
        
        # Collect from high-priority Arctic regions
        logger.info("Collecting from high-priority Norwegian Arctic regions...")
        vessels = collector.collect_priority_areas()
        
        if vessels:
            collection_log['status'] = 'success'
            collection_log['vessels_collected'] = len(vessels)
            collection_log['regions_processed'] = len(set(v.get('region', 'unknown') for v in vessels))
            
            # Save vessel data
            data_file = output_dir / f"barentswatch_vessels_{timestamp}.json"
            vessel_data = {
                'metadata': {
                    'collection_time': datetime.now().isoformat(),
                    'source': 'BarentsWatch Official Norwegian API',
                    'total_vessels': len(vessels),
                    'regions': list(set(v.get('region', 'unknown') for v in vessels))
                },
                'vessels': vessels
            }
            
            with open(data_file, 'w') as f:
                json.dump(vessel_data, f, indent=2)
            
            # Save latest copy
            latest_file = output_dir / "latest_barentswatch.json"
            with open(latest_file, 'w') as f:
                json.dump(vessel_data, f, indent=2)
            
            logger.info(f"✅ Collected {len(vessels)} vessels from BarentsWatch")
            print(f"✅ SUCCESS: Collected {len(vessels)} official Norwegian vessels")
            print(f"📁 Data saved to: {data_file}")
            print(f"📁 Latest copy: {latest_file}")
            
            # Show sample vessels
            print(f"\n🚢 Sample vessels:")
            for vessel in vessels[:3]:
                print(f"   • {vessel['name']} (MMSI: {vessel['mmsi']})")
                print(f"     Position: {vessel['latitude']:.3f}°N, {vessel['longitude']:.3f}°E")
                print(f"     Region: {vessel['region']} | Speed: {vessel['speed']:.1f} knots")
                print(f"     Authority: {vessel['authority']}")
        else:
            collection_log['status'] = 'no_data'
            collection_log['errors'].append("No vessels found in high-priority regions")
            
            logger.warning("No vessels collected from high-priority regions")
            print("⚠️ No vessels found in high-priority regions (may be normal)")
        
    except Exception as e:
        error_msg = f"Collection failed: {str(e)}"
        logger.error(error_msg)
        collection_log['status'] = 'error'
        collection_log['errors'].append(error_msg)
        print(f"❌ Collection failed: {e}")
    
    # Save collection log
    log_file = output_dir / f"collection_log_{timestamp}.json"
    with open(log_file, 'w') as f:
        json.dump(collection_log, f, indent=2)
    
    print(f"\n📋 Collection log: {log_file}")
    print(f"🔍 Status: {collection_log['status']}")

if __name__ == "__main__":
    main()