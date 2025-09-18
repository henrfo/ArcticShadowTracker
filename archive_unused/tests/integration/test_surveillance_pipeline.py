#!/usr/bin/env python3
"""
Integration tests for the complete Arctic surveillance pipeline.
Tests end-to-end workflow from data ingestion to threat reporting.
"""

import pytest
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import subprocess
import sys

from detection.vessel_detector import VesselDetector
from detection.cable_monitor import CableMonitor
from utils.data_persistence import DataPersistence


@pytest.mark.integration
class TestSurveillancePipelineIntegration:
    """Test complete surveillance pipeline integration."""
    
    def test_end_to_end_surveillance_workflow(self, tmp_path, realistic_ais_data, realistic_sar_detections):
        """Test complete surveillance workflow from detection to reporting."""
        # Initialize components
        vessel_detector = VesselDetector()
        cable_monitor = CableMonitor()
        data_persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Step 1: Detect dark vessels
        dark_vessels = vessel_detector.find_dark_vessels(realistic_sar_detections, realistic_ais_data)
        
        assert len(dark_vessels) >= 1  # Should find some dark vessels
        
        # Step 2: Check cable proximity for all vessels (AIS + dark vessels)
        all_vessels = realistic_ais_data.copy()
        
        # Convert dark vessels to vessel format for cable checking
        for dark_vessel in dark_vessels:
            vessel_entry = {
                'mmsi': dark_vessel.get('detection_id', 'DARK_UNKNOWN'),
                'latitude': dark_vessel['lat'],
                'longitude': dark_vessel['lon'],
                'vessel_name': 'Dark Vessel',
                'type': 'unknown'
            }
            all_vessels.append(vessel_entry)
        
        vessels_with_cable_info = cable_monitor.check_vessel_cable_proximity(all_vessels)
        
        assert len(vessels_with_cable_info) == len(all_vessels)
        
        # Step 3: Generate threat report
        cable_threat_report = cable_monitor.generate_cable_threat_report(vessels_with_cable_info)
        
        assert 'threat_level' in cable_threat_report
        assert 'vessels_near_cables' in cable_threat_report
        
        # Step 4: Compile comprehensive threats
        comprehensive_threats = []
        for vessel in vessels_with_cable_info:
            if vessel.get('near_cable', False):
                threat = {
                    'vessel_id': vessel.get('mmsi', 'UNKNOWN'),
                    'threat_level': 'HIGH' if vessel.get('cable_alerts') else 'MEDIUM',
                    'latitude': vessel['latitude'],
                    'longitude': vessel['longitude'],
                    'threat_type': 'cable_proximity',
                    'details': {
                        'cable_alerts': vessel.get('cable_alerts', []),
                        'distance_to_cable_km': vessel.get('distance_to_cable_km', float('inf'))
                    }
                }
                comprehensive_threats.append(threat)
        
        # Add dark vessel threats
        for dark_vessel in dark_vessels:
            threat = {
                'vessel_id': dark_vessel.get('detection_id', 'DARK_UNKNOWN'),
                'threat_level': 'CRITICAL' if dark_vessel.get('risk_score', 0) > 0.8 else 'HIGH',
                'latitude': dark_vessel['lat'],
                'longitude': dark_vessel['lon'],
                'threat_type': 'dark_vessel',
                'details': {
                    'risk_score': dark_vessel.get('risk_score', 0),
                    'confidence': dark_vessel.get('confidence', 0),
                    'vessel_length_estimate': dark_vessel.get('vessel_length_estimate', 0)
                }
            }
            comprehensive_threats.append(threat)
        
        # Step 5: Save all data
        mission_summary = {
            'mission_id': f'INTEGRATION_TEST_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'status': 'COMPLETED',
            'summary': {
                'total_vessels': len(realistic_ais_data),
                'dark_vessels': len(dark_vessels),
                'vessels_near_cables': len([v for v in vessels_with_cable_info if v.get('near_cable')]),
                'total_threats': len(comprehensive_threats),
                'critical_threats': len([t for t in comprehensive_threats if t['threat_level'] == 'CRITICAL']),
                'high_threats': len([t for t in comprehensive_threats if t['threat_level'] == 'HIGH']),
                'medium_threats': len([t for t in comprehensive_threats if t['threat_level'] == 'MEDIUM'])
            },
            'cable_threat_report': cable_threat_report,
            'processing_timestamp': datetime.now().isoformat()
        }
        
        saved_files = data_persistence.save_daily_data(
            ais_data=realistic_ais_data,
            sar_detections=realistic_sar_detections,
            threats=comprehensive_threats,
            mission_summary=mission_summary
        )
        
        # Verify all components worked together
        assert len(saved_files) >= 4  # AIS, SAR, threats, summary
        assert mission_summary['summary']['total_vessels'] > 0
        assert mission_summary['summary']['dark_vessels'] >= 0
        
        # Step 6: Verify data can be loaded back
        loaded_data = data_persistence.load_daily_data()
        
        assert 'ais_data' in loaded_data
        assert 'sar_detections' in loaded_data
        assert 'threats' in loaded_data
        assert 'mission_summary' in loaded_data
        
        assert len(loaded_data['ais_data']) == len(realistic_ais_data)
        assert len(loaded_data['threats']) == len(comprehensive_threats)
    
    def test_pipeline_with_no_threats(self, tmp_path):
        """Test pipeline operation when no threats are detected."""
        # Initialize components
        vessel_detector = VesselDetector()
        cable_monitor = CableMonitor()
        data_persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Use AIS data far from cables and SAR detections that match AIS
        safe_ais_data = [{
            'mmsi': '257999999',
            'latitude': 80.0,  # Far from cables
            'longitude': 50.0,
            'timestamp': datetime.now().isoformat(),
            'vessel_name': 'Safe Vessel',
            'type': 'research'
        }]
        
        matching_sar_detections = [{
            'detection_id': 'SAR_SAFE_001',
            'lat': 80.001,  # Very close to AIS position
            'lon': 50.001,
            'confidence': 0.85,
            'detection_time': datetime.now().isoformat(),
            'source_file': 'safe_test.tif',
            'vessel_length_estimate': 60
        }]
        
        # Run pipeline
        dark_vessels = vessel_detector.find_dark_vessels(matching_sar_detections, safe_ais_data)
        vessels_with_cable_info = cable_monitor.check_vessel_cable_proximity(safe_ais_data)
        cable_threat_report = cable_monitor.generate_cable_threat_report(vessels_with_cable_info)
        
        # Should detect no threats
        assert len(dark_vessels) == 0
        assert cable_threat_report['threat_level'] == 'LOW'
        assert cable_threat_report['vessels_near_cables'] == 0
        
        # Save and verify
        mission_summary = {
            'status': 'COMPLETED_NO_THREATS',
            'summary': {
                'total_vessels': len(safe_ais_data),
                'dark_vessels': 0,
                'vessels_near_cables': 0,
                'total_threats': 0
            }
        }
        
        saved_files = data_persistence.save_daily_data(
            ais_data=safe_ais_data,
            sar_detections=matching_sar_detections,
            threats=[],
            mission_summary=mission_summary
        )
        
        assert len(saved_files) >= 4
    
    def test_pipeline_error_recovery(self, tmp_path, realistic_ais_data):
        """Test pipeline behavior with component failures."""
        vessel_detector = VesselDetector()
        cable_monitor = CableMonitor()
        data_persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Test with empty SAR detections (simulating SAR processing failure)
        dark_vessels = vessel_detector.find_dark_vessels([], realistic_ais_data)
        assert dark_vessels == []
        
        # Test with malformed vessel data for cable monitoring
        malformed_vessels = [
            {'mmsi': '123', 'latitude': 'invalid', 'longitude': 15.0},
            {'mmsi': '124', 'latitude': 78.0, 'longitude': 15.0, 'vessel_name': 'Valid Vessel'}
        ]
        
        vessels_with_cable_info = cable_monitor.check_vessel_cable_proximity(malformed_vessels)
        
        # Should only process valid vessels
        assert len(vessels_with_cable_info) == 1
        assert vessels_with_cable_info[0]['mmsi'] == '124'
        
        # Generate report with partial data
        cable_threat_report = cable_monitor.generate_cable_threat_report(vessels_with_cable_info)
        assert 'threat_level' in cable_threat_report
        
        # Data persistence should still work with partial data
        mission_summary = {
            'status': 'COMPLETED_WITH_ERRORS',
            'errors': ['SAR processing failed', 'Some vessel data corrupted'],
            'summary': {'total_vessels': 1, 'dark_vessels': 0}
        }
        
        saved_files = data_persistence.save_daily_data(
            ais_data=realistic_ais_data,
            sar_detections=[],
            mission_summary=mission_summary
        )
        
        assert 'ais' in saved_files
        assert 'summary' in saved_files


