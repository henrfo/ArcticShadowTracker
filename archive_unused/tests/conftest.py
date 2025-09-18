"""
Pytest configuration and shared fixtures for ArcticShadowTracker tests.
"""

import pytest
import numpy as np
import tempfile
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing file operations."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_sar_image_data():
    """Generate sample SAR image data for testing."""
    return np.random.randint(0, 255, (1000, 1000), dtype=np.uint8)


@pytest.fixture
def mock_rasterio_dataset():
    """Create a mock rasterio dataset for testing."""
    mock_dataset = Mock()
    mock_dataset.read.return_value = np.random.randint(0, 255, (1000, 1000))
    mock_dataset.transform = Mock()
    mock_dataset.crs = 'EPSG:4326'
    
    # Add transform methods
    def xy_transform(row, col):
        return (15.0 + col * 0.001, 70.0 + row * 0.001)
    
    mock_dataset.transform.xy = xy_transform
    return mock_dataset


@pytest.fixture
def sample_vessel_positions():
    """Generate sample vessel position data."""
    base_time = datetime.now() - timedelta(hours=24)
    positions = []
    
    for i in range(24):  # 24 hours of hourly positions
        position = {
            'latitude': 70.0 + np.random.normal(0, 0.01),
            'longitude': 30.0 + np.random.normal(0, 0.01),
            'timestamp': (base_time + timedelta(hours=i)).isoformat(),
            'speed': np.random.uniform(5, 15),
            'heading': np.random.uniform(0, 360)
        }
        positions.append(position)
    
    return positions


@pytest.fixture
def sample_ais_messages():
    """Generate sample AIS messages."""
    base_time = datetime.now() - timedelta(hours=2)
    messages = []
    
    for i in range(10):
        message = {
            'mmsi': f'12345678{i}',
            'latitude': 70.0 + np.random.normal(0, 0.1),
            'longitude': 30.0 + np.random.normal(0, 0.1),
            'timestamp': (base_time + timedelta(minutes=i * 15)).isoformat(),
            'speed_over_ground': np.random.uniform(0, 20),
            'course_over_ground': np.random.uniform(0, 360),
            'vessel_name': f'Test Vessel {i}',
            'ship_type': np.random.choice([30, 70, 80])  # Fishing, cargo, tanker
        }
        messages.append(message)
    
    return messages


@pytest.fixture
def arctic_coordinates():
    """Provide Arctic coordinate boundaries for testing."""
    return {
        'svalbard': {
            'lat_range': (78.0, 79.0),
            'lon_range': (15.0, 17.0)
        },
        'barents_sea': {
            'lat_range': (69.0, 72.0),
            'lon_range': (30.0, 35.0)
        },
        'norwegian_sea': {
            'lat_range': (68.0, 71.0),
            'lon_range': (20.0, 30.0)
        }
    }


@pytest.fixture
def mock_tensorflow_model():
    """Create a mock TensorFlow model for testing."""
    mock_model = Mock()
    
    # Mock common model methods
    mock_model.fit.return_value = Mock()
    mock_model.predict.return_value = np.random.rand(1, 10)
    mock_model.save = Mock()
    
    # Mock model properties
    mock_model.layers = [Mock() for _ in range(5)]
    mock_model.input_shape = (None, 10)
    mock_model.output_shape = (None, 10)
    
    return mock_model


@pytest.fixture
def sample_cable_data():
    """Generate sample submarine cable data."""
    return [
        {
            'name': 'Test Cable 1',
            'id': 'TC1',
            'route': [(70.0, 30.0), (71.0, 31.0), (72.0, 32.0)],
            'type': 'fiber',
            'capacity': '100Gbps',
            'owner': 'Test Company',
            'year_installed': 2020,
            'depth_range': (100, 2000),
            'critical_sections': []
        },
        {
            'name': 'Test Cable 2',
            'id': 'TC2',
            'route': [(69.0, 29.0), (70.0, 30.0)],
            'type': 'power_fiber',
            'capacity': '50MW + 50Gbps',
            'owner': 'Test Utility',
            'year_installed': 2018,
            'depth_range': (50, 1500),
            'critical_sections': [
                {'start': (69.0, 29.0), 'end': (69.1, 29.1), 'reason': 'landing_site'}
            ]
        }
    ]


@pytest.fixture
def environmental_data():
    """Generate sample environmental data."""
    return {
        'weather': {
            'wind_speed': 15,  # m/s
            'wave_height': 2.5,  # meters
            'visibility': 8000,  # meters
            'temperature': -5,  # Celsius
            'ice_coverage': 0.3  # 30% ice coverage
        },
        'sea_state': 4,  # Beaufort scale
        'daylight_hours': 6,  # hours of daylight
        'moon_phase': 0.75  # 75% illuminated
    }


