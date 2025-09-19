#!/usr/bin/env python3
"""
Comprehensive unit tests for DataPersistence class.
Tests data validation, saving, loading, and operational data management.
"""

import pytest
import json
import pandas as pd
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import os

from utils.data_persistence import DataPersistence


class TestDataPersistenceInitialization:
    """Test DataPersistence initialization and directory setup."""
    
    def test_default_initialization(self, tmp_path):
        """Test DataPersistence initializes with default directory structure."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        assert persistence.base_dir == tmp_path
        assert (tmp_path / 'daily').exists()
        assert (tmp_path / 'historical').exists()
        assert (tmp_path / 'latest').exists()
    
    def test_custom_directory_initialization(self, tmp_path):
        """Test DataPersistence with custom base directory."""
        custom_dir = tmp_path / 'custom_data'
        persistence = DataPersistence(base_data_dir=str(custom_dir))
        
        assert persistence.base_dir == custom_dir
        assert custom_dir.exists()
        assert (custom_dir / 'daily').exists()
    
    def test_default_project_directory(self):
        """Test default directory resolution (without custom path)."""
        # This test needs to be careful not to create files in the actual project
        with patch('pathlib.Path.mkdir'):
            persistence = DataPersistence()
            
            expected_path = Path(__file__).parent.parent / 'data' / 'operational'
            assert str(persistence.base_dir) == str(expected_path)


class TestDataValidation:
    """Test data validation functionality."""
    
    def test_validate_ais_data_valid(self):
        """Test AIS data validation with valid data."""
        persistence = DataPersistence()
        
        valid_ais_data = [
            {
                'mmsi': '257012345',
                'latitude': 78.2,
                'longitude': 15.6,
                'timestamp': '2025-09-18T12:00:00'
            },
            {
                'mmsi': '259876543',
                'latitude': 70.5,
                'longitude': 31.2,
                'timestamp': '2025-09-18T12:15:00'
            }
        ]
        
        cleaned_data, quality_report = persistence._validate_data_quality(valid_ais_data, 'ais')
        
        assert len(cleaned_data) == 2
        assert quality_report['status'] == 'PROCESSED'
        assert quality_report['records_valid'] == 2
        assert quality_report['records_rejected'] == 0
        assert quality_report['error_rate'] == 0.0
    
    def test_validate_ais_data_missing_fields(self):
        """Test AIS data validation with missing required fields."""
        persistence = DataPersistence()
        
        invalid_ais_data = [
            {
                'mmsi': '257012345',
                'latitude': 78.2,
                # Missing longitude and timestamp
            },
            {
                'latitude': 78.2,
                'longitude': 15.6,
                'timestamp': '2025-09-18T12:00:00'
                # Missing mmsi
            },
            {
                'mmsi': '257012347',
                'latitude': 78.2,
                'longitude': 15.6,
                'timestamp': '2025-09-18T12:00:00'
            }  # Valid record
        ]
        
        cleaned_data, quality_report = persistence._validate_data_quality(invalid_ais_data, 'ais')
        
        assert len(cleaned_data) == 1  # Only one valid record
        assert quality_report['records_valid'] == 1
        assert quality_report['records_rejected'] == 2
        assert quality_report['error_rate'] == 2/3
        assert len(quality_report['errors']) == 2
    
    def test_validate_sar_data_invalid_coordinates(self):
        """Test SAR data validation with invalid coordinates."""
        persistence = DataPersistence()
        
        invalid_sar_data = [
            {
                'lat': 200.0,  # Invalid latitude
                'lon': 15.6,
                'detection_time': '2025-09-18T12:00:00'
            },
            {
                'lat': 78.2,
                'lon': -200.0,  # Invalid longitude
                'detection_time': '2025-09-18T12:00:00'
            },
            {
                'lat': 78.2,
                'lon': 15.6,
                'detection_time': '2025-09-18T12:00:00'
            }  # Valid record
        ]
        
        cleaned_data, quality_report = persistence._validate_data_quality(invalid_sar_data, 'sar')
        
        assert len(cleaned_data) == 1
        assert quality_report['records_valid'] == 1
        assert quality_report['records_rejected'] == 2
    
    def test_validate_threats_data(self):
        """Test threats data validation."""
        persistence = DataPersistence()
        
        threats_data = [
            {
                'vessel_id': 'VESSEL_001',
                'threat_level': 'HIGH',
                'latitude': 78.2,
                'longitude': 15.6
            },
            {
                'vessel_id': 'VESSEL_002',
                'threat_level': 'MEDIUM',
                'latitude': 70.5,
                'longitude': 31.2
            }
        ]
        
        cleaned_data, quality_report = persistence._validate_data_quality(threats_data, 'threats')
        
        assert len(cleaned_data) == 2
        assert quality_report['records_valid'] == 2
        
        # Check validation timestamps were added
        for record in cleaned_data:
            assert 'validation_timestamp' in record
    
    def test_validate_empty_data(self):
        """Test validation with empty data."""
        persistence = DataPersistence()
        
        cleaned_data, quality_report = persistence._validate_data_quality([], 'ais')
        
        assert cleaned_data == []
        assert quality_report['status'] == 'EMPTY'
        assert quality_report['records_processed'] == 0
        assert quality_report['records_valid'] == 0


class TestDataSaving:
    """Test data saving functionality."""
    
    def test_save_daily_data_basic(self, tmp_path, realistic_ais_data, realistic_sar_detections):
        """Test basic daily data saving."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        threats_data = [
            {
                'vessel_id': 'DARK_VESSEL_001',
                'threat_level': 'HIGH',
                'latitude': 78.5,
                'longitude': 16.2,
                'risk_score': 0.8
            }
        ]
        
        mission_summary = {
            'mission_id': 'ARCTIC_SURVEILLANCE_001',
            'status': 'COMPLETED',
            'summary': {
                'vessels_detected': len(realistic_ais_data),
                'dark_vessels': 1,
                'high_threats': 1
            }
        }
        
        saved_files = persistence.save_daily_data(
            ais_data=realistic_ais_data,
            sar_detections=realistic_sar_detections,
            threats=threats_data,
            mission_summary=mission_summary
        )
        
        assert 'ais' in saved_files
        assert 'sar' in saved_files
        assert 'threats' in saved_files
        assert 'summary' in saved_files
        
        # Verify files were created
        for file_path in saved_files.values():
            assert Path(file_path).exists()
    
    def test_save_daily_data_custom_date(self, tmp_path, realistic_ais_data):
        """Test daily data saving with custom date."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        custom_date = '2025-09-15'
        saved_files = persistence.save_daily_data(
            ais_data=realistic_ais_data,
            date_str=custom_date
        )
        
        # Check that files were saved in correct date directory
        date_dir = tmp_path / 'daily' / custom_date
        assert date_dir.exists()
        
        ais_file = Path(saved_files['ais'])
        assert custom_date in str(ais_file)
    
    def test_save_json_compressed_large_dataset(self, tmp_path):
        """Test compressed JSON saving for large datasets."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Create large dataset (above compression threshold)
        large_dataset = []
        for i in range(1500):  # Above default threshold of 1000
            large_dataset.append({
                'id': i,
                'data': f'test_data_{i}'
            })
        
        test_file = tmp_path / 'large_test.json'
        saved_path = persistence._save_json_compressed(large_dataset, test_file)
        
        # Should save as compressed file
        assert saved_path.endswith('.json.gz')
        assert Path(saved_path).exists()
        
        # Verify can read back compressed data
        with gzip.open(saved_path, 'rt', encoding='utf-8') as f:
            loaded_data = json.load(f)
        
        assert len(loaded_data) == 1500
        assert loaded_data[0]['id'] == 0
    
    def test_save_json_uncompressed_small_dataset(self, tmp_path):
        """Test uncompressed JSON saving for small datasets."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        small_dataset = [{'id': 1, 'data': 'test'}]  # Below compression threshold
        
        test_file = tmp_path / 'small_test.json'
        saved_path = persistence._save_json_compressed(small_dataset, test_file)
        
        # Should save as regular JSON
        assert saved_path.endswith('.json')
        assert not saved_path.endswith('.gz')
        
        # Verify file contents
        with open(saved_path, 'r') as f:
            loaded_data = json.load(f)
        
        assert len(loaded_data) == 1
        assert loaded_data[0]['id'] == 1
    
    def test_update_latest_data(self, tmp_path, realistic_ais_data):
        """Test latest data update functionality."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        threats_data = [{'vessel_id': 'TEST', 'threat_level': 'LOW'}]
        mission_summary = {'status': 'TEST'}
        
        # Save data which should update latest files
        persistence.save_daily_data(
            ais_data=realistic_ais_data,
            threats=threats_data,
            mission_summary=mission_summary
        )
        
        latest_dir = tmp_path / 'latest'
        
        # Check that latest files were created
        assert (latest_dir / 'ais_latest.json').exists()
        assert (latest_dir / 'threats_latest.json').exists()
        assert (latest_dir / 'summary_latest.json').exists()
        
        # Verify latest AIS data content
        with open(latest_dir / 'ais_latest.json', 'r') as f:
            latest_ais = json.load(f)
        
        assert len(latest_ais) == len(realistic_ais_data)


