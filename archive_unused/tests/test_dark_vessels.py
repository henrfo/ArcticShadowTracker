"""
Test suite for dark vessel detection functionality.
"""

import pytest
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add parent directory to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detection.dark_vessels import DarkVesselDetector, VesselTracker


class TestDarkVesselDetector:
    """Test class for DarkVesselDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create a detector instance for testing."""
        return DarkVesselDetector(
            matching_threshold_meters=500,
            vessel_size_threshold=20,
            confidence_threshold=0.7
        )
    
    @pytest.fixture
    def sample_sar_detections(self):
        """Sample SAR detections for testing."""
        return [
            {
                'detection_id': 'SAR_001',
                'latitude': 70.5,
                'longitude': 31.2,
                'estimated_length': 80,
                'confidence': 0.85,
                'detection_time': '2024-11-15T10:30:00'
            },
            {
                'detection_id': 'SAR_002',
                'latitude': 69.8,
                'longitude': 30.5,
                'estimated_length': 120,
                'confidence': 0.92,
                'detection_time': '2024-11-15T10:35:00'
            }
        ]
    
    @pytest.fixture
    def sample_ais_data(self):
        """Sample AIS data for testing."""
        return [
            {
                'mmsi': '123456789',
                'latitude': 70.51,  # Close to first SAR detection
                'longitude': 31.21,
                'timestamp': '2024-11-15T10:32:00',
                'vessel_name': 'Test Vessel 1'
            },
            {
                'mmsi': '987654321',
                'latitude': 68.0,   # Far from any SAR detection
                'longitude': 28.0,
                'timestamp': '2024-11-15T10:30:00',
                'vessel_name': 'Test Vessel 2'
            }
        ]
    
    def test_initialization(self, detector):
        """Test detector initialization."""
        assert detector.matching_threshold == 500
        assert detector.size_threshold == 20
        assert detector.confidence_threshold == 0.7
        assert detector.logger is not None
    
    @patch('detection.dark_vessels.rasterio.open')
    @patch('detection.dark_vessels.cv2')
    def test_detect_vessels_in_sar_success(self, mock_cv2, mock_rasterio_open, detector):
        """Test successful vessel detection in SAR imagery."""
        # Mock rasterio file reading
        mock_src = Mock()
        mock_src.read.return_value = np.random.randint(0, 255, (1000, 1000))
        mock_src.transform = Mock()
        mock_src.crs = 'EPSG:4326'
        mock_rasterio_open.return_value.__enter__.return_value = mock_src
        
        # Mock CV2 operations
        mock_cv2.normalize.return_value = np.random.randint(0, 255, (1000, 1000), dtype=np.uint8)
        mock_cv2.GaussianBlur.return_value = np.random.randint(0, 255, (1000, 1000), dtype=np.uint8)
        mock_cv2.morphologyEx.return_value = np.random.randint(0, 255, (1000, 1000), dtype=np.uint8)
        mock_cv2.threshold.return_value = (127, np.random.randint(0, 255, (1000, 1000), dtype=np.uint8))
        
        # Mock contour detection
        mock_contours = [np.array([[100, 100], [120, 100], [120, 120], [100, 120]])]
        mock_cv2.findContours.return_value = (mock_contours, None)
        mock_cv2.contourArea.return_value = 400  # Above threshold
        mock_cv2.boundingRect.return_value = (100, 100, 20, 20)
        mock_cv2.moments.return_value = {"m00": 400, "m10": 44000, "m01": 44000}
        
        # Mock coordinate transformation
        with patch.object(detector, '_pixel_to_geo', return_value=(70.5, 31.2)):
            with patch.object(detector, '_get_pixel_size', return_value=10):
                with patch.object(detector, '_calculate_vessel_confidence', return_value=0.8):
                    detections = detector.detect_vessels_in_sar('test_image.tif')
        
        assert isinstance(detections, list)
        if detections:  # If any detections were made
            detection = detections[0]
            assert 'detection_id' in detection
            assert 'latitude' in detection
            assert 'longitude' in detection
            assert 'confidence' in detection
    
    def test_detect_vessels_in_sar_file_error(self, detector):
        """Test handling of file read errors."""
        with patch('detection.dark_vessels.rasterio.open', side_effect=Exception("File not found")):
            detections = detector.detect_vessels_in_sar('nonexistent.tif')
            assert detections == []
    
    def test_calculate_vessel_confidence(self, detector):
        """Test vessel confidence calculation."""
        # Create mock vessel properties
        vessel_props = {
            'centroid': (500, 500),
            'bounding_box': (490, 490, 20, 20),
            'area': 400,
            'length_pixels': 20,
            'width_pixels': 20,
            'aspect_ratio': 1.0,
            'intensity_mean': 200,
            'intensity_max': 255,
            'intensity_std': 30
        }
        
        # Create mock image
        test_image = np.random.randint(100, 150, (1000, 1000), dtype=np.uint8)
        
        with patch('detection.dark_vessels.cv2.Canny') as mock_canny:
            mock_canny.return_value = np.random.randint(0, 1, (20, 20), dtype=np.uint8) * 255
            
            confidence = detector._calculate_vessel_confidence(vessel_props, test_image)
            
            assert isinstance(confidence, float)
            assert 0 <= confidence <= 1
    
    def test_find_dark_vessels(self, detector, sample_sar_detections, sample_ais_data):
        """Test dark vessel identification."""
        dark_vessels = detector.find_dark_vessels(sample_sar_detections, sample_ais_data)
        
        assert isinstance(dark_vessels, list)
        # First SAR detection should match with first AIS (close proximity)
        # Second SAR detection should be a dark vessel (no matching AIS)
        
        # Check that we have at least one dark vessel
        dark_vessel_ids = [dv['detection_id'] for dv in dark_vessels]
        assert 'SAR_002' in dark_vessel_ids  # This one has no nearby AIS
    
    def test_find_dark_vessels_no_ais(self, detector, sample_sar_detections):
        """Test dark vessel detection with no AIS data."""
        dark_vessels = detector.find_dark_vessels(sample_sar_detections, [])
        
        # All SAR detections should be classified as dark vessels
        assert len(dark_vessels) == len(sample_sar_detections)
        
        for dark_vessel in dark_vessels:
            assert dark_vessel['status'] == 'dark_vessel'
            assert 'risk_score' in dark_vessel
    
    def test_assess_dark_vessel_risk(self, detector):
        """Test dark vessel risk assessment."""
        dark_vessel = {
            'estimated_length': 150,  # Large vessel
            'confidence': 0.9,        # High confidence
            'closest_ais_distance': 75000  # Very isolated
        }
        
        risk_score = detector._assess_dark_vessel_risk(dark_vessel)
        
        assert isinstance(risk_score, float)
        assert 0 <= risk_score <= 10
        assert risk_score > 5  # Should be high risk due to large size and isolation
    
    def test_point_in_bounds(self, detector):
        """Test geographic bounds checking."""
        bounds = (69.0, 30.0, 71.0, 32.0)  # min_lat, min_lon, max_lat, max_lon
        
        assert detector._point_in_bounds(70.0, 31.0, bounds) == True
        assert detector._point_in_bounds(68.0, 31.0, bounds) == False  # Below min_lat
        assert detector._point_in_bounds(72.0, 31.0, bounds) == False  # Above max_lat
        assert detector._point_in_bounds(70.0, 29.0, bounds) == False  # Below min_lon
        assert detector._point_in_bounds(70.0, 33.0, bounds) == False  # Above max_lon
    
    def test_generate_detection_report_empty(self, detector):
        """Test report generation with no detections."""
        report = detector.generate_detection_report([])
        
        assert report['summary']['total_dark_vessels'] == 0
        assert report['summary']['high_risk_vessels'] == 0
        assert report['vessels'] == []
    
    def test_generate_detection_report_with_vessels(self, detector, sample_sar_detections):
        """Test report generation with vessels."""
        # Add risk scores to make them high risk
        for detection in sample_sar_detections:
            detection['risk_score'] = 8.5
        
        report = detector.generate_detection_report(sample_sar_detections)
        
        assert report['summary']['total_dark_vessels'] == 2
        assert report['summary']['high_risk_vessels'] == 2
        assert len(report['vessels']) == 2
        assert 'geographic_bounds' in report['summary']
    
    def test_generate_detection_report_save_file(self, detector, sample_sar_detections):
        """Test report saving to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
            temp_filename = temp_file.name
        
        try:
            report = detector.generate_detection_report(sample_sar_detections, temp_filename)
            
            # Check that file was created
            assert os.path.exists(temp_filename)
            
            # Check file contents
            import json
            with open(temp_filename, 'r') as f:
                saved_report = json.load(f)
            
            assert saved_report['summary']['total_dark_vessels'] == len(sample_sar_detections)
        finally:
            # Clean up
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)


class TestVesselTracker:
    """Test class for VesselTracker."""
    
    @pytest.fixture
    def tracker(self):
        """Create a tracker instance for testing."""
        return VesselTracker()
    
    @pytest.fixture
    def sample_positions(self):
        """Sample position data for testing."""
        base_time = datetime.now() - timedelta(hours=2)
        return [
            {
                'latitude': 70.0,
                'longitude': 30.0,
                'timestamp': (base_time + timedelta(minutes=0)).isoformat()
            },
            {
                'latitude': 70.1,
                'longitude': 30.1,
                'timestamp': (base_time + timedelta(minutes=30)).isoformat()
            },
            {
                'latitude': 70.2,
                'longitude': 30.2,
                'timestamp': (base_time + timedelta(minutes=60)).isoformat()
            }
        ]
    
    def test_initialization(self, tracker):
        """Test tracker initialization."""
        assert tracker.vessel_tracks == {}
        assert tracker.logger is not None
    
    def test_update_vessel_track(self, tracker, sample_positions):
        """Test vessel track updating."""
        vessel_id = "TEST_VESSEL_001"
        
        for position in sample_positions:
            tracker.update_vessel_track(vessel_id, position)
        
        assert vessel_id in tracker.vessel_tracks
        assert len(tracker.vessel_tracks[vessel_id]) == 3
    
    def test_update_vessel_track_old_positions(self, tracker):
        """Test that old positions are removed."""
        vessel_id = "TEST_VESSEL_002"
        
        # Add old position (over 30 days old)
        old_position = {
            'latitude': 70.0,
            'longitude': 30.0,
            'timestamp': (datetime.now() - timedelta(days=35)).isoformat()
        }
        
        # Add recent position
        recent_position = {
            'latitude': 70.1,
            'longitude': 30.1,
            'timestamp': datetime.now().isoformat()
        }
        
        tracker.update_vessel_track(vessel_id, old_position)
        tracker.update_vessel_track(vessel_id, recent_position)
        
        # Should only have the recent position
        assert len(tracker.vessel_tracks[vessel_id]) == 1
        assert tracker.vessel_tracks[vessel_id][0] == recent_position
    
    def test_get_vessel_track(self, tracker, sample_positions):
        """Test vessel track retrieval."""
        vessel_id = "TEST_VESSEL_003"
        
        # Add positions
        for position in sample_positions:
            tracker.update_vessel_track(vessel_id, position)
        
        track = tracker.get_vessel_track(vessel_id)
        assert len(track) == 3
        assert track == sample_positions
        
        # Test non-existent vessel
        empty_track = tracker.get_vessel_track("NONEXISTENT")
        assert empty_track == []
    
    def test_calculate_vessel_statistics(self, tracker, sample_positions):
        """Test vessel statistics calculation."""
        vessel_id = "TEST_VESSEL_004"
        
        # Add positions
        for position in sample_positions:
            tracker.update_vessel_track(vessel_id, position)
        
        stats = tracker.calculate_vessel_statistics(vessel_id)
        
        assert 'total_positions' in stats
        assert 'total_distance_km' in stats
        assert 'average_speed_kmh' in stats
        assert 'max_speed_kmh' in stats
        assert 'operating_area' in stats
        assert 'track_duration_hours' in stats
        
        assert stats['total_positions'] == 3
        assert stats['total_distance_km'] > 0
        assert stats['average_speed_kmh'] >= 0
        assert stats['track_duration_hours'] > 0
    
    def test_calculate_vessel_statistics_insufficient_data(self, tracker):
        """Test statistics calculation with insufficient data."""
        vessel_id = "TEST_VESSEL_005"
        
        # Add only one position
        position = {
            'latitude': 70.0,
            'longitude': 30.0,
            'timestamp': datetime.now().isoformat()
        }
        tracker.update_vessel_track(vessel_id, position)
        
        stats = tracker.calculate_vessel_statistics(vessel_id)
        assert 'error' in stats
    
    def test_calculate_bounding_box_area(self, tracker):
        """Test bounding box area calculation."""
        lats = [70.0, 70.1, 70.2]
        lons = [30.0, 30.1, 30.2]
        
        area = tracker._calculate_bounding_box_area(lats, lons)
        assert isinstance(area, float)
        assert area > 0
        
        # Test with insufficient data
        area_empty = tracker._calculate_bounding_box_area([], [])
        assert area_empty == 0
        
        area_single = tracker._calculate_bounding_box_area([70.0], [30.0])
        assert area_single == 0


class TestDarkVesselDetectionIntegration:
    """Integration tests for dark vessel detection."""
    
    def test_end_to_end_detection_pipeline(self):
        """Test complete detection pipeline."""
        detector = DarkVesselDetector()
        
        # Sample data representing a scenario
        sar_detections = [
            {
                'detection_id': 'SAR_001',
                'latitude': 70.5,
                'longitude': 31.2,
                'estimated_length': 80,
                'confidence': 0.85,
                'detection_time': '2024-11-15T10:30:00'
            },
            {
                'detection_id': 'SAR_002',
                'latitude': 69.8,
                'longitude': 30.5,
                'estimated_length': 120,
                'confidence': 0.92,
                'detection_time': '2024-11-15T10:35:00'
            }
        ]
        
        # AIS data with one vessel that matches first SAR detection
        ais_data = [
            {
                'mmsi': '123456789',
                'latitude': 70.51,  # Close to first SAR detection
                'longitude': 31.21,
                'timestamp': '2024-11-15T10:32:00'
            }
        ]
        
        # Find dark vessels
        dark_vessels = detector.find_dark_vessels(sar_detections, ais_data)
        
        # Second SAR detection should be dark vessel
        assert len(dark_vessels) == 1
        assert dark_vessels[0]['detection_id'] == 'SAR_002'
        
        # Generate report
        report = detector.generate_detection_report(dark_vessels)
        
        assert report['summary']['total_dark_vessels'] == 1
        assert len(report['vessels']) == 1
    
    def test_vessel_tracking_integration(self):
        """Test vessel tracking integration."""
        tracker = VesselTracker()
        detector = DarkVesselDetector()
        
        # Simulate tracking a vessel over time
        vessel_id = "TRACKED_VESSEL_001"
        base_time = datetime.now() - timedelta(hours=5)
        
        positions = []
        for i in range(10):
            position = {
                'latitude': 70.0 + i * 0.01,
                'longitude': 30.0 + i * 0.01,
                'timestamp': (base_time + timedelta(minutes=i * 30)).isoformat()
            }
            positions.append(position)
            tracker.update_vessel_track(vessel_id, position)
        
        # Get statistics
        stats = tracker.calculate_vessel_statistics(vessel_id)
        
        assert stats['total_positions'] == 10
        assert stats['total_distance_km'] > 0
        assert stats['track_duration_hours'] > 4
        
        # Verify track integrity
        track = tracker.get_vessel_track(vessel_id)
        assert len(track) == 10
        assert track[0]['latitude'] == 70.0
        assert track[-1]['latitude'] == 70.09


if __name__ == "__main__":
    pytest.main([__file__])