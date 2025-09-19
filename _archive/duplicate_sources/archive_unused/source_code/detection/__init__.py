"""
ArcticShadowTracker Detection Module

Focus: Simple, functional modules for educational maritime analysis
This module provides clean vessel detection capabilities.
"""

# Core detection components
try:
    from .vessel_detector import VesselDetector
    _vessel_detector_available = True
except ImportError:
    _vessel_detector_available = False

try:
    from .cable_monitor import CableMonitor
    _cable_monitor_available = True
except ImportError:
    _cable_monitor_available = False

# Advanced imports (optional, only if dependencies available)
try:
    from .advanced_dark_vessels import DarkVesselDetector, VesselTracker
    _advanced_available = True
except ImportError:
    _advanced_available = False

try:
    from .advanced_kola_watcher import KolaWatcher
    _kola_available = True
except ImportError:
    _kola_available = False

# Version info
__version__ = "1.0.0"

# Export only what's available
__all__ = []
if _vessel_detector_available:
    __all__.append('VesselDetector')
if _cable_monitor_available:
    __all__.append('CableMonitor')
if _advanced_available:
    __all__.extend(['DarkVesselDetector', 'VesselTracker'])
if _kola_available:
    __all__.append('KolaWatcher')