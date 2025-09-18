#!/usr/bin/env python3
"""
MVP aisstream.io AIS Data Collector
Simple script that fetches actual AIS data from aisstream.io and saves to timestamped files.
No databases, no fancy processing - just prove we can get real data.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from utils.free_ais_collector import FreeArcticAISCollector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """MVP data collection - prove we can get real Arctic vessel data from aisstream.io."""
    print("🌊 MVP aisstream.io AIS Data Collector")
    print("=" * 50)
    
    # Create output directory
    output_dir = Path('data/mvp_pipeline/aisstream')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize collector
    collector = FreeArcticAISCollector()
    
    # Generate timestamp for this run
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Collection log
    collection_log = {
        'timestamp': datetime.now().isoformat(),
        'source': 'aisstream_io',
        'status': 'started',
        'vessels_collected': 0,
        'collection_duration_minutes': 2,
        'errors': []
    }
    
    try:
        # Check for API key
        api_key = collector._get_aisstream_key()
        if not api_key:
            error_msg = "aisstream.io API key not found"
            logger.error(error_msg)
            collection_log['status'] = 'failed'
            collection_log['errors'].append(error_msg)
            
            # Save failure log
            log_file = output_dir / f"aisstream_failed_{timestamp}.json"
            with open(log_file, 'w') as f:
                json.dump(collection_log, f, indent=2)
            
            print(f"❌ API key not found - see {log_file}")
            print("\n💡 Setup instructions:")
            print("1. Register FREE at: https://aisstream.io/")
            print("2. Get your free API key")
            print("3. Set environment variable: export AISSTREAM_API_KEY='your_free_key'")
            return
        
        logger.info("✅ API key found")
        
        # Collect from aisstream.io (2 minutes of real-time data)
        logger.info("Collecting real-time AIS data from aisstream.io...")
        print("🔄 Collecting real-time AIS data for 2 minutes...")
        
        vessels = await collector.collect_aisstream_data('svalbard', duration_minutes=2)
        
        if vessels:
            collection_log['status'] = 'success'
            collection_log['vessels_collected'] = len(vessels)
            
            # Save vessel data
            data_file = output_dir / f"aisstream_vessels_{timestamp}.json"
            vessel_data = {
                'metadata': {
                    'collection_time': datetime.now().isoformat(),
                    'source': 'aisstream.io WebSocket Stream',
                    'region': 'svalbard',
                    'total_vessels': len(vessels),
                    'collection_duration_minutes': 2
                },
                'vessels': vessels
            }
            
            with open(data_file, 'w') as f:
                json.dump(vessel_data, f, indent=2)
            
            # Save latest copy
            latest_file = output_dir / "latest_aisstream.json"
            with open(latest_file, 'w') as f:
                json.dump(vessel_data, f, indent=2)
            
            logger.info(f"✅ Collected {len(vessels)} vessels from aisstream.io")
            print(f"✅ SUCCESS: Collected {len(vessels)} real-time vessels")
            print(f"📁 Data saved to: {data_file}")
            print(f"📁 Latest copy: {latest_file}")
            
            # Show sample vessels
            print(f"\n🚢 Sample vessels:")
            for vessel in vessels[:3]:
                print(f"   • {vessel['name']} (MMSI: {vessel['mmsi']})")
                print(f"     Position: {vessel['latitude']:.3f}°N, {vessel['longitude']:.3f}°E")
                print(f"     Speed: {vessel['speed']:.1f} knots | Course: {vessel['course']:.1f}°")
                print(f"     Source: {vessel['source']}")
        else:
            collection_log['status'] = 'no_data'
            collection_log['errors'].append("No vessels received from aisstream.io")
            
            logger.warning("No vessels received from aisstream.io")
            print("⚠️ No vessels received from aisstream.io")
            print("This could be normal if no vessels are currently in the Arctic region")
        
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

def run_sync_main():
    """Synchronous wrapper for the async main function."""
    try:
        # Check if we're already in an event loop
        loop = asyncio.get_running_loop()
        print("❌ Cannot run in existing event loop. Run this script directly.")
        return
    except RuntimeError:
        # No event loop, safe to use asyncio.run
        asyncio.run(main())

if __name__ == "__main__":
    run_sync_main()