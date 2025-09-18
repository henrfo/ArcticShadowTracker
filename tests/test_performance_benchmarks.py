#!/usr/bin/env python3
"""
Performance benchmarking tests for ArcticShadowTracker.
Tests processing speed, memory usage, and scalability requirements.
"""

import pytest
import time
import psutil
import os
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock
import numpy as np
import pandas as pd

from detection.vessel_detector import VesselDetector
from detection.cable_monitor import CableMonitor
from utils.data_persistence import DataPersistence


@pytest.mark.performance
class TestVesselDetectionPerformance:
    """Performance tests for vessel detection algorithms."""
    
    def test_dark_vessel_detection_scalability(self, performance_test_data):
        """Test dark vessel detection performance with increasing dataset sizes."""
        detector = VesselDetector()
        
        # Test with different dataset sizes
        sizes = [10, 50, 100, 500, 1000]
        processing_times = []
        
        for size in sizes:
            ais_subset = performance_test_data['ais_data'][:size]
            sar_subset = performance_test_data['sar_detections'][:min(size//5, len(performance_test_data['sar_detections']))]
            
            start_time = time.time()
            dark_vessels = detector.find_dark_vessels(sar_subset, ais_subset)
            end_time = time.time()
            
            processing_time = end_time - start_time
            processing_times.append(processing_time)
            
            # Performance requirements
            if size <= 100:
                assert processing_time < 1.0  # Small datasets: <1 second
            elif size <= 500:
                assert processing_time < 5.0  # Medium datasets: <5 seconds
            else:
                assert processing_time < 10.0  # Large datasets: <10 seconds
            
            assert isinstance(dark_vessels, list)
        
        # Check that processing time doesn't grow exponentially
        # (allowing for some quadratic growth due to correlation algorithm)
        time_ratio = processing_times[-1] / processing_times[0] if processing_times[0] > 0 else 1
        dataset_ratio = sizes[-1] / sizes[0]
        
        # Time growth should be less than dataset_ratio^2 (quadratic upper bound)
        assert time_ratio < dataset_ratio ** 2
    
    def test_sar_ais_correlation_performance(self):
        """Test performance of SAR-AIS correlation algorithm."""
        detector = VesselDetector()
        
        # Generate large synthetic dataset
        base_time = datetime.now()
        large_ais_data = []
        large_sar_data = []
        
        # Create 2000 AIS records
        for i in range(2000):
            large_ais_data.append({
                'mmsi': f'25701{i:04d}',
                'latitude': 70.0 + (i % 100) * 0.01,  # Spread across 1 degree
                'longitude': 30.0 + (i % 100) * 0.01,
                'timestamp': (base_time - timedelta(minutes=i % 60)).isoformat(),
                'type': 'test'
            })
        
        # Create 400 SAR detections (20% of AIS)
        for i in range(400):
            large_sar_data.append({
                'detection_id': f'SAR_PERF_{i:03d}',
                'lat': 70.0 + (i % 100) * 0.01 + 0.001,  # Slight offset
                'lon': 30.0 + (i % 100) * 0.01 + 0.001,
                'confidence': 0.8,
                'detection_time': (base_time - timedelta(minutes=i % 60)).isoformat(),
                'source_file': f'perf_test_{i//20}.tif',
                'vessel_length_estimate': 50 + (i % 100)
            })
        
        start_time = time.time()
        dark_vessels = detector.find_dark_vessels(large_sar_data, large_ais_data)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should complete within reasonable time
        assert processing_time < 15.0  # 15 second maximum
        
        # Calculate performance metrics
        total_comparisons = len(large_sar_data) * len(large_ais_data)
        comparisons_per_second = total_comparisons / processing_time
        
        assert comparisons_per_second > 50000  # Should handle >50k comparisons/second
        
        # Results should be reasonable
        assert isinstance(dark_vessels, list)
        assert len(dark_vessels) <= len(large_sar_data)
    
    def test_risk_scoring_performance(self, performance_test_data):
        """Test performance of risk scoring calculations."""
        detector = VesselDetector()
        
        # Generate many dark vessels for risk scoring
        test_dark_vessels = []
        for i in range(1000):
            vessel = {
                'detection_id': f'RISK_TEST_{i}',
                'lat': 78.0 + (i % 100) * 0.01,
                'lon': 15.0 + (i % 100) * 0.01,
                'confidence': 0.6 + (i % 40) * 0.01,
                'vessel_length_estimate': 30 + (i % 170),
                'detection_time': datetime.now().isoformat()
            }
            test_dark_vessels.append(vessel)
        
        start_time = time.time()
        
        # Calculate risk scores for all vessels
        risk_scores = []
        for vessel in test_dark_vessels:
            risk_score = detector._calculate_simple_risk_score(vessel)
            risk_scores.append(risk_score)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should be very fast
        assert processing_time < 1.0  # Risk scoring should be <1 second for 1000 vessels
        
        vessels_per_second = len(test_dark_vessels) / processing_time
        assert vessels_per_second > 1000  # Should score >1000 vessels per second
        
        # All scores should be valid
        assert all(0.0 <= score <= 1.0 for score in risk_scores)
        assert len(risk_scores) == len(test_dark_vessels)


@pytest.mark.performance 
class TestCableMonitoringPerformance:
    """Performance tests for cable monitoring system."""
    
    def test_cable_proximity_calculation_performance(self):
        """Test performance of cable proximity calculations."""
        monitor = CableMonitor(proximity_threshold_km=10.0)
        
        # Generate many vessels across Arctic region
        test_vessels = []
        for i in range(500):
            test_vessels.append({
                'mmsi': f'25701{i:03d}',
                'latitude': 68.0 + (i % 20) * 0.7,  # 68-82 degrees North
                'longitude': -10.0 + (i % 30) * 2.0,  # -10 to 50 degrees East
                'vessel_name': f'Performance Test Vessel {i}',
                'type': 'test'
            })
        
        start_time = time.time()
        vessels_with_info = monitor.check_vessel_cable_proximity(test_vessels)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Performance requirements
        assert processing_time < 3.0  # Should complete within 3 seconds
        
        vessels_per_second = len(test_vessels) / processing_time
        assert vessels_per_second > 150  # Should process >150 vessels per second
        
        # Verify all vessels were processed
        assert len(vessels_with_info) == len(test_vessels)
        
        # Check that all required fields were added
        for vessel in vessels_with_info:
            assert 'near_cable' in vessel
            assert 'distance_to_cable_km' in vessel
            assert 'cable_alerts' in vessel
    
    def test_distance_calculation_accuracy_vs_speed(self):
        """Test tradeoff between distance calculation accuracy and speed."""
        monitor = CableMonitor()
        
        # Test points at various distances from known cable endpoints
        test_points = [
            (78.22, 15.63),    # Longyearbyen (SUCS endpoint)
            (78.225, 15.635),  # Very close to Longyearbyen
            (78.3, 15.8),      # Nearby
            (79.0, 16.0),      # Medium distance
            (80.0, 20.0),      # Far
            (85.0, 50.0)       # Very far
        ]
        
        # Test cable (SUCS)
        test_cable = monitor.cables[0]  # Should be SUCS
        
        start_time = time.time()
        
        distances = []
        for lat, lon in test_points:
            distance = monitor._calculate_distance_to_cable(lat, lon, test_cable)
            distances.append(distance)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should be very fast for few points
        assert processing_time < 0.1  # <100ms for 6 distance calculations
        
        # Verify distance ordering makes sense
        assert distances[0] < distances[1] < distances[2]  # Closer points should have smaller distances
        assert distances[-1] > distances[-2]  # Farthest point should have largest distance
        
        # All distances should be non-negative
        assert all(d >= 0 for d in distances)
    
    def test_alert_generation_performance(self):
        """Test performance of cable alert generation."""
        monitor = CableMonitor(proximity_threshold_km=50.0)  # Large threshold to generate many alerts
        
        # Generate vessels near cable routes
        vessels_near_cables = []
        for i in range(100):
            # Place vessels near various cable endpoints
            base_positions = [(78.22, 15.63), (71.17, 25.78), (68.97, 33.08)]
            base_lat, base_lon = base_positions[i % len(base_positions)]
            
            vessels_near_cables.append({
                'mmsi': f'25702{i:03d}',
                'latitude': base_lat + (i % 10) * 0.01,
                'longitude': base_lon + (i % 10) * 0.01,
                'vessel_name': f'Alert Test Vessel {i}',
                'type': 'test'
            })
        
        start_time = time.time()
        vessels_with_alerts = monitor.check_vessel_cable_proximity(vessels_near_cables)
        threat_report = monitor.generate_cable_threat_report(vessels_with_alerts)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should handle alert generation quickly
        assert processing_time < 2.0  # <2 seconds for 100 vessels
        
        # Verify threat report was generated
        assert 'threat_level' in threat_report
        assert 'vessels_near_cables' in threat_report
        assert 'alert_counts' in threat_report
        
        # Should have found vessels near cables
        near_cable_count = sum(1 for v in vessels_with_alerts if v.get('near_cable', False))
        assert near_cable_count > 0
    
    def test_concurrent_cable_monitoring(self):
        """Test cable monitoring performance under concurrent access."""
        import concurrent.futures
        
        monitor = CableMonitor()
        
        def process_vessel_batch(batch_id):
            vessels = []
            for i in range(20):  # 20 vessels per batch
                vessels.append({
                    'mmsi': f'257{batch_id:02d}{i:02d}',
                    'latitude': 78.0 + batch_id * 0.1 + i * 0.01,
                    'longitude': 15.0 + batch_id * 0.1 + i * 0.01,
                    'type': 'concurrent_test'
                })
            
            start_time = time.time()
            result = monitor.check_vessel_cable_proximity(vessels)
            end_time = time.time()
            
            return {
                'batch_id': batch_id,
                'processing_time': end_time - start_time,
                'vessels_processed': len(result)
            }
        
        # Run 10 concurrent batches
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_vessel_batch, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete all batches within reasonable time
        assert total_time < 5.0  # 5 seconds for all concurrent batches
        
        # All batches should have completed successfully
        assert len(results) == 10
        
        total_vessels = sum(result['vessels_processed'] for result in results)
        assert total_vessels == 200  # 10 batches * 20 vessels each


@pytest.mark.performance
class TestDataPersistencePerformance:
    """Performance tests for data persistence operations."""
    
    def test_large_dataset_save_performance(self, tmp_path):
        """Test saving performance with large datasets."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Generate large AIS dataset
        large_ais_data = []
        for i in range(5000):
            large_ais_data.append({
                'mmsi': f'25701{i:04d}',
                'latitude': 68.0 + (i % 1000) * 0.01,
                'longitude': -10.0 + (i % 1000) * 0.06,
                'timestamp': (datetime.now() - timedelta(minutes=i % 1440)).isoformat(),
                'speed_over_ground': (i % 30),
                'course_over_ground': (i % 360),
                'vessel_name': f'Large Dataset Vessel {i}',
                'ship_type': 30 + (i % 8) * 10,
                'type': ['fishing', 'cargo', 'tanker'][i % 3]
            })
        
        # Generate SAR detections
        large_sar_data = []
        for i in range(1000):
            large_sar_data.append({
                'detection_id': f'SAR_LARGE_{i:04d}',
                'lat': 68.0 + (i % 200) * 0.05,
                'lon': -10.0 + (i % 200) * 0.3,
                'confidence': 0.6 + (i % 35) * 0.01,
                'detection_time': (datetime.now() - timedelta(minutes=i % 120)).isoformat(),
                'source_file': f'large_dataset_{i//50}.tif',
                'vessel_length_estimate': 30 + (i % 170)
            })
        
        # Generate threats
        large_threats_data = []
        for i in range(500):
            large_threats_data.append({
                'vessel_id': f'THREAT_LARGE_{i:03d}',
                'threat_level': ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'][i % 4],
                'latitude': 68.0 + (i % 100) * 0.1,
                'longitude': -10.0 + (i % 100) * 0.6,
                'threat_type': ['dark_vessel', 'cable_proximity', 'anomalous_behavior'][i % 3],
                'risk_score': 0.3 + (i % 70) * 0.01,
                'timestamp': datetime.now().isoformat()
            })
        
        mission_summary = {
            'mission_id': 'LARGE_DATASET_PERF_TEST',
            'status': 'COMPLETED',
            'summary': {
                'total_vessels': len(large_ais_data),
                'sar_detections': len(large_sar_data),
                'total_threats': len(large_threats_data)
            }
        }
        
        # Test save performance
        start_time = time.time()
        saved_files = persistence.save_daily_data(
            ais_data=large_ais_data,
            sar_detections=large_sar_data,
            threats=large_threats_data,
            mission_summary=mission_summary
        )
        end_time = time.time()
        
        save_time = end_time - start_time
        
        # Performance requirements
        assert save_time < 10.0  # Should save within 10 seconds
        
        total_records = len(large_ais_data) + len(large_sar_data) + len(large_threats_data)
        records_per_second = total_records / save_time
        assert records_per_second > 500  # Should save >500 records/second
        
        # Verify files were created
        assert len(saved_files) >= 4
        for file_path in saved_files.values():
            assert os.path.exists(file_path)
    
    def test_data_loading_performance(self, tmp_path, performance_test_data):
        """Test data loading performance."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # First save the performance test data
        test_date = '2025-09-18'
        mission_summary = {'status': 'COMPLETED', 'summary': {'test': True}}
        
        persistence.save_daily_data(
            ais_data=performance_test_data['ais_data'],
            sar_detections=performance_test_data['sar_detections'],
            mission_summary=mission_summary,
            date_str=test_date
        )
        
        # Test loading performance
        start_time = time.time()
        loaded_data = persistence.load_daily_data(test_date)
        end_time = time.time()
        
        load_time = end_time - start_time
        
        # Should load quickly
        assert load_time < 2.0  # Should load within 2 seconds
        
        # Verify data completeness
        assert len(loaded_data['ais_data']) == len(performance_test_data['ais_data'])
        assert len(loaded_data['sar_detections']) == len(performance_test_data['sar_detections'])
    
    def test_historical_summary_performance(self, tmp_path):
        """Test performance of historical summary generation."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Create historical data for many days
        days_to_create = 90  # 3 months of data
        
        data_creation_start = time.time()
        
        for i in range(days_to_create):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            
            # Create moderate amount of data per day
            daily_ais = []
            for j in range(50):  # 50 vessels per day
                daily_ais.append({
                    'mmsi': f'257{i:02d}{j:02d}',
                    'latitude': 78.0 + j * 0.01,
                    'longitude': 15.0 + j * 0.01,
                    'timestamp': f'2025-09-{18-i//30}T12:00:00'
                })
            
            mission_summary = {
                'mission_id': f'HIST_PERF_{date}',
                'data_counts': {
                    'ais_vessels': len(daily_ais),
                    'sar_detections': i % 10 + 5,
                    'threats_detected': i % 5
                },
                'mission_data': {
                    'summary': {
                        'critical_threats': i % 2,
                        'high_threats': i % 3 + 1,
                        'dark_vessels': i % 4
                    }
                }
            }
            
            persistence.save_daily_data(
                ais_data=daily_ais,
                mission_summary=mission_summary,
                date_str=date
            )
        
        data_creation_end = time.time()
        data_creation_time = data_creation_end - data_creation_start
        
        # Test historical summary generation performance
        summary_start = time.time()
        historical_summary = persistence.get_historical_summary(days_back=days_to_create)
        summary_end = time.time()
        
        summary_time = summary_end - summary_start
        
        # Performance requirements
        assert summary_time < 5.0  # Should generate summary within 5 seconds
        
        # Data creation should be reasonable too
        assert data_creation_time < 30.0  # Should create test data within 30 seconds
        
        # Verify summary completeness
        assert isinstance(historical_summary, pd.DataFrame)
        assert len(historical_summary) <= days_to_create
        assert len(historical_summary) > 0
        
        days_per_second = len(historical_summary) / summary_time
        assert days_per_second > 10  # Should process >10 days per second
    
    def test_data_validation_performance(self, tmp_path):
        """Test data validation performance with various data qualities."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Create dataset with mixed data quality
        mixed_quality_data = []
        
        # 80% good data
        for i in range(800):
            mixed_quality_data.append({
                'mmsi': f'25701{i:04d}',
                'latitude': 78.0 + (i % 100) * 0.01,
                'longitude': 15.0 + (i % 100) * 0.01,
                'timestamp': datetime.now().isoformat()
            })
        
        # 20% problematic data
        for i in range(200):
            if i % 5 == 0:
                # Missing fields
                mixed_quality_data.append({'mmsi': f'257BAD{i:03d}'})
            elif i % 5 == 1:
                # Invalid coordinates
                mixed_quality_data.append({
                    'mmsi': f'257BAD{i:03d}',
                    'latitude': 200.0,  # Invalid
                    'longitude': 15.0,
                    'timestamp': datetime.now().isoformat()
                })
            elif i % 5 == 2:
                # Invalid timestamp
                mixed_quality_data.append({
                    'mmsi': f'257BAD{i:03d}',
                    'latitude': 78.0,
                    'longitude': 15.0,
                    'timestamp': 'not-a-timestamp'
                })
            elif i % 5 == 3:
                # Wrong data types
                mixed_quality_data.append({
                    'mmsi': f'257BAD{i:03d}',
                    'latitude': 'seventy-eight',
                    'longitude': 15.0,
                    'timestamp': datetime.now().isoformat()
                })
            else:
                # Empty/null values
                mixed_quality_data.append({
                    'mmsi': f'257BAD{i:03d}',
                    'latitude': None,
                    'longitude': 15.0,
                    'timestamp': datetime.now().isoformat()
                })
        
        start_time = time.time()
        cleaned_data, quality_report = persistence._validate_data_quality(mixed_quality_data, 'ais')
        end_time = time.time()
        
        validation_time = end_time - start_time
        
        # Performance requirements
        assert validation_time < 2.0  # Should validate 1000 records within 2 seconds
        
        records_per_second = len(mixed_quality_data) / validation_time
        assert records_per_second > 500  # Should validate >500 records/second
        
        # Validation effectiveness
        assert len(cleaned_data) == 800  # Should keep good data
        assert quality_report['records_rejected'] == 200  # Should reject bad data
        assert quality_report['error_rate'] == 0.2  # 20% error rate


@pytest.mark.performance
class TestSystemResourceUsage:
    """Test system resource usage and limits."""
    
    def test_memory_usage_monitoring(self, tmp_path, performance_test_data):
        """Test memory usage during various operations."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Initialize components
        detector = VesselDetector()
        monitor = CableMonitor()
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        memory_after_init = process.memory_info().rss / 1024 / 1024
        init_memory_growth = memory_after_init - initial_memory
        
        # Initialization should not use excessive memory
        assert init_memory_growth < 50  # Less than 50MB for initialization
        
        # Perform intensive operations
        dark_vessels = detector.find_dark_vessels(
            performance_test_data['sar_detections'],
            performance_test_data['ais_data']
        )
        
        memory_after_detection = process.memory_info().rss / 1024 / 1024
        
        vessels_with_info = monitor.check_vessel_cable_proximity(performance_test_data['ais_data'])
        
        memory_after_cable_check = process.memory_info().rss / 1024 / 1024
        
        saved_files = persistence.save_daily_data(
            ais_data=performance_test_data['ais_data'],
            sar_detections=performance_test_data['sar_detections'],
            threats=dark_vessels
        )
        
        memory_after_save = process.memory_info().rss / 1024 / 1024
        
        # Memory growth should be reasonable
        total_memory_growth = memory_after_save - initial_memory
        assert total_memory_growth < 200  # Less than 200MB total growth
        
        # Individual operations should not cause excessive memory growth
        detection_growth = memory_after_detection - memory_after_init
        cable_growth = memory_after_cable_check - memory_after_detection
        save_growth = memory_after_save - memory_after_cable_check
        
        assert detection_growth < 100  # Dark vessel detection: <100MB
        assert cable_growth < 50      # Cable checking: <50MB
        assert save_growth < 50       # Data saving: <50MB
    
    def test_cpu_usage_efficiency(self, performance_test_data):
        """Test CPU usage efficiency of core algorithms."""
        detector = VesselDetector()
        monitor = CableMonitor()
        
        # Monitor CPU usage during processing
        start_cpu_times = psutil.cpu_times()
        start_time = time.time()
        
        # Perform CPU-intensive operations
        for _ in range(10):  # Run multiple iterations
            dark_vessels = detector.find_dark_vessels(
                performance_test_data['sar_detections'][:50],
                performance_test_data['ais_data'][:200]
            )
            
            vessels_with_info = monitor.check_vessel_cable_proximity(
                performance_test_data['ais_data'][:100]
            )
        
        end_time = time.time()
        end_cpu_times = psutil.cpu_times()
        
        # Calculate CPU efficiency
        total_cpu_time = (end_cpu_times.user - start_cpu_times.user) + (end_cpu_times.system - start_cpu_times.system)
        wall_clock_time = end_time - start_time
        
        cpu_efficiency = total_cpu_time / wall_clock_time if wall_clock_time > 0 else 0
        
        # Should be using CPU efficiently (but not 100% due to I/O, memory access, etc.)
        assert 0.1 < cpu_efficiency < 0.9  # Between 10% and 90% CPU utilization
        
        # Should complete within reasonable time
        assert wall_clock_time < 30.0  # 30 seconds max for all iterations
    
    def test_concurrent_processing_resource_usage(self, tmp_path):
        """Test resource usage under concurrent processing load."""
        import concurrent.futures
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        def processing_task(task_id):
            # Each task processes a moderate amount of data
            detector = VesselDetector()
            monitor = CableMonitor()
            persistence = DataPersistence(base_data_dir=str(tmp_path / f'task_{task_id}'))
            
            ais_data = []
            for i in range(100):
                ais_data.append({
                    'mmsi': f'257{task_id:02d}{i:02d}',
                    'latitude': 78.0 + task_id * 0.1 + i * 0.01,
                    'longitude': 15.0 + task_id * 0.1 + i * 0.01,
                    'timestamp': datetime.now().isoformat()
                })
            
            sar_data = []
            for i in range(20):
                sar_data.append({
                    'detection_id': f'SAR_{task_id}_{i}',
                    'lat': 78.0 + task_id * 0.1 + i * 0.05,
                    'lon': 15.0 + task_id * 0.1 + i * 0.05,
                    'confidence': 0.7,
                    'detection_time': datetime.now().isoformat(),
                    'source_file': f'concurrent_test_{task_id}.tif',
                    'vessel_length_estimate': 50
                })
            
            dark_vessels = detector.find_dark_vessels(sar_data, ais_data)
            vessels_with_info = monitor.check_vessel_cable_proximity(ais_data[:50])
            
            saved_files = persistence.save_daily_data(
                ais_data=ais_data,
                sar_detections=sar_data,
                threats=dark_vessels
            )
            
            return {
                'task_id': task_id,
                'dark_vessels': len(dark_vessels),
                'saved_files': len(saved_files)
            }
        
        start_time = time.time()
        
        # Run 8 concurrent tasks
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(processing_task, i) for i in range(8)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        end_time = time.time()
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        # Resource usage assertions
        assert end_time - start_time < 20.0  # Should complete within 20 seconds
        assert memory_growth < 300  # Memory growth should be <300MB
        assert len(results) == 8  # All tasks should complete
        
        # Each task should have processed data successfully
        for result in results:
            assert result['saved_files'] >= 3  # Should have saved at least 3 files
    
    def test_disk_io_performance(self, tmp_path):
        """Test disk I/O performance for data persistence."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Generate data of various sizes
        small_data = [{'id': i, 'data': f'small_{i}'} for i in range(100)]
        medium_data = [{'id': i, 'data': f'medium_{i}' * 10} for i in range(1000)]
        large_data = [{'id': i, 'data': f'large_{i}' * 100} for i in range(5000)]
        
        # Test save performance for different sizes
        datasets = [
            ('small', small_data),
            ('medium', medium_data),
            ('large', large_data)
        ]
        
        io_performance = {}
        
        for name, data in datasets:
            start_time = time.time()
            
            # Save as AIS data (will create both CSV and JSON)
            saved_files = persistence.save_daily_data(
                ais_data=data,
                date_str=f'2025-09-{18 if name == "small" else 17 if name == "medium" else 16}'
            )
            
            end_time = time.time()
            save_time = end_time - start_time
            
            # Test load performance
            load_start = time.time()
            loaded_data = persistence.load_daily_data(f'2025-09-{18 if name == "small" else 17 if name == "medium" else 16}')
            load_end = time.time()
            load_time = load_end - load_start
            
            io_performance[name] = {
                'save_time': save_time,
                'load_time': load_time,
                'records': len(data),
                'files_created': len(saved_files)
            }
            
            # Verify data integrity
            assert len(loaded_data['ais_data']) == len(data)
        
        # Performance assertions
        assert io_performance['small']['save_time'] < 0.5  # Small data: <500ms
        assert io_performance['medium']['save_time'] < 2.0  # Medium data: <2s
        assert io_performance['large']['save_time'] < 10.0  # Large data: <10s
        
        assert io_performance['small']['load_time'] < 0.2  # Small load: <200ms
        assert io_performance['medium']['load_time'] < 1.0  # Medium load: <1s
        assert io_performance['large']['load_time'] < 5.0  # Large load: <5s
        
        # I/O efficiency (records per second)
        for name, perf in io_performance.items():
            save_rate = perf['records'] / perf['save_time']
            load_rate = perf['records'] / perf['load_time']
            
            assert save_rate > 100  # Should save >100 records/second
            assert load_rate > 500  # Should load >500 records/second