@pytest.fixture
def vessel_database_entries():
    """Generate sample vessel database entries."""
    return [
        {
            'imo_number': '1234567',
            'mmsi': '123456789',
            'vessel_name': 'Test Fishing Vessel',
            'vessel_type': 'fishing',
            'flag_state': 'NO',
            'length': 45,
            'width': 12,
            'gross_tonnage': 150,
            'year_built': 2010,
            'owner': 'Test Fishing Company AS',
            'classification': 'commercial'
        },
        {
            'imo_number': '7654321',
            'mmsi': '987654321',
            'vessel_name': 'Test Cargo Ship',
            'vessel_type': 'cargo',
            'flag_state': 'DE',
            'length': 180,
            'width': 28,
            'gross_tonnage': 25000,
            'year_built': 2015,
            'owner': 'Test Shipping GmbH',
            'classification': 'commercial'
        }
    ]


@pytest.fixture
def mock_cv2():
    """Create mock OpenCV functions for testing."""
    mock_cv2 = Mock()
    
    # Mock common CV2 functions
    mock_cv2.normalize.return_value = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
    mock_cv2.GaussianBlur.return_value = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
    mock_cv2.threshold.return_value = (127, np.random.randint(0, 255, (100, 100), dtype=np.uint8))
    mock_cv2.findContours.return_value = ([], None)
    mock_cv2.contourArea.return_value = 100
    mock_cv2.boundingRect.return_value = (10, 10, 20, 20)
    mock_cv2.moments.return_value = {"m00": 400, "m10": 6000, "m01": 6000}
    mock_cv2.Canny.return_value = np.random.randint(0, 1, (20, 20), dtype=np.uint8) * 255
    
    # Constants
    mock_cv2.NORM_MINMAX = 32
    mock_cv2.CV_8U = 0
    mock_cv2.THRESH_BINARY = 0
    mock_cv2.THRESH_OTSU = 8
    mock_cv2.RETR_EXTERNAL = 0
    mock_cv2.CHAIN_APPROX_SIMPLE = 2
    mock_cv2.MORPH_TOPHAT = 5
    mock_cv2.MORPH_ELLIPSE = 2
    
    return mock_cv2


@pytest.fixture
def suspicious_behavior_indicators():
    """Generate sample suspicious behavior indicators."""
    return {
        'ais_manipulation': {
            'timestamp': datetime.now().isoformat(),
            'evidence': ['sudden_position_jump', 'impossible_speed'],
            'confidence': 0.85
        },
        'pattern_anomalies': [
            {
                'type': 'loitering',
                'location': (70.5, 31.2),
                'duration_hours': 6,
                'timestamp': datetime.now().isoformat()
            },
            {
                'type': 'rendezvous',
                'vessels': ['VESSEL_001', 'VESSEL_002'],
                'location': (69.8, 30.5),
                'timestamp': datetime.now().isoformat()
            }
        ],
        'communication_anomalies': [
            {
                'type': 'ais_gap',
                'start_time': (datetime.now() - timedelta(hours=8)).isoformat(),
                'end_time': (datetime.now() - timedelta(hours=4)).isoformat(),
                'duration_hours': 4
            }
        ]
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance/benchmark tests"
    )
    config.addinivalue_line(
        "markers", "edge_case: marks tests that handle edge cases and error conditions"
    )


@pytest.fixture
def realistic_ais_data():
    """Generate realistic AIS data for Arctic surveillance testing."""
    base_time = datetime.now()
    vessels = []
    
    # Fishing vessel near Svalbard
    vessels.append({
        'mmsi': '257012340',
        'latitude': 78.2,
        'longitude': 15.6,
        'timestamp': base_time.isoformat(),
        'speed_over_ground': 8.5,
        'course_over_ground': 180,
        'vessel_name': 'Arctic Fisher',
        'ship_type': 30,
        'type': 'fishing'
    })
    
    # Cargo vessel in Barents Sea
    vessels.append({
        'mmsi': '259876543',
        'latitude': 70.5,
        'longitude': 31.2,
        'timestamp': (base_time - timedelta(minutes=15)).isoformat(),
        'speed_over_ground': 12.0,
        'course_over_ground': 45,
        'vessel_name': 'Barents Cargo',
        'ship_type': 70,
        'type': 'cargo'
    })
    
    # Research vessel
    vessels.append({
        'mmsi': '257123456',
        'latitude': 79.0,
        'longitude': 11.9,
        'timestamp': (base_time - timedelta(minutes=5)).isoformat(),
        'speed_over_ground': 5.2,
        'course_over_ground': 270,
        'vessel_name': 'Arctic Research',
        'ship_type': 35,
        'type': 'research'
    })
    
    return vessels


@pytest.fixture
def realistic_sar_detections():
    """Generate realistic SAR detections matching some AIS data."""
    base_time = datetime.now()
    detections = []
    
    # Detection matching fishing vessel (with slight offset)
    detections.append({
        'detection_id': 'SAR_S1A_001',
        'lat': 78.201,  # Slight offset from AIS position
        'lon': 15.599,
        'confidence': 0.85,
        'detection_time': base_time.isoformat(),
        'source_file': 'S1A_test.tif',
        'vessel_length_estimate': 45
    })
    
    # Dark vessel detection (no matching AIS)
    detections.append({
        'detection_id': 'SAR_S1A_002',
        'lat': 78.5,
        'lon': 16.2,
        'confidence': 0.72,
        'detection_time': base_time.isoformat(),
        'source_file': 'S1A_test.tif',
        'vessel_length_estimate': 120
    })
    
    # Another dark vessel near cable
    detections.append({
        'detection_id': 'SAR_S1A_003',
        'lat': 71.17,
        'lon': 25.78,
        'confidence': 0.78,
        'detection_time': base_time.isoformat(),
        'source_file': 'S1A_test.tif',
        'vessel_length_estimate': 85
    })
    
    return detections


