"""
Pytest configuration and shared fixtures for ArcticShadowTracker tests.
"""

import pytest
import numpy as np
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock


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


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location/name."""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid.lower() or "end_to_end" in item.name.lower():
            item.add_marker(pytest.mark.integration)
        
        # Mark tests that use actual ML models as slow
        if any(keyword in item.name.lower() for keyword in ["train", "model", "pipeline"]):
            if not item.get_closest_marker("integration"):
                item.add_marker(pytest.mark.slow)