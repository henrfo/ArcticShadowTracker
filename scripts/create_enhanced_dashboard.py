#!/usr/bin/env python3
"""
Enhanced Arctic Dashboard Creator

This script creates the enhanced Arctic surveillance dashboard with Russian vessel tracks.
Can be run standalone or integrated into the existing streaming system.
"""

import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from arctic_tracker.utils.enhanced_dashboard import create_enhanced_dashboard_with_tracks
import logging

def main():
    """Main function to create enhanced dashboard"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("🛰️ Creating Enhanced Arctic Dashboard with Russian Vessel Tracks")
        logger.info("=" * 60)
        
        # Create enhanced dashboard
        map_file, latest_file = create_enhanced_dashboard_with_tracks()
        
        logger.info("=" * 60)
        logger.info("✅ Enhanced Dashboard Creation Complete!")
        logger.info(f"📄 Timestamped file: {map_file}")
        logger.info(f"📄 Latest file: {latest_file}")
        logger.info("")
        logger.info("🌐 Open the HTML files in your browser to view the enhanced dashboard")
        logger.info("🇷🇺 Russian vessel tracks are shown as colored lines with start/end markers")
        logger.info("🔍 Click on tracks and markers for detailed vessel information")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating enhanced dashboard: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)