class TestDataLoading:
    """Test data loading functionality."""
    
    def test_load_daily_data_existing(self, tmp_path, realistic_ais_data, realistic_sar_detections):
        """Test loading existing daily data."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # First save data
        test_date = '2025-09-18'
        threats_data = [{'vessel_id': 'TEST', 'threat_level': 'HIGH'}]
        mission_summary = {'status': 'COMPLETED'}
        
        persistence.save_daily_data(
            ais_data=realistic_ais_data,
            sar_detections=realistic_sar_detections,
            threats=threats_data,
            mission_summary=mission_summary,
            date_str=test_date
        )
        
        # Load the data back
        loaded_data = persistence.load_daily_data(test_date)
        
        assert 'ais_data' in loaded_data
        assert 'sar_detections' in loaded_data
        assert 'threats' in loaded_data
        assert 'mission_summary' in loaded_data
        
        assert len(loaded_data['ais_data']) == len(realistic_ais_data)
        assert len(loaded_data['sar_detections']) == len(realistic_sar_detections)
        assert len(loaded_data['threats']) == 1
    
    def test_load_daily_data_nonexistent(self, tmp_path):
        """Test loading data for nonexistent date."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        loaded_data = persistence.load_daily_data('2025-01-01')
        
        assert loaded_data == {}
    
    def test_load_daily_data_default_date(self, tmp_path, realistic_ais_data):
        """Test loading data with default date (today)."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Save data for today
        today = datetime.now().strftime('%Y-%m-%d')
        persistence.save_daily_data(ais_data=realistic_ais_data)
        
        # Load without specifying date (should use today)
        loaded_data = persistence.load_daily_data()
        
        assert 'ais_data' in loaded_data
        assert len(loaded_data['ais_data']) == len(realistic_ais_data)


class TestHistoricalSummary:
    """Test historical data summary functionality."""
    
    def test_get_historical_summary(self, tmp_path):
        """Test historical summary generation."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Create test data for multiple days
        for i in range(3):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            
            mission_summary = {
                'mission_id': f'TEST_{i}',
                'data_counts': {
                    'ais_vessels': 10 + i,
                    'sar_detections': 5 + i,
                    'threats_detected': 2 + i
                },
                'mission_data': {
                    'summary': {
                        'critical_threats': i,
                        'high_threats': i + 1,
                        'dark_vessels': i + 2
                    }
                }
            }
            
            persistence.save_daily_data(
                ais_data=[{'mmsi': f'test_{i}', 'latitude': 78.0, 'longitude': 15.0, 'timestamp': '2025-09-18T12:00:00'}],
                mission_summary=mission_summary,
                date_str=date
            )
        
        # Get historical summary
        summary_df = persistence.get_historical_summary(days_back=3)
        
        assert isinstance(summary_df, pd.DataFrame)
        assert len(summary_df) == 3
        
        required_columns = [
            'date', 'ais_vessels', 'sar_detections', 
            'threats_detected', 'critical_threats', 'high_threats', 'dark_vessels'
        ]
        
        for col in required_columns:
            assert col in summary_df.columns
        
        # Check data is sorted by date
        assert summary_df['date'].is_monotonic_increasing
    
    def test_get_historical_summary_no_data(self, tmp_path):
        """Test historical summary with no data."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        summary_df = persistence.get_historical_summary(days_back=7)
        
        assert isinstance(summary_df, pd.DataFrame)
        assert len(summary_df) == 0


class TestCumulativeDataset:
    """Test cumulative dataset creation."""
    
    def test_create_cumulative_dataset_threats(self, tmp_path):
        """Test creating cumulative threats dataset."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Create test data for multiple days
        for i in range(3):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            
            threats_data = [
                {
                    'vessel_id': f'THREAT_{i}_1',
                    'threat_level': 'HIGH',
                    'latitude': 78.0 + i * 0.1,
                    'longitude': 15.0 + i * 0.1,
                    'timestamp': f'2025-09-1{8-i}T12:00:00'
                },
                {
                    'vessel_id': f'THREAT_{i}_2',
                    'threat_level': 'MEDIUM',
                    'latitude': 78.1 + i * 0.1,
                    'longitude': 15.1 + i * 0.1,
                    'timestamp': f'2025-09-1{8-i}T12:15:00'
                }
            ]
            
            persistence.save_daily_data(threats=threats_data, date_str=date)
        
        # Create cumulative dataset
        cumulative_df = persistence.create_cumulative_dataset('threats', days_back=3)
        
        assert isinstance(cumulative_df, pd.DataFrame)
        assert len(cumulative_df) == 6  # 2 threats per day * 3 days
        
        # Check that collection_date was added
        assert 'collection_date' in cumulative_df.columns
        
        # Verify data from all days is present
        unique_dates = cumulative_df['collection_date'].nunique()
        assert unique_dates == 3
    
    def test_create_cumulative_dataset_no_data(self, tmp_path):
        """Test cumulative dataset creation with no data."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        cumulative_df = persistence.create_cumulative_dataset('ais', days_back=7)
        
        assert isinstance(cumulative_df, pd.DataFrame)
        assert len(cumulative_df) == 0


class TestDailySummaryReport:
    """Test daily summary report generation."""
    
    def test_generate_daily_summary_report_with_data(self, tmp_path, realistic_ais_data, realistic_sar_detections):
        """Test daily summary report generation with data."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Add vessel types to AIS data for testing
        enhanced_ais_data = realistic_ais_data.copy()
        for i, vessel in enumerate(enhanced_ais_data):
            vessel['type'] = ['fishing', 'cargo', 'research'][i % 3]
        
        threats_data = [
            {'vessel_id': 'T1', 'threat_level': 'CRITICAL', 'latitude': 78.0, 'longitude': 15.0},
            {'vessel_id': 'T2', 'threat_level': 'HIGH', 'latitude': 78.1, 'longitude': 15.1},
            {'vessel_id': 'T3', 'threat_level': 'MEDIUM', 'latitude': 78.2, 'longitude': 15.2}
        ]
        
        test_date = '2025-09-18'
        persistence.save_daily_data(
            ais_data=enhanced_ais_data,
            sar_detections=realistic_sar_detections,
            threats=threats_data,
            date_str=test_date
        )
        
        # Generate report
        report = persistence.generate_daily_summary_report(test_date)
        
        assert report['status'] == 'SUCCESS'
        assert report['date'] == test_date
        
        # Check vessel statistics
        vessel_stats = report['vessel_statistics']
        assert vessel_stats['total_ais_vessels'] == len(enhanced_ais_data)
        assert vessel_stats['total_sar_detections'] == len(realistic_sar_detections)
        assert 'vessel_types' in vessel_stats
        assert 'geographic_distribution' in vessel_stats
        
        # Check threat analysis
        threat_analysis = report['threat_analysis']
        assert threat_analysis['total_threats'] == 3
        assert threat_analysis['threat_levels']['CRITICAL'] == 1
        assert threat_analysis['threat_levels']['HIGH'] == 1
        assert threat_analysis['threat_levels']['MEDIUM'] == 1
        assert threat_analysis['max_threat_level'] == 'CRITICAL'
        
        # Check surveillance quality
        quality = report['surveillance_quality']
        assert 'ais_coverage' in quality
        assert 'sar_coverage' in quality
        assert 'data_completeness' in quality
    
    def test_generate_daily_summary_report_no_data(self, tmp_path):
        """Test daily summary report generation with no data."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        report = persistence.generate_daily_summary_report('2025-01-01')
        
        assert report['status'] == 'NO_DATA'
        assert report['date'] == '2025-01-01'
        assert 'No surveillance data available' in report['message']
    
    def test_generate_daily_summary_report_default_date(self, tmp_path, realistic_ais_data):
        """Test daily summary report with default date (today)."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Save data for today
        persistence.save_daily_data(ais_data=realistic_ais_data)
        
        # Generate report without specifying date
        report = persistence.generate_daily_summary_report()
        
        assert report['status'] == 'SUCCESS'
        assert report['date'] == datetime.now().strftime('%Y-%m-%d')


