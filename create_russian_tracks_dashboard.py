#!/usr/bin/env python3
"""
Enhanced Arctic Dashboard Creator

Simple launcher script to create the enhanced Arctic surveillance dashboard
with 24-hour vessel tracks for Russian and Chinese ships.

Usage:
    python create_russian_tracks_dashboard.py
"""

import sys
import os
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Main function to create the Russian vessel tracks dashboard"""
    print("🛰️ Arctic Shadow Tracker - Enhanced Vessel Tracks Dashboard")
    print("=" * 60)
    
    try:
        # Import the enhanced dashboard creator
        from arctic_tracker.utils.enhanced_dashboard import create_enhanced_dashboard_with_tracks
        
        print("📊 Creating enhanced dashboard with priority vessel tracks...")
        print("🇷🇺 Analyzing Russian vessels (MMSI starting with 273)...")
        print("🇨🇳 Analyzing Chinese vessels (MMSI starting with 412, 413, 414)...")
        
        # Create the enhanced dashboard
        map_file, latest_file = create_enhanced_dashboard_with_tracks()
        
        print("=" * 60)
        print("✅ Enhanced Dashboard Created Successfully!")
        print(f"📄 Main file: {map_file}")
        print(f"📄 Latest file: {latest_file}")
        print("")
        print("🌐 Features included:")
        print("   • 24-hour movement tracks for Russian and Chinese vessels")
        print("   • Color-coded tracks: Red for Russian, Orange for Chinese")
        print("   • Current position markers with detailed vessel info")
        print("   • Track timestamps and speeds on hover/click")
        print("   • All existing features (dark vessels, cable alerts)")
        print("   • Clean track visualization without direction arrows")
        print("")
        print("🔍 Open the HTML file in your web browser to view the dashboard")
        print("📱 Recommended: Use arctic_dashboard_with_tracks_latest.html for live updates")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you're running this from the project root directory")
        return False
        
    except Exception as e:
        print(f"❌ Error creating dashboard: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)