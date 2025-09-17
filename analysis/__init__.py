"""
ArcticShadowTracker Analysis Module

Focus: Simple, functional analysis for educational maritime research
This module provides clean risk assessment and pattern analysis.
"""

# Simple/core imports only (avoid heavy dependencies)
try:
    from .simple_risk_scoring import SimpleRiskScorer
    _risk_available = True
except ImportError:
    _risk_available = False

try:
    from .simple_patterns import VesselPatternAnalyzer, FleetAnalyzer
    _patterns_available = True
except ImportError:
    _patterns_available = False

# Advanced imports (optional, only if dependencies available)
try:
    from .advanced_risk_scoring import RiskScorer, ThreatAnalyzer
    _advanced_available = True
except ImportError:
    _advanced_available = False

# Version info
__version__ = "1.0.0"

# Export only what's available
__all__ = []
if _risk_available:
    __all__.extend(['SimpleRiskScorer'])
if _patterns_available:
    __all__.extend(['VesselPatternAnalyzer', 'FleetAnalyzer'])
if _advanced_available:
    __all__.extend(['RiskScorer', 'ThreatAnalyzer'])