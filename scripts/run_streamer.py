#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Streamer Runner

Simple helper script to run and monitor the Arctic Shadow Tracker streaming system.
Provides easy commands for starting, stopping, and checking the streamer status.
"""

import sys
import subprocess
import time
import signal
import os
from pathlib import Path


def check_requirements():
    """Check if required files and dependencies exist"""
    print("🔍 Checking requirements...")
    
    # Check config file
    config_file = Path('../config.yaml')
    if not config_file.exists():
        print("❌ config.yaml not found")
        print("   Please create config.yaml with your BarentsWatch API credentials")
        return False
    
    # Check if we can import required modules
    try:
        import yaml
        import requests
        import folium
        import pandas as pd
        print("✅ All required Python packages available")
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("   Please install with: pip install -r requirements.txt")
        return False
    
    return True


def run_streamer():
    """Run the Arctic Shadow Tracker streamer"""
    if not check_requirements():
        return
    
    print("🛰️ Starting Arctic Shadow Tracker Streamer...")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        # Run the streamer
        subprocess.run([sys.executable, '../arctic_shadow_streamer.py'])
    except KeyboardInterrupt:
        print("\n🛑 Streamer stopped by user")
    except Exception as e:
        print(f"❌ Error running streamer: {e}")


def run_single_cycle():
    """Run a single streaming cycle for testing"""
    if not check_requirements():
        return
    
    print("🧪 Running single test cycle...")
    
    try:
        # Import and run one cycle
        import sys
        sys.path.append('..')
        from arctic_shadow_streamer import run_surveillance_cycle
        
        success = run_surveillance_cycle()
        
        if success:
            print("✅ Test cycle completed successfully")
            print("📊 Check arctic_intelligence/ directory for results")
            print("🗺️ Open arctic_intelligence/arctic_dashboard_latest.html to view map")
        else:
            print("❌ Test cycle failed")
            
    except Exception as e:
        print(f"❌ Error in test cycle: {e}")


def show_status():
    """Show current streamer status and recent data"""
    print("📊 Arctic Shadow Tracker Status")
    print("-" * 40)
    
    data_dir = Path('../arctic_intelligence')
    if not data_dir.exists():
        print("❌ No data directory found - streamer not run yet")
        return
    
    # Check data files
    files_info = [
        ('vessel_positions.csv', 'Vessel positions'),
        ('cable_alerts.csv', 'Cable proximity alerts'),
        ('daily_summary.csv', 'Daily summary'),
        ('arctic_dashboard_latest.html', 'Interactive dashboard'),
        ('streaming.log', 'System logs')
    ]
    
    print("📁 Data Files:")
    for filename, description in files_info:
        filepath = data_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            modified = time.ctime(filepath.stat().st_mtime)
            print(f"   ✅ {filename}: {size:,} bytes (modified: {modified})")
        else:
            print(f"   ❌ {filename}: Not found")
    
    # Show recent log entries
    log_file = data_dir / 'streaming.log'
    if log_file.exists():
        print(f"\n📝 Recent Log Entries:")
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                for line in lines[-5:]:  # Show last 5 lines
                    print(f"   {line.strip()}")
        except Exception as e:
            print(f"   Error reading log: {e}")


def show_help():
    """Show usage help"""
    print("🛰️ Arctic Shadow Tracker - Streamer Runner")
    print("=" * 50)
    print("COMMANDS:")
    print("  run       - Start the continuous streaming system")
    print("  test      - Run a single cycle for testing")
    print("  status    - Show current status and recent data")
    print("  help      - Show this help message")
    print()
    print("EXAMPLES:")
    print("  python run_streamer.py run      # Start streaming")
    print("  python run_streamer.py test     # Test one cycle")
    print("  python run_streamer.py status   # Check status")
    print()
    print("FILES CREATED:")
    print("  arctic_intelligence/vessel_positions.csv     - Time-series vessel data")
    print("  arctic_intelligence/cable_alerts.csv         - Cable proximity alerts")
    print("  arctic_intelligence/daily_summary.csv        - Daily summary data")
    print("  arctic_intelligence/arctic_dashboard_latest.html - Interactive map dashboard")
    print("  arctic_intelligence/streaming.log             - System logs")


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        show_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'run':
        run_streamer()
    elif command == 'test':
        run_single_cycle()
    elif command == 'status':
        show_status()
    elif command == 'help':
        show_help()
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'python run_streamer.py help' for available commands")


if __name__ == "__main__":
    main()