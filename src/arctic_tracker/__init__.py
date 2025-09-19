"""
Arctic Tracker Core Module

Main components of the Arctic Shadow Tracker system.
"""

from .core.arctic_shadow_streamer import (
    run_surveillance_cycle,
    collect_ais_data,
    detect_dark_vessels,
    check_cable_proximity,
    create_interactive_map,
    main
)