#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Daily Surveillance Script
Simple automated daily surveillance execution.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.daily_operations import DailyOperations

# Configure logging
def setup_logging():
    """Setup logging with error handling"""
    try:
        # Create logs directory
        (project_root / 'logs').mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(project_root / 'logs' / f'daily_surveillance_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler()
            ]
        )
    except Exception as e:
        # Fallback to console only
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        print(f"Warning: Could not setup file logging: {e}")

setup_logging()

def main():
    """Execute daily surveillance operations."""
    print("🎯 Arctic Shadow Tracker - Daily Surveillance")
    print("=" * 50)
    
    try:
        # Initialize daily operations
        daily_ops = DailyOperations()
        
        # Run daily surveillance
        print(f"🕐 Starting surveillance: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        operation_results = daily_ops.run_daily_surveillance()
        
        # Display results
        print(f"\n✅ Surveillance completed!")
        print(f"Status: {operation_results['status']}")
        print(f"Duration: {operation_results.get('duration_seconds', 0):.1f} seconds")
        
        if operation_results['status'] == 'SUCCESS':
            print(f"\n📊 Data collected:")
            data_collected = operation_results.get('data_collected', {})
            for data_type, count in data_collected.items():
                print(f"   {data_type}: {count}")
            
            print(f"\n📁 Files generated:")
            files_generated = operation_results.get('files_generated', {})
            for file_type, file_path in files_generated.items():
                if file_path and not file_path.startswith('error'):
                    print(f"   {file_type}: {Path(file_path).name}")
            
            # Mission status
            mission_status = operation_results.get('mission_status', 'UNKNOWN')
            print(f"\n🎯 Mission Status: {mission_status}")
            
            if mission_status in ['CRITICAL_THREATS_DETECTED', 'HIGH_THREATS_DETECTED']:
                print("⚠️ ALERT: Threats detected - review operational reports!")
        
        else:
            print(f"❌ Operation failed: {operation_results.get('error', 'Unknown error')}")
            return 1
    
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logging.error(f"Fatal error in daily surveillance: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)