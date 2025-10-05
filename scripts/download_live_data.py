#!/usr/bin/env python3
"""
Download Live AIS Data from GitHub Pages
Fetches latest vessel data without requiring git commits to main branch
"""

import requests
from pathlib import Path
from datetime import datetime
import json

# GitHub Pages URL (update with your actual username)
GITHUB_PAGES_BASE = "https://henrfo.github.io/ArcticShadowTracker"

# Local paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
OUTPUTS_DIR = BASE_DIR / 'outputs'

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

def download_file(url, local_path):
    """Download a file from URL to local path"""
    try:
        print(f"Downloading {url}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        local_path.write_text(response.text)
        print(f"  ✓ Saved to {local_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Failed to download: {e}")
        return False

def main():
    """Download latest data from GitHub Pages"""
    print(f"=== Downloading Live AIS Data ===")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Source: {GITHUB_PAGES_BASE}")
    print()

    success_count = 0
    total_files = 2

    # Download vessel_tracks.json
    if download_file(
        f"{GITHUB_PAGES_BASE}/vessel_tracks.json",
        DATA_DIR / 'vessel_tracks.json'
    ):
        success_count += 1

    # Download latest map HTML
    if download_file(
        f"{GITHUB_PAGES_BASE}/index.html",
        OUTPUTS_DIR / 'index.html'
    ):
        success_count += 1

    print()
    print(f"Download complete: {success_count}/{total_files} files updated")

    if success_count == total_files:
        print("✓ All data synchronized successfully!")

        # Show vessel count
        try:
            with open(DATA_DIR / 'vessel_tracks.json') as f:
                vessel_data = json.load(f)
                print(f"  {len(vessel_data)} vessels tracked")
        except Exception:
            pass
    else:
        print("⚠ Some files failed to download - check your internet connection")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())
