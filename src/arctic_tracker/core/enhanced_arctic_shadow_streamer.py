#!/usr/bin/env python3
"""
Enhanced Arctic Shadow Tracker - Core Streaming System with Russian Vessel Tracks

Extended version of the original arctic_shadow_streamer.py that includes
enhanced dashboards with Russian vessel track visualization.
"""

import sys
import os
from pathlib import Path

# Import the original streamer functionality
from .arctic_shadow_streamer import (
    logger, DATA_DIR, SUBMARINE_CABLES, MMSI_COUNTRY_MAP,
    collect_ais_data, check_cable_proximity, detect_dark_vessels,
    save_to_csv, create_interactive_map
)

# Import enhanced dashboard functionality
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from utils.enhanced_dashboard import create_enhanced_dashboard_with_tracks

def run_enhanced_surveillance_cycle():
    """Run one complete surveillance cycle with enhanced dashboards"""
    logger.info("=" * 60)
    logger.info("Starting Enhanced Arctic Surveillance Cycle")
    logger.info("🇷🇺 Including Russian vessel track analysis")
    
    try:
        # Collect data (same as original)
        vessels = collect_ais_data()
        cable_alerts = check_cable_proximity(vessels)
        dark_vessels = detect_dark_vessels(vessels)
        
        # Save data (same as original)
        save_to_csv(vessels, dark_vessels, cable_alerts)
        
        # Create standard dashboard (same as original)
        standard_map_file = create_interactive_map(vessels, dark_vessels, cable_alerts)
        
        # Create enhanced dashboard with Russian vessel tracks
        logger.info("Creating enhanced dashboard with Russian vessel tracks...")
        enhanced_map_file, enhanced_latest = create_enhanced_dashboard_with_tracks()
        
        # Summary
        logger.info(f"Enhanced cycle complete: {len(vessels)} vessels, {len(dark_vessels)} dark, {len(cable_alerts)} alerts")
        logger.info(f"Standard dashboard: {standard_map_file}")
        logger.info(f"Enhanced dashboard: {enhanced_map_file}")
        logger.info(f"Enhanced latest: {enhanced_latest}")
        
        return True
        
    except Exception as e:
        logger.error(f"Enhanced surveillance cycle failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main_enhanced():
    """Main streaming loop with enhanced dashboards"""
    logger.info("🛰️ Enhanced Arctic Shadow Tracker Streaming Started")
    logger.info("🇷🇺 Russian vessel track monitoring enabled")
    
    while True:
        try:
            success = run_enhanced_surveillance_cycle()
            
            if success:
                logger.info("Waiting 30 minutes for next enhanced cycle...")
                import time
                time.sleep(1800)  # 30 minutes
            else:
                logger.info("Waiting 5 minutes before retry...")
                import time
                time.sleep(300)   # 5 minutes on error
                
        except KeyboardInterrupt:
            logger.info("Enhanced streaming stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error in enhanced streaming: {e}")
            import time
            time.sleep(300)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run single enhanced test cycle
        logger.info("Running single enhanced test cycle...")
        run_enhanced_surveillance_cycle()
    else:
        # Run continuous enhanced streaming
        main_enhanced()