"""
ArcticShadowTracker Models Module

Focus: Simple, functional models for educational maritime analysis
This module provides clean machine learning implementations.
"""

# Simple/core imports only (avoid heavy dependencies)
try:
    from .simple_autoencoder import SimpleAnomalyDetector
    _simple_available = True
except ImportError:
    _simple_available = False

# Advanced imports (optional, only if dependencies available) 
try:
    from .advanced_autoencoder import MaritimeAnomalyDetector
    _advanced_available = True
except ImportError:
    _advanced_available = False

# Version info
__version__ = "1.0.0"

# Export only what's available
__all__ = []
if _simple_available:
    __all__.extend(['SimpleAnomalyDetector'])
if _advanced_available:
    __all__.extend(['MaritimeAnomalyDetector'])