@pytest.fixture
def corrupted_test_data():
    """Generate various types of corrupted data for edge case testing."""
    return {
        'invalid_coordinates': [
            {'mmsi': '123456789', 'latitude': 200, 'longitude': 15.0, 'timestamp': '2025-09-18T12:00:00'},
            {'mmsi': '123456790', 'latitude': 78.0, 'longitude': 200, 'timestamp': '2025-09-18T12:00:00'}
        ],
        'missing_fields': [
            {'mmsi': '123456791', 'latitude': 78.0},  # Missing longitude and timestamp
            {'latitude': 78.0, 'longitude': 15.0, 'timestamp': '2025-09-18T12:00:00'}  # Missing MMSI
        ],
        'malformed_timestamps': [
            {'mmsi': '123456792', 'latitude': 78.0, 'longitude': 15.0, 'timestamp': 'not-a-timestamp'},
            {'mmsi': '123456793', 'latitude': 78.0, 'longitude': 15.0, 'timestamp': None}
        ],
        'invalid_types': [
            {'mmsi': '123456794', 'latitude': 'not-a-number', 'longitude': 15.0, 'timestamp': '2025-09-18T12:00:00'},
            {'mmsi': 123456795, 'latitude': 78.0, 'longitude': 15.0, 'timestamp': '2025-09-18T12:00:00'}
        ]
    }


@pytest.fixture
def performance_test_data():
    """Generate large datasets for performance testing."""
    import random
    
    large_ais_dataset = []
    large_sar_dataset = []
    
    # Generate 1000 AIS records
    base_time = datetime.now()
    for i in range(1000):
        large_ais_dataset.append({
            'mmsi': f'25701{i:04d}',
            'latitude': random.uniform(68.0, 82.0),
            'longitude': random.uniform(-10.0, 50.0),
            'timestamp': (base_time - timedelta(minutes=random.randint(0, 1440))).isoformat(),
            'speed_over_ground': random.uniform(0, 25),
            'course_over_ground': random.uniform(0, 360),
            'type': random.choice(['fishing', 'cargo', 'tanker', 'research'])
        })
    
    # Generate 200 SAR detections
    for i in range(200):
        large_sar_dataset.append({
            'detection_id': f'SAR_PERF_{i:03d}',
            'lat': random.uniform(68.0, 82.0),
            'lon': random.uniform(-10.0, 50.0),
            'confidence': random.uniform(0.6, 0.95),
            'detection_time': (base_time - timedelta(minutes=random.randint(0, 120))).isoformat(),
            'source_file': f'test_image_{i//20}.tif',
            'vessel_length_estimate': random.uniform(30, 200)
        })
    
    return {
        'ais_data': large_ais_dataset,
        'sar_detections': large_sar_dataset
    }


@pytest.fixture
def mock_placeholder_sar_file(tmp_path):
    """Create a mock placeholder SAR file for testing."""
    import json
    
    placeholder_data = {
        "type": "placeholder",
        "mission_id": "S1A_IW_GRDH_1SDV_20250918T060000",
        "center_location": [78.22, 15.63],
        "coverage_area": {
            "bounds": [15.0, 77.8, 16.0, 78.6]
        },
        "acquisition_time": "2025-09-18T06:00:00Z",
        "status": "simulated"
    }
    
    placeholder_file = tmp_path / "test_sar_image.placeholder"
    with open(placeholder_file, 'w') as f:
        json.dump(placeholder_data, f)
    
    return str(placeholder_file)


@pytest.fixture
def expected_test_results():
    """Expected results for validation testing."""
    return {
        'dark_vessel_detection': {
            'expected_dark_vessels': 2,  # From realistic test data
            'expected_matched_vessels': 1
        },
        'cable_proximity': {
            'vessels_near_cables': 1,
            'critical_alerts': 0,
            'high_alerts': 0
        },
        'risk_scoring': {
            'min_risk_score': 0.4,  # Base dark vessel risk
            'max_risk_score': 1.0
        }
    }


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location/name."""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid.lower() or "end_to_end" in item.name.lower():
            item.add_marker(pytest.mark.integration)
        
        # Mark performance tests
        if "performance" in item.name.lower() or "benchmark" in item.name.lower():
            item.add_marker(pytest.mark.slow)
        
        # Mark tests that use actual ML models as slow
        if any(keyword in item.name.lower() for keyword in ["train", "model", "pipeline"]):
            if not item.get_closest_marker("integration"):
                item.add_marker(pytest.mark.slow)