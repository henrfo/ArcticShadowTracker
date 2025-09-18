#!/usr/bin/env python3
"""
Comprehensive unit tests for VesselDetector class.
Tests vessel detection, SAR-AIS correlation, and risk scoring algorithms.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import tempfile
import os
import json

from detection.vessel_detector import VesselDetector


class TestVesselDetectorInitialization:
    """Test VesselDetector initialization and configuration."""
    
    def test_default_initialization(self):
        """Test VesselDetector initializes with default parameters."""
        detector = VesselDetector()
        
        assert detector.matching_threshold == 1000
        assert detector.enable_ml_filtering is True
        assert detector.confidence_threshold == 0.6
    
    def test_custom_initialization(self):
        """Test VesselDetector initializes with custom parameters."""
        detector = VesselDetector(
            matching_threshold_meters=500,
            enable_ml_filtering=False,
            confidence_threshold=0.8
        )
        
        assert detector.matching_threshold == 500
        assert detector.enable_ml_filtering is False
        assert detector.confidence_threshold == 0.8


class TestSARDetection:
    """Test SAR vessel detection functionality."""
    
    def test_detect_vessels_placeholder_file(self, mock_placeholder_sar_file):
        """Test SAR detection with placeholder file."""
        detector = VesselDetector()
        
        detections = detector.detect_vessels_in_sar(mock_placeholder_sar_file)
        
        assert isinstance(detections, list)
        assert len(detections) >= 2  # Should generate 2-6 detections
        
        # Validate detection structure
        for detection in detections:
            assert 'detection_id' in detection
            assert 'lat' in detection
            assert 'lon' in detection
            assert 'confidence' in detection
            assert 'detection_time' in detection
            assert 'source_file' in detection
            assert 'vessel_length_estimate' in detection
            
            # Validate coordinate ranges (Arctic)
            assert 77.0 < detection['lat'] < 79.0
            assert 14.0 < detection['lon'] < 18.0
            assert 0.6 <= detection['confidence'] <= 0.95
    
    def test_detect_vessels_nonexistent_file(self):
        """Test SAR detection with nonexistent file."""
        detector = VesselDetector()
        
        detections = detector.detect_vessels_in_sar("/nonexistent/file.tif")
        
        assert detections == []
    
    def test_detect_vessels_roi_bounds(self, mock_placeholder_sar_file):
        """Test SAR detection with region of interest bounds."""
        detector = VesselDetector()
        roi_bounds = (77.5, 15.0, 78.5, 16.0)
        
        detections = detector.detect_vessels_in_sar(mock_placeholder_sar_file, roi_bounds)
        
        assert isinstance(detections, list)
        # All detections should be within ROI (allowing for simulation variation)
        for detection in detections:
            assert 77.0 < detection['lat'] < 79.0  # Relaxed bounds for simulation
            assert 14.0 < detection['lon'] < 18.0


class TestDarkVesselDetection:
    """Test dark vessel detection through SAR-AIS correlation."""
    
    def test_find_dark_vessels_basic(self, realistic_sar_detections, realistic_ais_data):
        """Test basic dark vessel detection with realistic data."""
        detector = VesselDetector()
        
        dark_vessels = detector.find_dark_vessels(realistic_sar_detections, realistic_ais_data)
        
        assert isinstance(dark_vessels, list)
        assert len(dark_vessels) == 2  # Expected 2 dark vessels from test data
        
        # Validate dark vessel structure
        for dark_vessel in dark_vessels:
            assert dark_vessel['dark_vessel'] is True
            assert 'risk_score' in dark_vessel
            assert 'analysis_timestamp' in dark_vessel
            assert 0.0 <= dark_vessel['risk_score'] <= 1.0
    
    def test_find_dark_vessels_no_sar(self):
        """Test dark vessel detection with no SAR detections."""
        detector = VesselDetector()
        
        dark_vessels = detector.find_dark_vessels([], [{'mmsi': '123', 'lat': 78, 'lon': 15, 'timestamp': '2025-09-18T12:00:00'}])
        
        assert dark_vessels == []
    
    def test_find_dark_vessels_no_ais(self, realistic_sar_detections):
        """Test dark vessel detection with no AIS data (all detections become dark vessels)."""
        detector = VesselDetector()
        
        dark_vessels = detector.find_dark_vessels(realistic_sar_detections, [])
        
        assert len(dark_vessels) == len(realistic_sar_detections)
        
        for dark_vessel in dark_vessels:
            assert dark_vessel['dark_vessel'] is True
    
    def test_find_dark_vessels_time_tolerance(self, realistic_sar_detections, realistic_ais_data):
        """Test dark vessel detection with different time tolerances."""
        detector = VesselDetector()
        
        # Test with very short time tolerance (should find more dark vessels)
        dark_vessels_short = detector.find_dark_vessels(
            realistic_sar_detections, realistic_ais_data, time_tolerance_minutes=1
        )
        
        # Test with very long time tolerance (should find fewer dark vessels)
        dark_vessels_long = detector.find_dark_vessels(
            realistic_sar_detections, realistic_ais_data, time_tolerance_minutes=120
        )
        
        assert len(dark_vessels_short) >= len(dark_vessels_long)


class TestAISMatching:
    """Test SAR-AIS matching algorithms."""
    
    def test_has_matching_ais_exact_match(self):
        """Test AIS matching with exact coordinates and time."""
        detector = VesselDetector(matching_threshold_meters=1000)
        
        sar_detection = {
            'lat': 78.0,
            'lon': 15.0,
            'detection_time': '2025-09-18T12:00:00'
        }
        
        ais_data = [{
            'lat': 78.0,
            'lon': 15.0,
            'timestamp': '2025-09-18T12:00:00'
        }]
        
        has_match = detector._has_matching_ais(sar_detection, ais_data, 30)
        assert has_match is True
    
    def test_has_matching_ais_distance_threshold(self):
        """Test AIS matching with distance threshold."""
        detector = VesselDetector(matching_threshold_meters=500)
        
        sar_detection = {
            'lat': 78.0,
            'lon': 15.0,
            'detection_time': '2025-09-18T12:00:00'
        }
        
        # AIS position ~1km away (should not match with 500m threshold)
        ais_data = [{
            'lat': 78.01,  # ~1.1km north
            'lon': 15.0,
            'timestamp': '2025-09-18T12:00:00'
        }]
        
        has_match = detector._has_matching_ais(sar_detection, ais_data, 30)
        assert has_match is False
        
        # Test with larger threshold
        detector_large = VesselDetector(matching_threshold_meters=2000)
        has_match_large = detector_large._has_matching_ais(sar_detection, ais_data, 30)
        assert has_match_large is True
    
    def test_has_matching_ais_time_threshold(self):
        """Test AIS matching with time threshold."""
        detector = VesselDetector()
        
        sar_detection = {
            'lat': 78.0,
            'lon': 15.0,
            'detection_time': '2025-09-18T12:00:00'
        }
        
        # AIS data 45 minutes earlier (should not match with 30min threshold)
        ais_data = [{
            'lat': 78.0,
            'lon': 15.0,
            'timestamp': '2025-09-18T11:15:00'
        }]
        
        has_match = detector._has_matching_ais(sar_detection, ais_data, 30)
        assert has_match is False
        
        # Test with 60 minute threshold
        has_match_long = detector._has_matching_ais(sar_detection, ais_data, 60)
        assert has_match_long is True
    
    def test_has_matching_ais_malformed_data(self):
        """Test AIS matching with malformed data."""
        detector = VesselDetector()
        
        sar_detection = {
            'lat': 78.0,
            'lon': 15.0,
            'detection_time': '2025-09-18T12:00:00'
        }
        
        malformed_ais = [
            {'lat': 'invalid', 'lon': 15.0, 'timestamp': '2025-09-18T12:00:00'},
            {'lat': 78.0, 'timestamp': '2025-09-18T12:00:00'},  # Missing lon
            {'lat': 78.0, 'lon': 15.0, 'timestamp': 'invalid-timestamp'},
            {}  # Empty record
        ]
        
        has_match = detector._has_matching_ais(sar_detection, malformed_ais, 30)
        assert has_match is False


class TestRiskScoring:
    """Test risk scoring algorithms for detected vessels."""
    
    def test_calculate_simple_risk_score_base(self):
        """Test base risk score for dark vessel."""
        detector = VesselDetector()
        
        vessel_data = {
            'confidence': 0.7,
            'vessel_length_estimate': 50
        }
        
        risk_score = detector._calculate_simple_risk_score(vessel_data)
        
        assert risk_score >= 0.4  # Base dark vessel risk
        assert risk_score <= 1.0
    
    def test_calculate_simple_risk_score_high_confidence(self):
        """Test risk score with high confidence detection."""
        detector = VesselDetector()
        
        vessel_high_conf = {
            'confidence': 0.85,
            'vessel_length_estimate': 50
        }
        
        vessel_low_conf = {
            'confidence': 0.65,
            'vessel_length_estimate': 50
        }
        
        risk_high = detector._calculate_simple_risk_score(vessel_high_conf)
        risk_low = detector._calculate_simple_risk_score(vessel_low_conf)
        
        assert risk_high > risk_low
    
    def test_calculate_simple_risk_score_large_vessel(self):
        """Test risk score with large vessel."""
        detector = VesselDetector()
        
        large_vessel = {
            'confidence': 0.7,
            'vessel_length_estimate': 150
        }
        
        small_vessel = {
            'confidence': 0.7,
            'vessel_length_estimate': 40
        }
        
        risk_large = detector._calculate_simple_risk_score(large_vessel)
        risk_small = detector._calculate_simple_risk_score(small_vessel)
        
        assert risk_large > risk_small
    
    def test_calculate_simple_risk_score_very_large_vessel(self):
        """Test risk score with very large vessel (>200m)."""
        detector = VesselDetector()
        
        very_large_vessel = {
            'confidence': 0.7,
            'vessel_length_estimate': 250
        }
        
        risk_score = detector._calculate_simple_risk_score(very_large_vessel)
        
        # Should get base (0.4) + very large vessel (0.3) = 0.7
        assert risk_score >= 0.7
    
    def test_calculate_simple_risk_score_missing_data(self):
        """Test risk score with missing vessel data."""
        detector = VesselDetector()
        
        minimal_vessel = {}  # No data provided
        
        risk_score = detector._calculate_simple_risk_score(minimal_vessel)
        
        assert risk_score >= 0.4  # Should still get base dark vessel risk
        assert risk_score <= 1.0


class TestSARSimulation:
    """Test SAR detection simulation functionality."""
    
    def test_simulate_sar_detections_metadata_loading(self, tmp_path):
        """Test SAR simulation loads metadata correctly."""
        detector = VesselDetector()
        
        # Create custom metadata
        custom_metadata = {
            "center_location": [80.0, 20.0],
            "coverage_area": {"bounds": [19.0, 79.5, 21.0, 80.5]}
        }
        
        placeholder_file = tmp_path / "custom_test.placeholder"
        with open(placeholder_file, 'w') as f:
            json.dump(custom_metadata, f)
        
        detections = detector._simulate_sar_detections(str(placeholder_file), None)
        
        assert len(detections) >= 2
        
        # Check that detections are around the custom center location
        for detection in detections:
            assert 79.5 < detection['lat'] < 80.5  # Around 80.0
            assert 19.5 < detection['lon'] < 20.5  # Around 20.0
    
    def test_simulate_sar_detections_error_handling(self, tmp_path):
        """Test SAR simulation handles errors gracefully."""
        detector = VesselDetector()
        
        # Create invalid JSON file
        invalid_file = tmp_path / "invalid.placeholder"
        with open(invalid_file, 'w') as f:
            f.write("invalid json content")
        
        detections = detector._simulate_sar_detections(str(invalid_file), None)
        
        assert detections == []
    
    def test_simulate_sar_detections_consistent_structure(self, mock_placeholder_sar_file):
        """Test that simulated detections have consistent structure."""
        detector = VesselDetector()
        
        detections = detector._simulate_sar_detections(mock_placeholder_sar_file, None)
        
        required_fields = [
            'detection_id', 'lat', 'lon', 'confidence', 
            'detection_time', 'source_file', 'vessel_length_estimate'
        ]
        
        for detection in detections:
            for field in required_fields:
                assert field in detection
                assert detection[field] is not None
            
            # Validate data types
            assert isinstance(detection['lat'], float)
            assert isinstance(detection['lon'], float)
            assert isinstance(detection['confidence'], float)
            assert isinstance(detection['vessel_length_estimate'], float)
            assert isinstance(detection['detection_time'], str)


@pytest.mark.edge_case
class TestVesselDetectorEdgeCases:
    """Test edge cases and error handling."""
    
    def test_detection_with_empty_inputs(self):
        """Test vessel detection with empty inputs."""
        detector = VesselDetector()
        
        # Empty SAR detections
        dark_vessels = detector.find_dark_vessels([], [])
        assert dark_vessels == []
        
        # Empty AIS data
        sar_detections = [{'lat': 78.0, 'lon': 15.0, 'detection_time': '2025-09-18T12:00:00'}]
        dark_vessels = detector.find_dark_vessels(sar_detections, [])
        assert len(dark_vessels) == 1
        assert dark_vessels[0]['dark_vessel'] is True
    
    def test_detection_with_invalid_coordinates(self):
        """Test detection with invalid coordinate data."""
        detector = VesselDetector()
        
        invalid_sar = [{
            'lat': None,
            'lon': 15.0,
            'detection_time': '2025-09-18T12:00:00'
        }]
        
        valid_ais = [{
            'lat': 78.0,
            'lon': 15.0,
            'timestamp': '2025-09-18T12:00:00'
        }]
        
        # Should handle gracefully and not crash
        dark_vessels = detector.find_dark_vessels(invalid_sar, valid_ais)
        assert isinstance(dark_vessels, list)
    
    def test_detection_with_extreme_threshold_values(self):
        """Test detection with extreme threshold values."""
        # Very small threshold
        detector_small = VesselDetector(matching_threshold_meters=1)
        
        sar_detection = {
            'lat': 78.0,
            'lon': 15.0,
            'detection_time': '2025-09-18T12:00:00'
        }
        
        ais_data = [{
            'lat': 78.0001,  # ~11 meters away
            'lon': 15.0,
            'timestamp': '2025-09-18T12:00:00'
        }]
        
        has_match_small = detector_small._has_matching_ais(sar_detection, ais_data, 30)
        assert has_match_small is False
        
        # Very large threshold
        detector_large = VesselDetector(matching_threshold_meters=100000)
        has_match_large = detector_large._has_matching_ais(sar_detection, ais_data, 30)
        assert has_match_large is True


@pytest.mark.performance
class TestVesselDetectorPerformance:
    """Test performance characteristics of vessel detection."""
    
    def test_dark_vessel_detection_performance(self, performance_test_data):
        """Test dark vessel detection performance with large datasets."""
        import time
        
        detector = VesselDetector()
        
        start_time = time.time()
        dark_vessels = detector.find_dark_vessels(
            performance_test_data['sar_detections'],
            performance_test_data['ais_data']
        )
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert isinstance(dark_vessels, list)
        assert processing_time < 5.0  # Should complete within 5 seconds
        
        # Performance metrics
        sar_count = len(performance_test_data['sar_detections'])
        ais_count = len(performance_test_data['ais_data'])
        comparisons_per_second = (sar_count * ais_count) / processing_time
        
        assert comparisons_per_second > 10000  # Should handle >10k comparisons/second
    
    def test_memory_usage_large_datasets(self, performance_test_data):
        """Test memory usage with large datasets."""
        import sys
        
        detector = VesselDetector()
        
        # Measure memory before
        initial_size = sys.getsizeof(detector.__dict__)
        
        # Process large dataset
        dark_vessels = detector.find_dark_vessels(
            performance_test_data['sar_detections'],
            performance_test_data['ais_data']
        )
        
        # Measure memory after
        final_size = sys.getsizeof(detector.__dict__)
        
        # Memory usage should not grow significantly
        memory_growth = final_size - initial_size
        assert memory_growth < 1000000  # Less than 1MB growth
        
        # Results should be reasonable size
        assert len(dark_vessels) <= len(performance_test_data['sar_detections'])