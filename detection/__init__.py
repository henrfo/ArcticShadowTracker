"""
ArcticShadowTracker Detection Module

Focus: Simple, functional modules for educational maritime analysis
This module provides clean vessel detection capabilities.
"""

# Simple/core imports only (avoid heavy dependencies)
try:
    from .simple_vessel_detection import VesselDetector, PatternDetector
    _simple_available = True
except ImportError:
    _simple_available = False

# Advanced imports (optional, only if dependencies available)
try:
    from .advanced_dark_vessels import DarkVesselDetector, VesselTracker
    _advanced_available = True
except ImportError:
    _advanced_available = False

# Version info
__version__ = "1.0.0"

# Export only what's available
__all__ = []
if _simple_available:
    __all__.extend(['VesselDetector', 'PatternDetector'])
if _advanced_available:
    __all__.extend(['DarkVesselDetector', 'VesselTracker'])