# ArcticShadowTracker - API Reference

## Core Classes and Methods

This reference provides detailed API documentation for the main classes and methods in ArcticShadowTracker, designed to help Claude Code provide accurate assistance.

## Detection Module APIs

### `DarkVesselDetector`

Main class for detecting vessels not broadcasting AIS signals.

```python
class DarkVesselDetector:
    def __init__(self, matching_threshold_meters=500, 
                 vessel_size_threshold=20,
                 confidence_threshold=0.7):
        """
        Initialize dark vessel detector.
        
        Args:
            matching_threshold_meters (int): Max distance for SAR/AIS correlation
            vessel_size_threshold (int): Minimum vessel size in pixels
            confidence_threshold (float): Minimum detection confidence (0-1)
        """

    def detect_vessels_in_sar(self, sar_image_path: str, 
                             roi_bounds: Optional[Tuple] = None) -> List[Dict]:
        """
        Detect vessels in SAR imagery.
        
        Args:
            sar_image_path (str): Path to Sentinel-1 SAR image
            roi_bounds (tuple): Optional (min_lat, min_lon, max_lat, max_lon)
            
        Returns:
            List[Dict]: Detected vessels with coordinates and metadata
            
        Example vessel dict:
        {
            'detection_id': 'SAR_20241115_001',
            'latitude': 70.123,
            'longitude': 31.456,
            'estimated_length': 85.5,
            'confidence': 0.87,
            'detection_time': '2024-11-15T10:30:00'
        }
        """

    def find_dark_vessels(self, sar_detections: List[Dict], 
                         ais_data: List[Dict],
                         time_tolerance_minutes: int = 30) -> List[Dict]:
        """
        Compare SAR detections with AIS data to find dark vessels.
        
        Args:
            sar_detections: Output from detect_vessels_in_sar()
            ais_data: AIS position reports
            time_tolerance_minutes: Max time difference for correlation
            
        Returns:
            List[Dict]: Dark vessels with risk assessment
        """
```

### `CableMonitor`

Infrastructure protection and submarine cable monitoring.

```python
class CableMonitor:
    def __init__(self, proximity_threshold_km=5, 
                 loitering_threshold_hours=2):
        """
        Initialize cable monitoring system.
        
        Args:
            proximity_threshold_km (float): Alert distance from cables
            loitering_threshold_hours (float): Time threshold for loitering
        """

    def check_vessel_cable_proximity(self, vessels: List[Dict]) -> List[Dict]:
        """
        Check if vessels are near submarine cables.
        
        Args:
            vessels: List of vessel position dictionaries
            
        Returns:
            List[Dict]: Vessels with cable proximity information added
            
        Added fields:
        - 'near_cable': bool
        - 'closest_cable': str (cable name)
        - 'distance_to_cable_km': float
        - 'cable_alerts': List[Dict] (proximity alerts)
        """

    def detect_loitering_near_cables(self, vessel_tracks: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Detect vessels loitering near submarine cables.
        
        Args:
            vessel_tracks: Dict of {vessel_id: [position_list]}
            
        Returns:
            List[Dict]: Loitering incidents with details
        """
```

### `KolaWatcher`

Specialized monitoring for Kola Peninsula strategic areas.

```python
class KolaWatcher:
    def analyze_vessel_activity(self, vessels: List[Dict]) -> Dict:
        """
        Analyze vessel activity in Kola Peninsula region.
        
        Args:
            vessels: List of vessel positions and data
            
        Returns:
            Dict: Comprehensive analysis with structure:
            {
                'naval_base_activity': Dict[str, Dict],
                'restricted_zone_violations': List[Dict],
                'strategic_area_activity': Dict[str, Dict],
                'threat_assessment': Dict
            }
        """

    def generate_kola_report(self, vessels: List[Dict]) -> Dict:
        """
        Generate comprehensive Kola Peninsula monitoring report.
        
        Returns:
            Dict: Complete monitoring report with executive summary
        """
```

## Models Module APIs

### `MaritimeAnomalyDetector`

Autoencoder-based anomaly detection for vessel behavior.

