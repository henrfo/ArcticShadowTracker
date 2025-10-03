#!/usr/bin/env python3
"""
Auto-pull AIS data from GitHub Actions
Runs in background to keep local repo synced with remote vessel data
"""

import subprocess
import time
from datetime import datetime

def check_and_pull():
    """Check for remote updates and pull if available"""
    try:
        # Fetch latest changes
        subprocess.run(['git', 'fetch', 'origin', 'main'],
                      capture_output=True, check=True)

        # Check if remote has new commits
        local = subprocess.run(['git', 'rev-parse', 'HEAD'],
                              capture_output=True, text=True, check=True).stdout.strip()
        remote = subprocess.run(['git', 'rev-parse', 'origin/main'],
                               capture_output=True, text=True, check=True).stdout.strip()

        if local != remote:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Remote has updates. Pulling changes...")

            result = subprocess.run(['git', 'pull', 'origin', 'main', '--no-edit'],
                                  capture_output=True, text=True)

            if result.returncode == 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Successfully synced with remote AIS data")
                return True
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠ Pull failed: {result.stderr}")
                return False
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Local is up to date with remote")
            return False

    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {e}")
        return False

def main():
    """Main loop - check every 5 minutes"""
    print("Arctic Shadow Tracker - Auto-pull AIS data")
    print("Checking for remote updates every 5 minutes...")
    print("Press Ctrl+C to stop")
    print()

    try:
        while True:
            check_and_pull()
            time.sleep(300)  # 5 minutes

    except KeyboardInterrupt:
        print("\n\nAuto-pull stopped")

if __name__ == '__main__':
    main()
