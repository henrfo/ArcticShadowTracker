# ArcticShadowTracker - Testing Guide

## Overview

This guide provides comprehensive testing strategies and examples for the ArcticShadowTracker project. All tests use synthetic data to ensure reproducible results for educational purposes.

## Test Structure

```
tests/
├── __init__.py
├── test_dark_vessels.py       # Core detection functionality
├── test_autoencoder.py        # ML model testing
├── test_cable_monitor.py      # Infrastructure monitoring
├── test_patterns.py           # Behavioral analysis
├── test_risk_scoring.py       # Risk assessment
├── fixtures/                  # Test data
│   ├── synthetic_sar.py      # Synthetic SAR imagery
│   ├── synthetic_ais.py      # Mock AIS data
│   └── test_scenarios.py     # Common test scenarios
└── integration/               # End-to-end tests
    ├── test_full_pipeline.py
    └── test_notebook_execution.py
```

## Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_dark_vessels.py

# Run with coverage report
pytest --cov=. --cov-report=html

# Run tests with verbose output
pytest -v

# Run only fast tests (skip ML training)
pytest -m "not slow"
```

### Test Categories
```bash
# Unit tests only
pytest tests/ -k "not integration"

# Integration tests only  
pytest tests/integration/

# ML model tests (may be slow)
pytest tests/test_autoencoder.py tests/test_patterns.py
```

## Test Data Generation

### Synthetic SAR Imagery
```python
# tests/fixtures/synthetic_sar.py
import numpy as np
from typing import Tuple, List

