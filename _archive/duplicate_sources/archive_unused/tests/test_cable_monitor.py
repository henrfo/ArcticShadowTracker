#!/usr/bin/env python3
"""
Comprehensive unit tests for CableMonitor class.
Tests submarine cable proximity detection and threat assessment.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from geopy.distance import geodesic

from detection.cable_monitor import CableMonitor


class TestCableMonitorInitialization:
    """Test CableMonitor initialization and cable loading."""
    
    def test_default_initialization(self):
        """Test CableMonitor initializes with default parameters."""
        monitor = CableMonitor()
        
        assert monitor.proximity_threshold == 5.0
        assert len(monitor.cables) > 0
        assert isinstance(monitor.cables, list)
    
    def test_custom_threshold_initialization(self):
        """Test CableMonitor initializes with custom proximity threshold."""
        monitor = CableMonitor(proximity_threshold_km=10.0)
        
        assert monitor.proximity_threshold == 10.0
    
    def test_cable_data_structure(self):
        """Test that loaded cable data has correct structure."""
        monitor = CableMonitor()
        
        required_fields = ['name', 'id', 'route', 'type']
        
        for cable in monitor.cables:
            for field in required_fields:
                assert field in cable
            
            # Validate route structure
            assert isinstance(cable['route'], list)
            assert len(cable['route']) >= 2  # At least two points
            
            for point in cable['route']:
                assert isinstance(point, tuple)
                assert len(point) == 2
                lat, lon = point
                assert -90 <= lat <= 90
                assert -180 <= lon <= 180
    
    def test_arctic_cable_loading(self):
        """Test that Arctic-specific cables are loaded."""
        monitor = CableMonitor()
        
        # Check for known Arctic cables
        cable_names = [cable['name'] for cable in monitor.cables]
        
        assert 'Svalbard Underwater Cable System (SUCS)' in cable_names
        assert 'Longyearbyen-Barentsburg Cable' in cable_names
        assert 'Arctic Connect (Planned)' in cable_names
        assert 'Murmansk-Svalbard Research Link' in cable_names
        
        # Verify critical cable designation
        critical_cables = [cable for cable in monitor.cables if cable.get('critical', False)]
        assert len(critical_cables) >= 1


class TestVesselCableProximity:
    """Test vessel proximity checking to submarine cables."""
    
    def test_check_vessel_cable_proximity_basic(self):
        """Test basic vessel cable proximity checking."""
        monitor = CableMonitor(proximity_threshold_km=5.0)
        
        # Vessel near Longyearbyen (close to SUCS cable)
        vessels = [{
            'mmsi': '257012345',
            'latitude': 78.22,
            'longitude': 15.63,
            'vessel_name': 'Test Vessel',
            'type': 'fishing'
        }]
        
        result = monitor.check_vessel_cable_proximity(vessels)
        
        assert len(result) == 1
        vessel_info = result[0]
        
        # Check required fields added
        assert 'near_cable' in vessel_info
        assert 'closest_cable' in vessel_info
        assert 'distance_to_cable_km' in vessel_info
        assert 'cable_alerts' in vessel_info
        
        # Should be near SUCS cable
        assert vessel_info['near_cable'] is True
        assert vessel_info['closest_cable'] == 'Svalbard Underwater Cable System (SUCS)'
        assert vessel_info['distance_to_cable_km'] < 5.0
    
    def test_check_vessel_cable_proximity_far_vessel(self):
        """Test vessel far from any cables."""
        monitor = CableMonitor(proximity_threshold_km=5.0)
        
        # Vessel in open ocean, far from cables
        vessels = [{
            'mmsi': '257012346',
            'latitude': 75.0,  # Far from any cable routes
            'longitude': 50.0,
            'vessel_name': 'Distant Vessel',
            'type': 'cargo'
        }]
        
        result = monitor.check_vessel_cable_proximity(vessels)
        
        assert len(result) == 1
        vessel_info = result[0]
        
        assert vessel_info['near_cable'] is False
        assert vessel_info['distance_to_cable_km'] > 5.0
        assert len(vessel_info['cable_alerts']) == 0
    
    def test_check_vessel_cable_proximity_multiple_vessels(self):
        """Test proximity checking with multiple vessels."""
        monitor = CableMonitor(proximity_threshold_km=10.0)
        
        vessels = [
            # Near Longyearbyen
            {
                'mmsi': '257012347',
                'latitude': 78.2,
                'longitude': 15.6,
                'vessel_name': 'Arctic Vessel 1',
                'type': 'fishing'
            },
            # Near Hammerfest
            {
                'mmsi': '257012348',
                'latitude': 71.17,
                'longitude': 25.78,
                'vessel_name': 'Arctic Vessel 2',
                'type': 'cargo'
            },
            # Far from cables
            {
                'mmsi': '257012349',
                'latitude': 80.0,
                'longitude': 50.0,
                'vessel_name': 'Distant Vessel',
                'type': 'research'
            }
        ]
        
        result = monitor.check_vessel_cable_proximity(vessels)
        
        assert len(result) == 3
        
        # Count vessels near cables
        near_cable_vessels = [v for v in result if v['near_cable']]
        assert len(near_cable_vessels) == 2
    
    def test_check_vessel_cable_proximity_empty_input(self):
        """Test proximity checking with empty vessel list."""
        monitor = CableMonitor()
        
        result = monitor.check_vessel_cable_proximity([])
        
        assert result == []
    
    def test_check_vessel_cable_proximity_malformed_data(self):
        """Test proximity checking with malformed vessel data."""
        monitor = CableMonitor()
        
        malformed_vessels = [
            {'mmsi': '123', 'latitude': 'invalid', 'longitude': 15.0},  # Invalid latitude
            {'mmsi': '124', 'latitude': 78.0},  # Missing longitude
            {'mmsi': '125', 'longitude': 15.0},  # Missing latitude
            {},  # Empty vessel
            {
                'mmsi': '126',
                'latitude': 78.0,
                'longitude': 15.0,
                'vessel_name': 'Valid Vessel'
            }  # Valid vessel for comparison
        ]
        
        result = monitor.check_vessel_cable_proximity(malformed_vessels)
        
        # Should only process valid vessels
        assert len(result) == 1
        assert result[0]['mmsi'] == '126'


class TestCableDistanceCalculation:
    """Test cable distance calculation algorithms."""
    
    def test_calculate_distance_to_cable_point_to_point(self):
        """Test distance calculation to simple two-point cable."""
        monitor = CableMonitor()
        
        # Simple cable from (70, 30) to (71, 31)
        test_cable = {
            'name': 'Test Cable',
            'route': [(70.0, 30.0), (71.0, 31.0)]
        }
        
        # Test point exactly on first endpoint
        distance1 = monitor._calculate_distance_to_cable(70.0, 30.0, test_cable)
        assert distance1 == 0.0
        
        # Test point exactly on second endpoint
        distance2 = monitor._calculate_distance_to_cable(71.0, 31.0, test_cable)
        assert distance2 == 0.0
        
        # Test point near first endpoint
        distance3 = monitor._calculate_distance_to_cable(70.01, 30.01, test_cable)
        assert 0.0 < distance3 < 2.0  # Should be about 1.5km away
    
    def test_calculate_distance_to_cable_multi_segment(self):
        """Test distance calculation to multi-segment cable."""
        monitor = CableMonitor()
        
        # Multi-segment cable
        test_cable = {
            'name': 'Multi-segment Cable',
            'route': [(70.0, 30.0), (71.0, 31.0), (72.0, 32.0)]
        }
        
        # Point near middle segment
        distance = monitor._calculate_distance_to_cable(71.5, 31.5, test_cable)
        assert distance < 100.0  # Should be reasonably close
    
    def test_calculate_distance_to_cable_geodesic_accuracy(self):
        """Test that distance calculation uses geodesic (great circle) distances."""
        monitor = CableMonitor()
        
        # Test against known geodesic calculation
        test_cable = {
            'name': 'Geodesic Test Cable',
            'route': [(78.0, 15.0), (78.0, 16.0)]
        }
        
        test_point_lat, test_point_lon = 78.0, 15.5
        
        calculated_distance = monitor._calculate_distance_to_cable(
            test_point_lat, test_point_lon, test_cable
        )
        
        # Calculate expected distance manually
        expected_distance1 = geodesic((test_point_lat, test_point_lon), (78.0, 15.0)).kilometers
        expected_distance2 = geodesic((test_point_lat, test_point_lon), (78.0, 16.0)).kilometers
        expected_min = min(expected_distance1, expected_distance2)
        
        # Should match within reasonable precision
        assert abs(calculated_distance - expected_min) < 0.1
    
    def test_calculate_distance_to_cable_arctic_coordinates(self):
        """Test distance calculation with Arctic coordinates (high latitude)."""
        monitor = CableMonitor()
        
        # Arctic cable at high latitude
        arctic_cable = {
            'name': 'High Arctic Cable',
            'route': [(85.0, 0.0), (85.0, 180.0)]  # Crosses pole region
        }
        
        # Test point near cable
        distance = monitor._calculate_distance_to_cable(85.01, 90.0, arctic_cable)
        
        assert distance < 500.0  # Should be reasonable distance in Arctic
        assert distance >= 0.0


class TestAlertGeneration:
    """Test cable threat alert generation."""
    
    def test_get_alert_level_critical_cable_close(self):
        """Test alert level for critical cable with close vessel."""
        monitor = CableMonitor()
        
        critical_cable = {'critical': True, 'name': 'Critical Cable'}
        
        # Very close to critical cable
        alert_level = monitor._get_alert_level(0.5, critical_cable)
        assert alert_level == 'CRITICAL'
        
        # Close to critical cable
        alert_level = monitor._get_alert_level(1.5, critical_cable)
        assert alert_level == 'HIGH'
        
        # Within monitoring zone of critical cable
        alert_level = monitor._get_alert_level(3.0, critical_cable)
        assert alert_level == 'MEDIUM'
    
    def test_get_alert_level_non_critical_cable(self):
        """Test alert level for non-critical cable."""
        monitor = CableMonitor()
        
        non_critical_cable = {'critical': False, 'name': 'Regular Cable'}
        
        # Very close to non-critical cable
        alert_level = monitor._get_alert_level(0.5, non_critical_cable)
        assert alert_level == 'HIGH'
        
        # Close to non-critical cable
        alert_level = monitor._get_alert_level(1.5, non_critical_cable)
        assert alert_level == 'MEDIUM'
        
        # Within monitoring zone of non-critical cable
        alert_level = monitor._get_alert_level(3.0, non_critical_cable)
        assert alert_level == 'LOW'
    
    def test_get_alert_level_missing_critical_flag(self):
        """Test alert level with missing critical flag (should default to False)."""
        monitor = CableMonitor()
        
        cable_no_critical = {'name': 'Undefined Cable'}
        
        alert_level = monitor._get_alert_level(0.5, cable_no_critical)
        assert alert_level == 'HIGH'  # Should treat as non-critical
    
    def test_cable_alert_structure(self):
        """Test structure of generated cable alerts."""
        monitor = CableMonitor(proximity_threshold_km=10.0)
        
        vessels = [{
            'mmsi': '257012350',
            'latitude': 78.22,
            'longitude': 15.63,
            'vessel_name': 'Alert Test Vessel',
            'type': 'cargo'
        }]
        
        result = monitor.check_vessel_cable_proximity(vessels)
        vessel_info = result[0]
        
        if vessel_info['cable_alerts']:
            alert = vessel_info['cable_alerts'][0]
            
            required_alert_fields = [
                'cable_name', 'cable_id', 'distance_km', 
                'alert_level', 'timestamp'
            ]
            
            for field in required_alert_fields:
                assert field in alert
            
            assert alert['distance_km'] >= 0.0
            assert alert['alert_level'] in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
            assert isinstance(alert['timestamp'], str)


class TestCableThreatReporting:
    """Test cable threat report generation."""
    
    def test_generate_cable_threat_report_no_vessels(self):
        """Test threat report with no vessels near cables."""
        monitor = CableMonitor()
        
        vessels_with_no_alerts = [{
            'mmsi': '257012351',
            'near_cable': False,
            'cable_alerts': []
        }]
        
        report = monitor.generate_cable_threat_report(vessels_with_no_alerts)
        
        assert report['threat_level'] == 'LOW'
        assert report['vessels_near_cables'] == 0
        assert 'No vessels detected near submarine cables' in report['summary']
    
    def test_generate_cable_threat_report_with_alerts(self):
        """Test threat report with vessels near cables."""
        monitor = CableMonitor()
        
        vessels_with_alerts = [
            {
                'mmsi': '257012352',
                'near_cable': True,
                'cable_alerts': [{
                    'cable_name': 'Test Cable 1',
                    'alert_level': 'HIGH',
                    'distance_km': 1.2
                }]
            },
            {
                'mmsi': '257012353',
                'near_cable': True,
                'cable_alerts': [{
                    'cable_name': 'Test Cable 2',
                    'alert_level': 'MEDIUM',
                    'distance_km': 3.5
                }]
            }
        ]
        
        report = monitor.generate_cable_threat_report(vessels_with_alerts)
        
        assert report['threat_level'] == 'HIGH'  # Highest alert level
        assert report['vessels_near_cables'] == 2
        assert report['alert_counts']['high'] == 1
        assert report['alert_counts']['medium'] == 1
        assert report['alert_counts']['critical'] == 0
    
    def test_generate_cable_threat_report_critical_threat(self):
        """Test threat report with critical threat level."""
        monitor = CableMonitor()
        
        critical_vessel = [{
            'mmsi': '257012354',
            'near_cable': True,
            'cable_alerts': [{
                'cable_name': 'Critical Cable',
                'alert_level': 'CRITICAL',
                'distance_km': 0.3
            }]
        }]
        
        report = monitor.generate_cable_threat_report(critical_vessel)
        
        assert report['threat_level'] == 'CRITICAL'
        assert report['alert_counts']['critical'] == 1
    
    def test_generate_cable_threat_report_structure(self):
        """Test structure of generated threat report."""
        monitor = CableMonitor()
        
        report = monitor.generate_cable_threat_report([])
        
        required_fields = [
            'timestamp', 'threat_level', 'vessels_near_cables', 
            'alert_counts', 'summary'
        ]
        
        for field in required_fields:
            assert field in report
        
        assert 'critical' in report['alert_counts']
        assert 'high' in report['alert_counts']
        assert 'medium' in report['alert_counts']
        
        assert report['threat_level'] in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']


@pytest.mark.edge_case
class TestCableMonitorEdgeCases:
    """Test edge cases and error handling."""
    
    def test_vessel_at_cable_endpoint(self):
        """Test vessel exactly at cable endpoint."""
        monitor = CableMonitor()
        
        # Vessel exactly at Longyearbyen (SUCS cable endpoint)
        vessels = [{
            'mmsi': '257012355',
            'latitude': 78.22,  # Exact SUCS endpoint
            'longitude': 15.63,
            'vessel_name': 'Endpoint Vessel',
            'type': 'supply'
        }]
        
        result = monitor.check_vessel_cable_proximity(vessels)
        vessel_info = result[0]
        
        assert vessel_info['near_cable'] is True
        assert vessel_info['distance_to_cable_km'] < 1.0
    
    def test_vessel_with_extreme_coordinates(self):
        """Test vessel with extreme but valid coordinates."""
        monitor = CableMonitor()
        
        extreme_vessels = [
            {
                'mmsi': '257012356',
                'latitude': 89.9,  # Near North Pole
                'longitude': 0.0,
                'vessel_name': 'Polar Vessel',
                'type': 'research'
            },
            {
                'mmsi': '257012357',
                'latitude': 60.0,  # Southern edge of Arctic
                'longitude': 179.9,
                'vessel_name': 'Edge Vessel',
                'type': 'fishing'
            }
        ]
        
        result = monitor.check_vessel_cable_proximity(extreme_vessels)
        
        assert len(result) == 2
        for vessel_info in result:
            assert 'distance_to_cable_km' in vessel_info
            assert vessel_info['distance_to_cable_km'] >= 0.0
    
    def test_cable_with_single_point_route(self):
        """Test handling of invalid cable with single point route."""
        monitor = CableMonitor()
        
        # Temporarily add invalid cable for testing
        original_cables = monitor.cables.copy()
        monitor.cables.append({
            'name': 'Invalid Single Point Cable',
            'id': 'INVALID',
            'route': [(70.0, 30.0)],  # Only one point
            'type': 'test',
            'critical': False
        })
        
        vessels = [{
            'mmsi': '257012358',
            'latitude': 70.0,
            'longitude': 30.0,
            'vessel_name': 'Test Vessel',
            'type': 'test'
        }]
        
        # Should handle gracefully without crashing
        result = monitor.check_vessel_cable_proximity(vessels)
        assert len(result) == 1
        
        # Restore original cables
        monitor.cables = original_cables
    
    def test_multiple_alerts_same_vessel(self):
        """Test vessel generating multiple cable alerts."""
        monitor = CableMonitor(proximity_threshold_km=50.0)  # Large threshold
        
        # Vessel positioned where it might be near multiple cables
        vessels = [{
            'mmsi': '257012359',
            'latitude': 74.0,  # Between multiple cable routes
            'longitude': 25.0,
            'vessel_name': 'Multi-Alert Vessel',
            'type': 'cargo'
        }]
        
        result = monitor.check_vessel_cable_proximity(vessels)
        vessel_info = result[0]
        
        # Should be able to have multiple alerts
        assert isinstance(vessel_info['cable_alerts'], list)
        # At minimum should track distance to all cables
        assert vessel_info['distance_to_cable_km'] >= 0.0


@pytest.mark.performance
class TestCableMonitorPerformance:
    """Test performance characteristics of cable monitoring."""
    
    def test_proximity_calculation_performance(self, performance_test_data):
        """Test cable proximity calculation performance."""
        import time
        
        monitor = CableMonitor(proximity_threshold_km=10.0)
        
        # Use AIS data as vessel positions
        vessels = []
        for ais_record in performance_test_data['ais_data'][:100]:  # Limit to 100 vessels
            vessels.append({
                'mmsi': ais_record['mmsi'],
                'latitude': ais_record['latitude'],
                'longitude': ais_record['longitude'],
                'type': ais_record.get('type', 'unknown')
            })
        
        start_time = time.time()
        result = monitor.check_vessel_cable_proximity(vessels)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert len(result) == len(vessels)
        assert processing_time < 2.0  # Should complete within 2 seconds
        
        # Calculate vessels processed per second
        vessels_per_second = len(vessels) / processing_time
        assert vessels_per_second > 50  # Should process >50 vessels/second
    
    def test_threat_report_generation_performance(self):
        """Test performance of threat report generation."""
        import time
        
        monitor = CableMonitor()
        
        # Generate many vessels with alerts
        vessels_with_alerts = []
        for i in range(50):
            vessels_with_alerts.append({
                'mmsi': f'25701{i:04d}',
                'near_cable': True,
                'cable_alerts': [{
                    'cable_name': f'Test Cable {i % 5}',
                    'alert_level': ['LOW', 'MEDIUM', 'HIGH'][i % 3],
                    'distance_km': (i % 5) + 1.0
                }]
            })
        
        start_time = time.time()
        report = monitor.generate_cable_threat_report(vessels_with_alerts)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        assert processing_time < 0.1  # Should be very fast
        assert report['vessels_near_cables'] == 50
    
    def test_memory_usage_cable_monitoring(self):
        """Test memory usage of cable monitoring operations."""
        import sys
        
        monitor = CableMonitor()
        
        # Measure initial memory
        initial_size = sys.getsizeof(monitor.__dict__)
        
        # Process vessels multiple times
        test_vessels = [{
            'mmsi': '257012360',
            'latitude': 78.0,
            'longitude': 15.0,
            'type': 'test'
        }]
        
        for _ in range(100):
            result = monitor.check_vessel_cable_proximity(test_vessels)
        
        # Measure final memory
        final_size = sys.getsizeof(monitor.__dict__)
        
        # Memory should not grow significantly
        memory_growth = final_size - initial_size
        assert memory_growth < 100000  # Less than 100KB growth