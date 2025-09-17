"""
ArcticShadowTracker - Maritime Surveillance and Threat Detection

A comprehensive educational and research platform for Arctic maritime security analysis.
This project is designed for defensive maritime security research and monitoring of 
public waters in accordance with international law.

Quick Start:
-----------
For educational use (learning concepts):
    from arcticshadowtracker.detection import SimpleVesselDetector
    from arcticshadowtracker.models import SimpleAnomalyDetector
    from arcticshadowtracker.analysis import SimpleRiskScorer

For research/production use (full features):
    from arcticshadowtracker.detection import DarkVesselDetector, CableMonitor
    from arcticshadowtracker.models import MaritimeAnomalyDetector
    from arcticshadowtracker.analysis import RiskScorer

Module Organization:
------------------
detection/     - Vessel detection and tracking
  ├── basic_*     → Educational implementations
  └── advanced_*  → Production-ready implementations
  
models/        - Machine learning models
  ├── basic_*     → Simple ML for learning
  └── advanced_*  → Full-featured ML models
  
analysis/      - Risk assessment and pattern analysis
  ├── basic_*     → Simplified analysis
  └── advanced_*  → Comprehensive analysis

Educational Focus:
-----------------
This project emphasizes:
- Defensive maritime security research
- Educational exploration of data science in geospatial analysis
- Student research methodologies
- Compliance with international maritime law
"""

# Import key components for convenience
from . import detection, models, analysis

# Quick access to primary classes (advanced versions by default)
from .detection import DarkVesselDetector, CableMonitor, KolaWatcher
from .models import MaritimeAnomalyDetector, VesselClassifier
from .analysis import RiskScorer, ThreatAnalyzer

# Educational shortcuts
class Educational:
    """Educational module shortcuts for learning."""
    from .detection import SimpleVesselDetector as VesselDetector
    from .models import SimpleAnomalyDetector as AnomalyDetector
    from .analysis import SimpleRiskScorer as RiskScorer

# Project metadata
__title__ = "ArcticShadowTracker"
__description__ = "Maritime surveillance and threat detection for Arctic waters"
__version__ = "1.0.0"
__author__ = "Student Research Project"
__license__ = "Educational Use"

__all__ = [
    # Modules
    'detection',
    'models', 
    'analysis',
    # Primary classes
    'DarkVesselDetector',
    'CableMonitor',
    'KolaWatcher',
    'MaritimeAnomalyDetector',
    'VesselClassifier',
    'RiskScorer',
    'ThreatAnalyzer',
    # Educational access
    'Educational'
]