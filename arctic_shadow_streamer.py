#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Consolidated Single Entry Point

Monitors Arctic waters for vessel activity, dark vessel detection,
and submarine cable proximity monitoring.
"""

# Import consolidated functionality
from arctic_shadow_streamer_consolidated import main, run_surveillance_cycle

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run single test cycle
        print("Running single test cycle...")
        run_surveillance_cycle()
    else:
        # Run continuous streaming
        main()