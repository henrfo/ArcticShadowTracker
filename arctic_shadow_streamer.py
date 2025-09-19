#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Backward compatibility wrapper

This file maintains backward compatibility while using the new organized structure.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import from the new location
from arctic_tracker.core.arctic_shadow_streamer import main, run_surveillance_cycle

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run single test cycle
        print("Running single test cycle...")
        run_surveillance_cycle()
    else:
        # Run continuous streaming
        main()