```python
class MaritimeAnomalyDetector:
    def __init__(self, input_dim=10, encoding_dim=5):
        """
        Initialize anomaly detector.
        
        Args:
            input_dim (int): Number of input features (default: 10)
            encoding_dim (int): Encoding layer dimension
        """

    def extract_features(self, vessel_data: Dict) -> np.array:
        """
        Extract feature vector from vessel data.
        
        Args:
            vessel_data: Dict with keys:
            - 'distance_to_cable': float (km)
            - 'distance_to_military_base': float (km)
            - 'vessel_size': float (meters)
            - 'estimated_speed': float (km/h)
            - 'time_stationary': float (hours)
            - 'time_of_day': int (0-23)
            - 'day_of_week': int (0-6)
            - 'distance_to_port': float (km)
            - 'weather_severity': float (0-10)
            - 'repeat_visits': int
            
        Returns:
            np.array: 10-element feature vector
        """

    def train(self, training_data: np.array, epochs=100, batch_size=32):
        """
        Train autoencoder on normal vessel behavior patterns.
        
        Args:
            training_data: (N, 10) array of normal behavior features
            epochs: Training epochs
            batch_size: Training batch size
            
        Returns:
            History object from Keras training
        """

    def predict_anomaly(self, vessel_data: Dict) -> Dict:
        """
        Predict if vessel exhibits anomalous behavior.
        
        Args:
            vessel_data: Vessel information dict or feature array
            
        Returns:
            Dict: {
                'is_anomaly': bool,
                'anomaly_score': float (0-10),
                'reconstruction_error': float,
                'threshold': float
            }
        """
```

### `VesselClassifier`

Multi-modal vessel classification using imagery, AIS, and behavioral data.

```python
class VesselClassifier:
    def __init__(self, model_type='random_forest'):
        """
        Initialize vessel classifier.
        
        Args:
            model_type: 'random_forest', 'gradient_boost', 'svm', 'neural_net'
        """

    def extract_imagery_features(self, sar_image_patch: np.array) -> List[float]:
        """
        Extract features from SAR imagery patch.
        
        Args:
            sar_image_patch: Image patch around detected vessel
            
        Returns:
            List[float]: 15 imagery features (intensity, shape, texture)
        """

    def train(self, training_data: List[Dict], labels: List[str]):
        """
        Train vessel classifier.
        
        Args:
            training_data: List of feature dicts with keys:
            - 'imagery': np.array (optional)
            - 'ais_data': Dict (optional)
            - 'vessel_history': Dict (optional) 
            - 'context_data': Dict (optional)
            labels: Vessel type labels
        """

    def predict(self, **kwargs) -> Dict:
        """
        Predict vessel type.
        
        Kwargs:
            imagery_patch, ais_data, vessel_history, context_data
            
        Returns:
            Dict: {
                'vessel_type': str,
                'confidence': float,
                'probabilities': Dict[str, float],
                'risk_score': float
            }
        """
```

## Analysis Module APIs

### `BehaviorPatternAnalyzer`

Analyze individual vessel behavioral patterns.

```python
class BehaviorPatternAnalyzer:
    def analyze_vessel_behavior(self, vessel_id: str, 
                               track_history: List[Dict],
                               time_window_hours: int = 24) -> Dict:
        """
        Analyze behavioral patterns for a single vessel.
        
        Args:
            vessel_id: Unique vessel identifier
            track_history: List of position dicts with:
            - 'latitude': float
            - 'longitude': float  
            - 'timestamp': str (ISO format)
            - 'speed': float (optional)
            - 'heading': float (optional)
            time_window_hours: Analysis window
            
        Returns:
            Dict: {
                'movement_features': Dict,
                'temporal_features': Dict,
                'spatial_features': Dict,
                'pattern_classification': Dict,
                'anomalies': List[Dict],
                'suspicion_score': float,
                'behavioral_assessment': Dict
            }
        """
```

### `FleetPatternAnalyzer`

Detect coordination between multiple vessels.

```python
class FleetPatternAnalyzer:
    def detect_coordinated_behavior(self, vessel_tracks: Dict[str, List[Dict]], 
                                   time_window_hours: int = 6,
                                   proximity_threshold_km: float = 10) -> List[Dict]:
        """
        Detect coordinated behavior between vessels.
        
        Args:
            vessel_tracks: Dict of {vessel_id: track_history}
            time_window_hours: Coordination detection window
            proximity_threshold_km: Distance threshold for coordination
            
        Returns:
            List[Dict]: Coordination events with types:
            - 'spatial_coordination': Vessels in close proximity
            - 'synchronized_start/stop': Coordinated timing
            - 'coordinated_movement': Similar routes
        """
```

### `RiskScorer`

Comprehensive multi-dimensional risk assessment.