@pytest.mark.edge_case
class TestDataPersistenceEdgeCases:
    """Test edge cases and error handling."""
    
    def test_save_data_with_none_values(self, tmp_path):
        """Test saving data with None values."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Call with all None values
        saved_files = persistence.save_daily_data(
            ais_data=None,
            sar_detections=None,
            threats=None,
            mission_summary=None
        )
        
        # Should return empty dict but not crash
        assert isinstance(saved_files, dict)
    
    def test_directory_creation_failure(self):
        """Test handling of directory creation failure."""
        # Try to create directory in protected location
        with patch('pathlib.Path.mkdir', side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError):
                DataPersistence(base_data_dir='/root/protected')
    
    def test_corrupted_json_file_loading(self, tmp_path):
        """Test handling of corrupted JSON files during loading."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Create corrupted JSON file
        test_date = '2025-09-18'
        date_dir = tmp_path / 'daily' / test_date
        date_dir.mkdir(parents=True)
        
        corrupted_file = date_dir / 'ais_data_120000.json'
        with open(corrupted_file, 'w') as f:
            f.write('{"invalid": json content}')  # Invalid JSON
        
        # Should handle gracefully
        loaded_data = persistence.load_daily_data(test_date)
        
        # Should return empty dict or skip corrupted files
        assert isinstance(loaded_data, dict)
    
    def test_large_dataset_memory_handling(self, tmp_path):
        """Test handling of very large datasets."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Create very large AIS dataset
        large_ais_data = []
        for i in range(10000):
            large_ais_data.append({
                'mmsi': f'25701{i:05d}',
                'latitude': 78.0 + (i % 100) * 0.01,
                'longitude': 15.0 + (i % 100) * 0.01,
                'timestamp': '2025-09-18T12:00:00'
            })
        
        # Should handle without memory errors
        saved_files = persistence.save_daily_data(ais_data=large_ais_data)
        
        assert 'ais' in saved_files
        assert Path(saved_files['ais']).exists()
    
    def test_concurrent_access_simulation(self, tmp_path, realistic_ais_data):
        """Test simulation of concurrent access to data files."""
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Simulate multiple saves in quick succession
        for i in range(5):
            enhanced_data = realistic_ais_data.copy()
            for vessel in enhanced_data:
                vessel['batch'] = i
            
            saved_files = persistence.save_daily_data(ais_data=enhanced_data)
            assert 'ais' in saved_files
        
        # Verify latest data loading still works
        loaded_data = persistence.load_daily_data()
        assert 'ais_data' in loaded_data


@pytest.mark.performance
class TestDataPersistencePerformance:
    """Test performance characteristics of data persistence operations."""
    
    def test_save_performance_large_dataset(self, tmp_path, performance_test_data):
        """Test save performance with large dataset."""
        import time
        
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        start_time = time.time()
        saved_files = persistence.save_daily_data(
            ais_data=performance_test_data['ais_data'],
            sar_detections=performance_test_data['sar_detections']
        )
        end_time = time.time()
        
        save_time = end_time - start_time
        
        assert save_time < 5.0  # Should save within 5 seconds
        assert len(saved_files) >= 2
        
        # Calculate records per second
        total_records = len(performance_test_data['ais_data']) + len(performance_test_data['sar_detections'])
        records_per_second = total_records / save_time
        assert records_per_second > 200  # Should save >200 records/second
    
    def test_load_performance_large_dataset(self, tmp_path, performance_test_data):
        """Test load performance with large dataset."""
        import time
        
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # First save the data
        test_date = '2025-09-18'
        persistence.save_daily_data(
            ais_data=performance_test_data['ais_data'],
            sar_detections=performance_test_data['sar_detections'],
            date_str=test_date
        )
        
        # Test load performance
        start_time = time.time()
        loaded_data = persistence.load_daily_data(test_date)
        end_time = time.time()
        
        load_time = end_time - start_time
        
        assert load_time < 2.0  # Should load within 2 seconds
        assert len(loaded_data['ais_data']) == len(performance_test_data['ais_data'])
        assert len(loaded_data['sar_detections']) == len(performance_test_data['sar_detections'])
    
    def test_validation_performance(self, tmp_path, performance_test_data):
        """Test data validation performance."""
        import time
        
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        start_time = time.time()
        cleaned_data, quality_report = persistence._validate_data_quality(
            performance_test_data['ais_data'], 'ais'
        )
        end_time = time.time()
        
        validation_time = end_time - start_time
        
        assert validation_time < 1.0  # Should validate within 1 second
        assert len(cleaned_data) > 0
        assert quality_report['records_processed'] == len(performance_test_data['ais_data'])
    
    def test_historical_summary_performance(self, tmp_path):
        """Test historical summary generation performance."""
        import time
        
        persistence = DataPersistence(base_data_dir=str(tmp_path))
        
        # Create data for many days
        for i in range(30):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            mission_summary = {
                'data_counts': {'ais_vessels': 10, 'sar_detections': 5, 'threats_detected': 2},
                'mission_data': {'summary': {'critical_threats': 0, 'high_threats': 1, 'dark_vessels': 2}}
            }
            persistence.save_daily_data(
                ais_data=[{'mmsi': 'test', 'latitude': 78, 'longitude': 15, 'timestamp': '2025-09-18T12:00:00'}],
                mission_summary=mission_summary,
                date_str=date
            )
        
        start_time = time.time()
        summary_df = persistence.get_historical_summary(days_back=30)
        end_time = time.time()
        
        summary_time = end_time - start_time
        
        assert summary_time < 2.0  # Should generate summary within 2 seconds
        assert len(summary_df) <= 30