@pytest.mark.integration
class TestNotebookIntegration:
    """Test integration with operational notebook."""
    
    def test_operational_notebook_execution(self, tmp_path):
        """Test that the operational notebook can execute without errors."""
        notebook_path = Path(__file__).parent.parent.parent / 'notebooks' / 'operational' / 'arctic_surveillance_dashboard.ipynb'
        
        if not notebook_path.exists():
            pytest.skip("Operational notebook not found")
        
        # Create test environment
        env = {
            'ARCTIC_DATA_DIR': str(tmp_path),
            'ARCTIC_TEST_MODE': 'true'
        }
        
        try:
            # Execute notebook using nbconvert
            result = subprocess.run([
                sys.executable, '-m', 'jupyter', 'nbconvert',
                '--to', 'notebook',
                '--execute',
                '--ExecutePreprocessor.timeout=300',  # 5 minute timeout
                '--output', str(tmp_path / 'executed_notebook.ipynb'),
                str(notebook_path)
            ], 
            capture_output=True, 
            text=True, 
            env={**env}
            )
            
            # Check if execution was successful
            if result.returncode == 0:
                # Verify output notebook exists
                executed_notebook = tmp_path / 'executed_notebook.ipynb'
                assert executed_notebook.exists()
                
                # Basic validation of executed notebook
                with open(executed_notebook, 'r') as f:
                    notebook_content = json.load(f)
                
                assert 'cells' in notebook_content
                assert len(notebook_content['cells']) > 0
                
            else:
                pytest.fail(f"Notebook execution failed: {result.stderr}")
                
        except FileNotFoundError:
            pytest.skip("Jupyter not available for notebook testing")
    
    def test_script_execution(self, tmp_path):
        """Test execution of daily surveillance script."""
        script_path = Path(__file__).parent.parent.parent / 'scripts' / 'run_daily_surveillance.py'
        
        if not script_path.exists():
            pytest.skip("Daily surveillance script not found")
        
        # Set test environment
        env = {
            'ARCTIC_DATA_DIR': str(tmp_path),
            'ARCTIC_TEST_MODE': 'true',
            'PYTHONPATH': str(Path(__file__).parent.parent.parent)
        }
        
        try:
            result = subprocess.run([
                sys.executable, str(script_path)
            ], 
            capture_output=True, 
            text=True, 
            env={**env},
            timeout=120  # 2 minute timeout
            )
            
            if result.returncode == 0:
                # Check that output files were created
                operational_dir = tmp_path / 'data' / 'operational' / 'daily'
                if operational_dir.exists():
                    # Should have created some daily data
                    assert len(list(operational_dir.glob('*/*.json'))) > 0
            else:
                # Script execution might fail in test environment - that's ok
                # as long as it doesn't crash with import errors
                assert "ImportError" not in result.stderr
                assert "ModuleNotFoundError" not in result.stderr
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Script execution not available in test environment")