```python
class RiskScorer:
    def calculate_comprehensive_risk_score(self, vessel_data: Dict) -> Dict:
        """
        Calculate comprehensive risk score for a vessel.
        
        Args:
            vessel_data: Complete vessel information including:
            - Position data (lat, lon, timestamp)
            - Physical characteristics (length, type, nationality)
            - Behavioral analysis results
            - Historical data
            
        Returns:
            Dict: {
                'overall_risk_score': float (0-10),
                'risk_level': str ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'),
                'component_scores': Dict,
                'risk_factors': List[str],
                'recommendations': List[str]
            }
        """

    def generate_risk_report(self, vessel_assessments: List[Dict]) -> Dict:
        """
        Generate fleet-wide risk assessment report.
        
        Args:
            vessel_assessments: List of risk assessment results
            
        Returns:
            Dict: Comprehensive fleet risk report with statistics and trends
        """
```

## Data Structures

### Standard Vessel Position Format
```python
vessel_position = {
    'vessel_id': str,           # Unique identifier
    'latitude': float,          # WGS84 decimal degrees
    'longitude': float,         # WGS84 decimal degrees
    'timestamp': str,           # ISO 8601 format
    'speed': float,             # km/h (optional)
    'heading': float,           # Degrees 0-360 (optional)
    'source': str              # 'SAR', 'AIS', etc.
}
```

### AIS Message Format
```python
ais_message = {
    'mmsi': str,               # Maritime Mobile Service Identity
    'vessel_name': str,        # Vessel name
    'latitude': float,         # Position
    'longitude': float,
    'speed_over_ground': float, # Knots
    'course_over_ground': float, # Degrees
    'heading': float,          # True heading
    'ship_type': int,          # AIS ship type code
    'length': float,           # Meters
    'width': float,            # Meters
    'timestamp': str           # ISO 8601
}
```

### Risk Assessment Result Format
```python
risk_assessment = {
    'vessel_id': str,
    'overall_risk_score': float,    # 0-10 scale
    'risk_level': str,              # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    'component_scores': {
        'vessel_characteristics': {'score': float, 'details': dict},
        'behavioral_patterns': {'score': float, 'details': dict},
        'location_context': {'score': float, 'details': dict},
        'temporal_factors': {'score': float, 'details': dict},
        'intelligence_indicators': {'score': float, 'details': dict}
    },
    'risk_factors': List[str],      # Human-readable risk factors
    'mitigating_factors': List[str], # Factors reducing risk
    'recommendations': List[str]     # Recommended actions
}
```

## Configuration Parameters

### Detection Thresholds
```python
# Dark vessel detection
MATCHING_THRESHOLD_METERS = 500    # SAR/AIS correlation distance
CONFIDENCE_THRESHOLD = 0.7         # Minimum detection confidence
TIME_TOLERANCE_MINUTES = 30        # Temporal correlation window

# Cable monitoring  
CABLE_PROXIMITY_THRESHOLD_KM = 5   # Alert distance from cables
LOITERING_THRESHOLD_HOURS = 2      # Time threshold for loitering alerts

# Risk scoring
RISK_SCORE_HIGH_THRESHOLD = 6      # High risk threshold
RISK_SCORE_CRITICAL_THRESHOLD = 8  # Critical risk threshold
```

### Machine Learning Parameters
```python
# Autoencoder
AUTOENCODER_INPUT_DIM = 10         # Number of behavioral features
AUTOENCODER_ENCODING_DIM = 5       # Compressed representation size
ANOMALY_THRESHOLD_PERCENTILE = 95  # Threshold based on training errors

# Classification
VESSEL_TYPES = [
    'fishing_vessel', 'cargo_ship', 'tanker', 'naval_vessel',
    'research_vessel', 'patrol_boat', 'submarine', 
    'unknown_military', 'suspicious_civilian'
]
```

## Error Handling Patterns

### Standard Exception Types
```python
class ArcticShadowTrackerError(Exception):
    """Base exception for ArcticShadowTracker"""

class DataProcessingError(ArcticShadowTrackerError):
    """Raised when data processing fails"""

class ModelError(ArcticShadowTrackerError):
    """Raised when ML model operations fail"""

class DetectionError(ArcticShadowTrackerError):
    """Raised when vessel detection fails"""
```

### Logging Configuration
```python
import logging

# Standard logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('arctic_shadow_tracker')
```

This API reference provides Claude Code with detailed interface information for effective assistance with ArcticShadowTracker development and debugging.