def create_synthetic_sar_image(width: int = 1000, height: int = 1000,
                              vessel_positions: List[Tuple[int, int]] = None) -> np.ndarray:
    """
    Create synthetic SAR image with vessel signatures.
    
    Args:
        width, height: Image dimensions
        vessel_positions: List of (x, y) pixel positions for vessels
        
    Returns:
        np.ndarray: Synthetic SAR image with realistic noise and vessel signatures
    """
    # Background noise (Rayleigh distribution for SAR)
    background = np.random.rayleigh(50, (height, width))
    
    # Add vessel signatures
    if vessel_positions:
        for x, y in vessel_positions:
            # Create vessel signature (bright target)
            vessel_signal = create_vessel_signature(size=(20, 60))  # 20x60 pixel vessel
            
            # Place vessel in image
            y_start = max(0, y - vessel_signal.shape[0] // 2)
            y_end = min(height, y_start + vessel_signal.shape[0])
            x_start = max(0, x - vessel_signal.shape[1] // 2)
            x_end = min(width, x_start + vessel_signal.shape[1])
            
            background[y_start:y_end, x_start:x_end] += vessel_signal
    
    return background.astype(np.uint8)

def create_vessel_signature(size: Tuple[int, int] = (20, 60)) -> np.ndarray:
    """Create realistic vessel radar signature."""
    height, width = size
    
    # Vessel shape (elongated bright return)
    vessel = np.zeros((height, width))
    
    # Main hull return
    vessel[height//4:3*height//4, :] = 150
    
    # Superstructure (brighter)
    vessel[height//3:2*height//3, width//4:3*width//4] = 200
    
    # Add some speckle noise
    vessel += np.random.rayleigh(10, vessel.shape)
    
    return vessel
```

### Mock AIS Data
```python
# tests/fixtures/synthetic_ais.py
from datetime import datetime, timedelta
from typing import List, Dict
import random

def create_mock_ais_messages(num_vessels: int = 10, 
                           area_bounds: Tuple[float, float, float, float] = (68.0, 10.0, 82.0, 60.0)
                           ) -> List[Dict]:
    """
    Create mock AIS messages for testing.
    
    Args:
        num_vessels: Number of vessels to simulate
        area_bounds: (min_lat, min_lon, max_lat, max_lon)
        
    Returns:
        List[Dict]: Mock AIS messages
    """
    messages = []
    base_time = datetime.now()
    
    for i in range(num_vessels):
        # Generate vessel characteristics
        vessel_type = random.choice([30, 31, 70, 71, 80, 81])  # Fishing, cargo, tanker
        length = random.uniform(20, 300)
        speed = random.uniform(0, 25)
        
        message = {
            'mmsi': f'25800{i:04d}',
            'vessel_name': f'TEST_VESSEL_{i:03d}',
            'latitude': random.uniform(area_bounds[0], area_bounds[2]),
            'longitude': random.uniform(area_bounds[1], area_bounds[3]),
            'speed_over_ground': speed,
            'course_over_ground': random.uniform(0, 360),
            'heading': random.uniform(0, 360),
            'ship_type': vessel_type,
            'length': length,
            'width': length / random.uniform(3, 8),  # Realistic width ratio
            'timestamp': (base_time - timedelta(minutes=random.randint(0, 60))).isoformat()
        }
        messages.append(message)
    
    return messages
```

### Test Scenarios
```python
# tests/fixtures/test_scenarios.py
from dataclasses import dataclass
from typing import List, Dict, Tuple

@dataclass
class TestScenario:
    name: str
    description: str
    sar_vessels: List[Tuple[float, float]]  # lat, lon positions
    ais_vessels: List[Dict]
    expected_dark_vessels: int
    expected_risk_level: str

# Common test scenarios
STANDARD_SCENARIOS = [
    TestScenario(
        name="normal_traffic",
        description="Normal maritime traffic with all vessels broadcasting AIS",
        sar_vessels=[(70.1, 31.2), (70.3, 31.5), (70.5, 31.8)],
        ais_vessels=[
            {'lat': 70.1, 'lon': 31.2, 'mmsi': '258001001'},
            {'lat': 70.3, 'lon': 31.5, 'mmsi': '258001002'},
            {'lat': 70.5, 'lon': 31.8, 'mmsi': '258001003'}
        ],
        expected_dark_vessels=0,
        expected_risk_level="LOW"
    ),
    
    TestScenario(
        name="dark_vessel_near_cable",
        description="Dark vessel detected near submarine cable",
        sar_vessels=[(78.22, 15.63), (70.2, 31.0)],  # One near Svalbard cable
        ais_vessels=[
            {'lat': 70.2, 'lon': 31.0, 'mmsi': '258001001'}  # Only one has AIS
        ],
        expected_dark_vessels=1,
        expected_risk_level="HIGH"
    ),
    
    TestScenario(
        name="coordinated_vessels",
        description="Multiple vessels in formation without AIS",
        sar_vessels=[(72.0, 32.0), (72.01, 32.01), (72.02, 32.02)],  # Close formation
        ais_vessels=[],  # No AIS
        expected_dark_vessels=3,
        expected_risk_level="CRITICAL"
    )
]
```

## Unit Test Examples

### Dark Vessel Detection Tests
```python
# tests/test_dark_vessels.py
import pytest
import numpy as np
from detection.dark_vessels import DarkVesselDetector
from tests.fixtures.synthetic_sar import create_synthetic_sar_image
from tests.fixtures.synthetic_ais import create_mock_ais_messages

class TestDarkVesselDetector:
    
    @pytest.fixture
    def detector(self):
        return DarkVesselDetector(matching_threshold_meters=500)
    
    @pytest.fixture
    def mock_sar_detections(self):
        return [
            {
                'detection_id': 'SAR_TEST_001',
                'latitude': 70.123,
                'longitude': 31.456,
                'estimated_length': 80.0,
                'confidence': 0.85,
                'detection_time': '2024-11-15T10:30:00'
            },
            {
                'detection_id': 'SAR_TEST_002', 
                'latitude': 70.500,
                'longitude': 32.000,
                'estimated_length': 120.0,
                'confidence': 0.92,
                'detection_time': '2024-11-15T10:32:00'
            }
        ]
    
    @pytest.fixture
    def mock_ais_data(self):
        return [
            {
                'mmsi': '258001001',
                'latitude': 70.124,  # Close to first SAR detection
                'longitude': 31.457,
                'timestamp': '2024-11-15T10:31:00',
                'vessel_name': 'TEST_VESSEL_001'
            }
        ]
    
    def test_find_dark_vessels_basic(self, detector, mock_sar_detections, mock_ais_data):
        """Test basic dark vessel detection functionality."""
        dark_vessels = detector.find_dark_vessels(
            mock_sar_detections, 
            mock_ais_data, 
            time_tolerance_minutes=30
        )
        
        # Should find one dark vessel (second SAR detection has no matching AIS)
        assert len(dark_vessels) == 1
        assert dark_vessels[0]['detection_id'] == 'SAR_TEST_002'
        assert dark_vessels[0]['status'] == 'dark_vessel'
        assert 'risk_score' in dark_vessels[0]
    
    def test_find_dark_vessels_no_ais(self, detector, mock_sar_detections):
        """Test detection when no AIS data available."""
        dark_vessels = detector.find_dark_vessels(mock_sar_detections, [])
        
        # All SAR detections should be marked as dark vessels
        assert len(dark_vessels) == len(mock_sar_detections)
        
    def test_find_dark_vessels_perfect_match(self, detector, mock_sar_detections, mock_ais_data):
        """Test when all SAR detections have matching AIS."""
        # Add matching AIS for second detection
        extended_ais = mock_ais_data + [{
            'mmsi': '258001002',
            'latitude': 70.501,  # Close to second SAR detection
            'longitude': 32.001,
            'timestamp': '2024-11-15T10:33:00',
            'vessel_name': 'TEST_VESSEL_002'
        }]
        
        dark_vessels = detector.find_dark_vessels(mock_sar_detections, extended_ais)
        
        # Should find no dark vessels
        assert len(dark_vessels) == 0
    
    def test_matching_threshold(self, mock_sar_detections, mock_ais_data):
        """Test that matching threshold is respected."""
        # Strict threshold
        strict_detector = DarkVesselDetector(matching_threshold_meters=100)
        dark_vessels_strict = strict_detector.find_dark_vessels(
            mock_sar_detections, mock_ais_data
        )
        
        # Loose threshold  
        loose_detector = DarkVesselDetector(matching_threshold_meters=1000)
        dark_vessels_loose = loose_detector.find_dark_vessels(
            mock_sar_detections, mock_ais_data
        )
        
        # Strict threshold should find more dark vessels (less matching)
        assert len(dark_vessels_strict) >= len(dark_vessels_loose)
    
    def test_time_tolerance(self, detector, mock_sar_detections):
        """Test temporal correlation tolerance."""
        # Old AIS data
        old_ais = [{
            'mmsi': '258001001',
            'latitude': 70.124,
            'longitude': 31.457,
            'timestamp': '2024-11-15T08:00:00',  # 2.5 hours before SAR
            'vessel_name': 'TEST_VESSEL_001'
        }]
        
        # Should not match with default 30-minute tolerance
        dark_vessels = detector.find_dark_vessels(
            mock_sar_detections, old_ais, time_tolerance_minutes=30
        )
        assert len(dark_vessels) == len(mock_sar_detections)
        
        # Should match with extended tolerance
        dark_vessels_extended = detector.find_dark_vessels(
            mock_sar_detections, old_ais, time_tolerance_minutes=180
        )
        assert len(dark_vessels_extended) < len(mock_sar_detections)
```

### Machine Learning Model Tests
```python
# tests/test_autoencoder.py
import pytest
import numpy as np
from models.autoencoder import MaritimeAnomalyDetector, create_synthetic_training_data

class TestMaritimeAnomalyDetector:
    
    @pytest.fixture
    def detector(self):
        return MaritimeAnomalyDetector(input_dim=10, encoding_dim=5)
    
    @pytest.fixture
    def training_data(self):
        """Generate synthetic training data."""
        return create_synthetic_training_data(n_samples=500)
    
    def test_feature_extraction(self, detector):
        """Test feature extraction from vessel data."""
        vessel_data = {
            'distance_to_cable': 5000,
            'distance_to_military_base': 20000,
            'vessel_size': 80,
            'estimated_speed': 12,
            'time_stationary': 2,
            'time_of_day': 14,
            'day_of_week': 2,
            'distance_to_port': 50000,
            'weather_severity': 3,
            'repeat_visits': 2
        }
        
        features = detector.extract_features(vessel_data)
        
        assert features.shape == (1, 10)
        assert np.all(features >= 0)  # All features should be non-negative
    
    @pytest.mark.slow
    def test_training(self, detector, training_data):
        """Test autoencoder training process."""
        history = detector.train(training_data, epochs=10, batch_size=32)
        
        assert detector.model is not None
        assert detector.threshold is not None
        assert detector.threshold > 0
        assert len(history.history['loss']) == 10  # Correct number of epochs
    
    def test_anomaly_prediction(self, detector, training_data):
        """Test anomaly prediction after training."""
        # Train with minimal epochs for testing
        detector.train(training_data, epochs=5)
        
        # Test normal vessel
        normal_vessel = {
            'distance_to_cable': 15000,
            'distance_to_military_base': 30000,
            'vessel_size': 50,
            'estimated_speed': 8,
            'time_stationary': 1,
            'time_of_day': 12,
            'day_of_week': 3,
            'distance_to_port': 40000,
            'weather_severity': 4,
            'repeat_visits': 2
        }
        
        result = detector.predict_anomaly(normal_vessel)
        
        assert 'is_anomaly' in result
        assert 'anomaly_score' in result
        assert 'reconstruction_error' in result
        assert 0 <= result['anomaly_score'] <= 10
    
    def test_suspicious_vessel_detection(self, detector, training_data):
        """Test detection of obviously suspicious behavior."""
        detector.train(training_data, epochs=5)
        
        # Highly suspicious vessel
        suspicious_vessel = {
            'distance_to_cable': 100,      # Very close to cable
            'distance_to_military_base': 2000,  # Near military
            'vessel_size': 80,
            'estimated_speed': 2,          # Very slow
            'time_stationary': 12,         # Long stationary
            'time_of_day': 3,             # Night time
            'day_of_week': 6,             # Weekend
            'distance_to_port': 100000,   # Far from port
            'weather_severity': 1,        # Good weather
            'repeat_visits': 8            # Multiple visits
        }
        
        result = detector.predict_anomaly(suspicious_vessel)
        
        # Should detect as anomaly with high score
        assert result['anomaly_score'] > 5
```

### Integration Tests
```python
# tests/integration/test_full_pipeline.py
import pytest
from detection.dark_vessels import DarkVesselDetector
from detection.cable_monitor import CableMonitor
from analysis.risk_scoring import RiskScorer
from tests.fixtures.test_scenarios import STANDARD_SCENARIOS

class TestFullPipeline:
    
    def test_complete_detection_pipeline(self):
        """Test complete detection and analysis pipeline."""
        scenario = STANDARD_SCENARIOS[1]  # Dark vessel near cable
        
        # Initialize components
        detector = DarkVesselDetector()
        cable_monitor = CableMonitor()
        risk_scorer = RiskScorer()
        
        # Simulate SAR detections
        sar_detections = [
            {
                'detection_id': f'SAR_TEST_{i:03d}',
                'latitude': pos[0],
                'longitude': pos[1],
                'estimated_length': 80.0,
                'confidence': 0.85,
                'detection_time': '2024-11-15T10:30:00'
            }
            for i, pos in enumerate(scenario.sar_vessels)
        ]
        
        # Step 1: Dark vessel detection
        dark_vessels = detector.find_dark_vessels(
            sar_detections, scenario.ais_vessels
        )
        
        assert len(dark_vessels) == scenario.expected_dark_vessels
        
        # Step 2: Cable proximity analysis
        all_vessels = dark_vessels + [
            {
                'vessel_id': ais['mmsi'],
                'latitude': ais['lat'],
                'longitude': ais['lon']
            }
            for ais in scenario.ais_vessels
        ]
        
        vessels_with_cable_info = cable_monitor.check_vessel_cable_proximity(all_vessels)
        
        # Step 3: Risk assessment
        risk_assessments = []
        for vessel in vessels_with_cable_info:
            vessel_data = {
                'vessel_id': vessel.get('vessel_id', vessel.get('detection_id')),
                'latitude': vessel['latitude'],
                'longitude': vessel['longitude'],
                'estimated_length': vessel.get('estimated_length', 80),
                'vessel_type': 'unknown' if 'detection_id' in vessel else 'commercial',
                'ais_data': None if 'detection_id' in vessel else {'mmsi': vessel['vessel_id']}
            }
            
            risk_assessment = risk_scorer.calculate_comprehensive_risk_score(vessel_data)
            risk_assessments.append(risk_assessment)
        
        # Validate expected outcomes
        if scenario.expected_risk_level == "HIGH":
            high_risk_vessels = [r for r in risk_assessments if r['risk_level'] in ['HIGH', 'CRITICAL']]
            assert len(high_risk_vessels) > 0
        
        # Generate final report
        fleet_report = risk_scorer.generate_risk_report(risk_assessments)
        
        assert 'threat_summary' in fleet_report
        assert fleet_report['total_vessels_assessed'] == len(risk_assessments)
```

## Performance Testing

### Benchmark Tests
```python
# tests/test_performance.py
import pytest
import time
import numpy as np
from detection.dark_vessels import DarkVesselDetector

class TestPerformance:
    
    @pytest.mark.slow
    def test_large_dataset_performance(self):
        """Test performance with large datasets."""
        detector = DarkVesselDetector()
        
        # Generate large synthetic dataset
        large_sar_detections = [
            {
                'detection_id': f'SAR_{i:06d}',
                'latitude': 70.0 + np.random.uniform(-5, 5),
                'longitude': 30.0 + np.random.uniform(-10, 10),
                'estimated_length': np.random.uniform(20, 200),
                'confidence': np.random.uniform(0.7, 1.0),
                'detection_time': '2024-11-15T10:30:00'
            }
            for i in range(1000)  # 1000 SAR detections
        ]
        
        large_ais_data = [
            {
                'mmsi': f'25800{i:05d}',
                'latitude': 70.0 + np.random.uniform(-5, 5),
                'longitude': 30.0 + np.random.uniform(-10, 10),
                'timestamp': '2024-11-15T10:30:00',
                'vessel_name': f'VESSEL_{i}'
            }
            for i in range(800)  # 800 AIS messages
        ]
        
        # Measure performance
        start_time = time.time()
        dark_vessels = detector.find_dark_vessels(large_sar_detections, large_ais_data)
        processing_time = time.time() - start_time
        
        # Performance assertions
        assert processing_time < 10.0  # Should complete within 10 seconds
        assert len(dark_vessels) > 0    # Should find some dark vessels
        
        print(f"Processed {len(large_sar_detections)} SAR detections and "
              f"{len(large_ais_data)} AIS messages in {processing_time:.2f} seconds")
```

## Continuous Integration Configuration

### pytest.ini
```ini
[tool:pytest]
minversion = 6.0
addopts = 
    -ra 
    -q 
    --strict-markers
    --disable-warnings
testpaths = tests
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    ml: marks tests as machine learning tests
```

### GitHub Actions Workflow
```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10']
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run fast tests
      run: |
        pytest -m "not slow" --cov=. --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## Test Data Management

### Data Fixtures
- Keep test data small and focused
- Use synthetic data to avoid licensing issues
- Version control test fixtures
- Document expected test outcomes

### Reproducibility
- Set random seeds for consistent results
- Use fixed timestamps in test data
- Document test environment requirements
- Provide clear setup instructions

This testing guide ensures comprehensive validation of ArcticShadowTracker functionality while maintaining the educational focus of the project.