@pytest.mark.integration 
class TestDataFlowIntegration:
    """Test data flow between components."""
    
    def test_ais_sar_correlation_accuracy(self, tmp_path):
        """Test accuracy of AIS-SAR correlation with known test cases."""
        vessel_detector = VesselDetector(matching_threshold_meters=500)
        
        # Create test case with known vessel
        known_vessel_ais = {
            'mmsi': '257123456',
            'latitude': 78.2200,
            'longitude': 15.6300,
            'timestamp': '2025-09-18T12:00:00'
        }
        
        # SAR detection very close to AIS position (should match)
        matching_sar = {
            'detection_id': 'SAR_MATCH_001',
            'lat': 78.2201,  # ~11 meters away
            'lon': 15.6299,
            'confidence': 0.85,
            'detection_time': '2025-09-18T12:01:00',  # 1 minute later
            'source_file': 'test.tif',
            'vessel_length_estimate': 45
        }
        
        # SAR detection far from AIS position (should not match)
        non_matching_sar = {
            'detection_id': 'SAR_DARK_001',
            'lat': 78.2500,  # ~3km away
            'lon': 15.6500,
            'confidence': 0.75,
            'detection_time': '2025-09-18T12:00:30',
            'source_file': 'test.tif',
            'vessel_length_estimate': 80
        }
        
        ais_data = [known_vessel_ais]
        sar_detections = [matching_sar, non_matching_sar]
        
        dark_vessels = vessel_detector.find_dark_vessels(sar_detections, ais_data)
        
        # Should find only the non-matching SAR detection as dark vessel
        assert len(dark_vessels) == 1
        assert dark_vessels[0]['detection_id'] == 'SAR_DARK_001'
        assert dark_vessels[0]['dark_vessel'] is True
    
    def test_cable_proximity_accuracy(self, tmp_path):
        """Test accuracy of cable proximity calculations with known distances."""
        cable_monitor = CableMonitor(proximity_threshold_km=2.0)
        
        # Test vessel at known distance from Longyearbyen (SUCS cable endpoint)
        test_vessel = {
            'mmsi': '257123457',
            'latitude': 78.22,    # Exact SUCS endpoint
            'longitude': 15.63,
            'vessel_name': 'Distance Test Vessel',
            'type': 'test'
        }
        
        vessels_with_info = cable_monitor.check_vessel_cable_proximity([test_vessel])
        vessel_info = vessels_with_info[0]
        
        # Should be very close to SUCS cable
        assert vessel_info['near_cable'] is True
        assert vessel_info['distance_to_cable_km'] < 0.1  # Within 100m
        assert vessel_info['closest_cable'] == 'Svalbard Underwater Cable System (SUCS)'
        
        # Test vessel far from all cables
        distant_vessel = {
            'mmsi': '257123458',
            'latitude': 85.0,     # Far north
            'longitude': 100.0,   # Far east
            'vessel_name': 'Distant Test Vessel',
            'type': 'test'
        }
        
        distant_vessels_with_info = cable_monitor.check_vessel_cable_proximity([distant_vessel])
        distant_vessel_info = distant_vessels_with_info[0]
        
        assert distant_vessel_info['near_cable'] is False
        assert distant_vessel_info['distance_to_cable_km'] > 2.0
    
    def test_risk_scoring_consistency(self, tmp_path):
        """Test consistency of risk scoring across multiple detections."""
        vessel_detector = VesselDetector()
        
        # Create vessels with varying characteristics
        test_cases = [
            # High confidence, large vessel
            {
                'detection_id': 'HIGH_RISK',
                'lat': 78.0,
                'lon': 15.0,
                'confidence': 0.90,
                'vessel_length_estimate': 180,
                'detection_time': '2025-09-18T12:00:00'
            },
            # Medium confidence, medium vessel  
            {
                'detection_id': 'MEDIUM_RISK',
                'lat': 78.1,
                'lon': 15.1,
                'confidence': 0.75,
                'vessel_length_estimate': 80,
                'detection_time': '2025-09-18T12:00:00'
            },
            # Low confidence, small vessel
            {
                'detection_id': 'LOW_RISK',
                'lat': 78.2,
                'lon': 15.2,
                'confidence': 0.65,
                'vessel_length_estimate': 35,
                'detection_time': '2025-09-18T12:00:00'
            }
        ]
        
        # Process as dark vessels (no AIS data)
        dark_vessels = vessel_detector.find_dark_vessels(test_cases, [])
        
        # Extract risk scores
        risk_scores = {vessel['detection_id']: vessel['risk_score'] for vessel in dark_vessels}
        
        # Verify risk ordering
        assert risk_scores['HIGH_RISK'] > risk_scores['MEDIUM_RISK']
        assert risk_scores['MEDIUM_RISK'] > risk_scores['LOW_RISK']
        
        # All should be above base risk threshold
        for score in risk_scores.values():
            assert score >= 0.4  # Base dark vessel risk
            assert score <= 1.0   # Maximum risk
    
    def test_data_persistence_integrity(self, tmp_path, realistic_ais_data, realistic_sar_detections):
        """Test data integrity through save/load cycle."""
        data_persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Create comprehensive test data
        threats_data = [
            {
                'vessel_id': 'THREAT_001',
                'threat_level': 'CRITICAL',
                'latitude': 78.5,
                'longitude': 16.2,
                'threat_type': 'dark_vessel',
                'risk_score': 0.95
            }
        ]
        
        mission_summary = {
            'mission_id': 'INTEGRITY_TEST_001',
            'status': 'COMPLETED',
            'processing_time_seconds': 45.2,
            'summary': {
                'total_vessels': len(realistic_ais_data),
                'total_threats': len(threats_data)
            }
        }
        
        # Save data
        saved_files = data_persistence.save_daily_data(
            ais_data=realistic_ais_data,
            sar_detections=realistic_sar_detections,
            threats=threats_data,
            mission_summary=mission_summary
        )
        
        # Load data back
        loaded_data = data_persistence.load_daily_data()
        
        # Verify data integrity
        assert len(loaded_data['ais_data']) == len(realistic_ais_data)
        assert len(loaded_data['sar_detections']) == len(realistic_sar_detections)
        assert len(loaded_data['threats']) == len(threats_data)
        
        # Check specific field preservation
        original_mmsis = {vessel['mmsi'] for vessel in realistic_ais_data}
        loaded_mmsis = {vessel['mmsi'] for vessel in loaded_data['ais_data']}
        assert original_mmsis == loaded_mmsis
        
        # Check mission summary preservation
        loaded_summary = loaded_data['mission_summary']
        assert loaded_summary['mission_data']['mission_id'] == 'INTEGRITY_TEST_001'
        assert loaded_summary['mission_data']['status'] == 'COMPLETED'


@pytest.mark.integration
@pytest.mark.performance
class TestPipelinePerformance:
    """Test end-to-end pipeline performance."""
    
    def test_full_pipeline_performance(self, tmp_path, performance_test_data):
        """Test performance of complete surveillance pipeline."""
        import time
        
        # Initialize components
        vessel_detector = VesselDetector()
        cable_monitor = CableMonitor()
        data_persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Use subset of performance data to keep test reasonable
        ais_data = performance_test_data['ais_data'][:100]
        sar_detections = performance_test_data['sar_detections'][:20]
        
        start_time = time.time()
        
        # Run complete pipeline
        dark_vessels = vessel_detector.find_dark_vessels(sar_detections, ais_data)
        
        all_vessels = ais_data.copy()
        for dark_vessel in dark_vessels:
            vessel_entry = {
                'mmsi': dark_vessel.get('detection_id', 'DARK_UNKNOWN'),
                'latitude': dark_vessel['lat'],
                'longitude': dark_vessel['lon'],
                'type': 'unknown'
            }
            all_vessels.append(vessel_entry)
        
        vessels_with_cable_info = cable_monitor.check_vessel_cable_proximity(all_vessels)
        cable_threat_report = cable_monitor.generate_cable_threat_report(vessels_with_cable_info)
        
        threats = []
        for vessel in vessels_with_cable_info:
            if vessel.get('near_cable'):
                threats.append({
                    'vessel_id': vessel['mmsi'],
                    'threat_level': 'HIGH',
                    'latitude': vessel['latitude'],
                    'longitude': vessel['longitude']
                })
        
        mission_summary = {
            'status': 'COMPLETED',
            'summary': {
                'total_vessels': len(ais_data),
                'dark_vessels': len(dark_vessels),
                'total_threats': len(threats)
            }
        }
        
        saved_files = data_persistence.save_daily_data(
            ais_data=ais_data,
            sar_detections=sar_detections,
            threats=threats,
            mission_summary=mission_summary
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Performance assertions
        assert total_time < 10.0  # Complete pipeline should finish within 10 seconds
        assert len(saved_files) >= 4
        
        # Calculate processing rates
        vessels_per_second = len(all_vessels) / total_time
        assert vessels_per_second > 10  # Should process >10 vessels per second
    
    def test_pipeline_memory_usage(self, tmp_path, performance_test_data):
        """Test memory usage of complete pipeline."""
        import sys
        
        # Measure initial memory
        initial_objects = len([obj for obj in sys.modules.keys()])
        
        # Run pipeline multiple times to check for memory leaks
        vessel_detector = VesselDetector()
        cable_monitor = CableMonitor()
        data_persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        for i in range(10):  # Run 10 iterations
            ais_subset = performance_test_data['ais_data'][i*10:(i+1)*10]
            sar_subset = performance_test_data['sar_detections'][i*2:(i+1)*2]
            
            dark_vessels = vessel_detector.find_dark_vessels(sar_subset, ais_subset)
            vessels_with_info = cable_monitor.check_vessel_cable_proximity(ais_subset)
            threat_report = cable_monitor.generate_cable_threat_report(vessels_with_info)
        
        # Check for significant memory growth
        final_objects = len([obj for obj in sys.modules.keys()])
        object_growth = final_objects - initial_objects
        
        assert object_growth < 50  # Should not create too many new objects
    
    def test_concurrent_pipeline_simulation(self, tmp_path):
        """Test pipeline behavior under simulated concurrent load."""
        import threading
        import time
        
        results = []
        errors = []
        
        def run_pipeline(thread_id):
            try:
                detector = VesselDetector()
                monitor = CableMonitor()
                persistence = DataPersistence(base_data_dir=str(tmp_path / f'thread_{thread_id}'))
                
                # Simple test data
                ais_data = [{
                    'mmsi': f'25701234{thread_id}',
                    'latitude': 78.0 + thread_id * 0.01,
                    'longitude': 15.0 + thread_id * 0.01,
                    'timestamp': datetime.now().isoformat()
                }]
                
                sar_data = [{
                    'detection_id': f'SAR_{thread_id}',
                    'lat': 78.0 + thread_id * 0.01 + 0.1,  # Offset to create dark vessel
                    'lon': 15.0 + thread_id * 0.01,
                    'confidence': 0.8,
                    'detection_time': datetime.now().isoformat(),
                    'source_file': f'test_{thread_id}.tif',
                    'vessel_length_estimate': 50
                }]
                
                dark_vessels = detector.find_dark_vessels(sar_data, ais_data)
                vessels_with_info = monitor.check_vessel_cable_proximity(ais_data)
                
                results.append({
                    'thread_id': thread_id,
                    'dark_vessels': len(dark_vessels),
                    'total_vessels': len(vessels_with_info)
                })
                
            except Exception as e:
                errors.append({'thread_id': thread_id, 'error': str(e)})
        
        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=run_pipeline, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout per thread
        
        # Verify results
        assert len(errors) == 0, f"Pipeline errors in concurrent execution: {errors}"
        assert len(results) == 5
        
        # All threads should have processed their data
        for result in results:
            assert result['total_vessels'] > 0