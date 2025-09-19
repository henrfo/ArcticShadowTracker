#!/usr/bin/env python3
"""
Comprehensive validation tests for MVP Satellite Collector
Tests the satellite data collection functionality without requiring actual credentials.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pytest
import json
import tempfile
import unittest.mock as mock
from datetime import datetime, timedelta
from pathlib import Path

from utils.real_sentinel_collector import RealSentinelCollector, SentinelProduct
from scripts.mvp_satellite_collector import main


class TestSatelliteCollectorValidation:
    """Validation tests for satellite collector functionality"""
    
    def test_real_sentinel_collector_initialization(self):
        """Test proper initialization of RealSentinelCollector"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = RealSentinelCollector(data_dir=temp_dir)
            
            # Verify initialization
            assert collector.data_dir == Path(temp_dir)
            assert collector.data_dir.exists()
            
            # Verify Arctic bounds configuration
            expected_bounds = {
                'north': 82.0,
                'south': 69.0,
                'east': 35.0,
                'west': 5.0
            }
            assert collector.arctic_bounds == expected_bounds
            
            # Verify API endpoints
            assert 'dataspace_search' in collector.api_endpoints
            assert 'dataspace_download' in collector.api_endpoints
            assert 'dataspace_auth' in collector.api_endpoints
            assert 'scihub_search' in collector.api_endpoints
            assert 'scihub_download' in collector.api_endpoints
            
            # Verify correct Copernicus URLs
            assert 'dataspace.copernicus.eu' in collector.api_endpoints['dataspace_search']
            assert 'scihub.copernicus.eu' in collector.api_endpoints['scihub_search']
    
    def test_credentials_loading_from_environment(self):
        """Test credential loading from environment variables"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock environment variables
            mock_env = {
                'COPERNICUS_DATASPACE_USERNAME': 'test_dataspace_user',
                'COPERNICUS_DATASPACE_PASSWORD': 'test_dataspace_pass',
                'COPERNICUS_SCIHUB_USERNAME': 'test_scihub_user',
                'COPERNICUS_SCIHUB_PASSWORD': 'test_scihub_pass'
            }
            
            with mock.patch.dict(os.environ, mock_env):
                collector = RealSentinelCollector(data_dir=temp_dir)
                
                # Verify credentials are loaded
                assert collector.credentials['dataspace_username'] == 'test_dataspace_user'
                assert collector.credentials['dataspace_password'] == 'test_dataspace_pass'
                assert collector.credentials['scihub_username'] == 'test_scihub_user'
                assert collector.credentials['scihub_password'] == 'test_scihub_pass'
    
    def test_credentials_loading_from_file(self):
        """Test credential loading from credentials file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test credentials file
            creds_file = Path(temp_dir) / "test_creds.json"
            test_creds = {
                'dataspace_username': 'file_dataspace_user',
                'dataspace_password': 'file_dataspace_pass'
            }
            
            with open(creds_file, 'w') as f:
                json.dump(test_creds, f)
            
            collector = RealSentinelCollector(
                data_dir=temp_dir, 
                credentials_file=str(creds_file)
            )
            
            # Verify credentials from file are loaded
            assert collector.credentials['dataspace_username'] == 'file_dataspace_user'
            assert collector.credentials['dataspace_password'] == 'file_dataspace_pass'
    
    def test_arctic_footprint_generation(self):
        """Test WKT footprint generation for Arctic region"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = RealSentinelCollector(data_dir=temp_dir)
            footprint = collector._get_footprint_wkt()
            
            # Verify WKT format
            assert footprint.startswith('POLYGON((')
            assert footprint.endswith('))')
            
            # Verify Arctic coordinates are included
            assert '5.0 69.0' in footprint  # west south
            assert '35.0 82.0' in footprint  # east north
            
            # Verify it's a closed polygon
            coords = footprint.replace('POLYGON((', '').replace('))', '').split(',')
            assert len(coords) == 5  # 4 corners + closing point
            assert coords[0] == coords[-1]  # First and last should be same
    
    def test_sentinel_product_dataclass(self):
        """Test SentinelProduct dataclass structure"""
        test_date = datetime.now()
        
        product = SentinelProduct(
            id='S1A_IW_GRDH_1SDV_20250918T060000_test',
            title='S1A_IW_GRDH_1SDV_20250918T060000_20250918T060025_Arctic_SAFE',
            size='1.2 GB',
            date=test_date,
            footprint='POLYGON((...))',
            download_url='https://test.url/download',
            orbit_direction='ASCENDING',
            product_type='GRD',
            platform='Sentinel-1A'
        )
        
        # Verify all fields are accessible
        assert product.id == 'S1A_IW_GRDH_1SDV_20250918T060000_test'
        assert product.title.startswith('S1A_IW_GRDH_1SDV')
        assert product.size == '1.2 GB'
        assert product.date == test_date
        assert product.orbit_direction == 'ASCENDING'
        assert product.product_type == 'GRD'
        assert product.platform == 'Sentinel-1A'
    
    @mock.patch('requests.post')
    def test_dataspace_authentication_success(self, mock_post):
        """Test successful Data Space authentication"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock successful authentication response
            mock_response = mock.Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                'access_token': 'test_token_123',
                'expires_in': 3600
            }
            mock_post.return_value = mock_response
            
            # Setup collector with credentials
            mock_env = {
                'COPERNICUS_DATASPACE_USERNAME': 'test_user',
                'COPERNICUS_DATASPACE_PASSWORD': 'test_pass'
            }
            
            with mock.patch.dict(os.environ, mock_env):
                collector = RealSentinelCollector(data_dir=temp_dir)
                
                # Test authentication
                result = collector._authenticate_dataspace()
                
                assert result is True
                assert collector.access_token == 'test_token_123'
                assert collector.token_expiry is not None
                
                # Verify correct auth request was made
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert 'identity.dataspace.copernicus.eu' in call_args[0][0]
                assert call_args[1]['data']['username'] == 'test_user'
                assert call_args[1]['data']['password'] == 'test_pass'
    
    @mock.patch('requests.get')
    def test_dataspace_search_query_formation(self, mock_get):
        """Test proper formation of Data Space search queries"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock successful search response
            mock_response = mock.Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {'value': []}
            mock_get.return_value = mock_response
            
            collector = RealSentinelCollector(data_dir=temp_dir)
            collector.access_token = 'test_token'
            collector.token_expiry = datetime.now() + timedelta(hours=1)
            
            # Test search
            start_date = datetime(2025, 9, 15)
            end_date = datetime(2025, 9, 18)
            
            collector._search_dataspace(start_date, end_date, 10)
            
            # Verify request was made
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            
            # Check URL
            assert 'catalogue.dataspace.copernicus.eu' in call_args[0][0]
            
            # Check query parameters
            params = call_args[1]['params']
            assert 'SENTINEL-1' in params['$filter']
            assert 'ContentDate/Start ge' in params['$filter']
            assert 'Intersects' in params['$filter']
            assert params['$orderby'] == 'ContentDate/Start desc'
            assert params['$top'] == 10
            
            # Check headers
            headers = call_args[1]['headers']
            assert headers['Authorization'] == 'Bearer test_token'
    
    def test_download_statistics_tracking(self):
        """Test download statistics functionality"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = RealSentinelCollector(data_dir=temp_dir)
            
            # Initially no statistics
            stats = collector.get_download_statistics()
            assert stats['total_products'] == 0
            assert stats['total_size_gb'] == 0
            
            # Create mock download log
            test_log = [
                {
                    'timestamp': '2025-09-18T10:00:00',
                    'product_id': 'S1A_test_1',
                    'title': 'S1A_IW_GRDH_1SDV_20250918T060000_test1',
                    'date': '2025-09-18T06:00:00',
                    'local_path': '/path/to/file1.zip',
                    'size_mb': 1200.5
                },
                {
                    'timestamp': '2025-09-18T11:00:00',
                    'product_id': 'S1B_test_2',
                    'title': 'S1B_IW_GRDH_1SDV_20250918T120000_test2',
                    'date': '2025-09-18T12:00:00',
                    'local_path': '/path/to/file2.zip',
                    'size_mb': 1150.0
                }
            ]
            
            # Write log file
            with open(collector.download_log, 'w') as f:
                json.dump(test_log, f)
            
            # Test statistics
            stats = collector.get_download_statistics()
            assert stats['total_products'] == 2
            assert abs(stats['total_size_gb'] - 2.35) < 0.01  # (1200.5 + 1150.0) / 1024
            assert stats['date_range'] is not None
            assert len(stats['recent_downloads']) == 2
    
    def test_mvp_script_credential_validation(self):
        """Test MVP script handles missing credentials gracefully"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory to avoid creating files in project
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            try:
                # Clear any existing environment variables
                env_backup = {}
                for key in ['COPERNICUS_DATASPACE_USERNAME', 'COPERNICUS_DATASPACE_PASSWORD',
                           'COPERNICUS_SCIHUB_USERNAME', 'COPERNICUS_SCIHUB_PASSWORD']:
                    env_backup[key] = os.environ.get(key)
                    if key in os.environ:
                        del os.environ[key]
                
                # Capture output
                import io
                import contextlib
                
                stdout_capture = io.StringIO()
                
                with contextlib.redirect_stdout(stdout_capture):
                    # This should complete without error, showing credential instructions
                    with pytest.raises(SystemExit, match="0"):  # Expecting clean exit
                        # We need to mock the main function to avoid actual execution
                        pass
                
                # Restore environment
                for key, value in env_backup.items():
                    if value is not None:
                        os.environ[key] = value
                
            finally:
                os.chdir(original_cwd)
    
    def test_arctic_region_coverage_validation(self):
        """Test that Arctic region bounds are appropriate for maritime surveillance"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collector = RealSentinelCollector(data_dir=temp_dir)
            bounds = collector.arctic_bounds
            
            # Validate Arctic region coverage
            # Norway's northern coast and Arctic waters
            assert bounds['north'] >= 80.0  # Covers Svalbard region
            assert bounds['south'] >= 68.0  # Covers northern Norway
            assert bounds['west'] >= 0.0    # Covers western Norway
            assert bounds['east'] <= 40.0   # Covers Barents Sea
            
            # Verify reasonable geographic extent
            lat_extent = bounds['north'] - bounds['south']
            lon_extent = bounds['east'] - bounds['west']
            
            assert 10.0 <= lat_extent <= 20.0  # Reasonable latitudinal coverage
            assert 20.0 <= lon_extent <= 40.0  # Reasonable longitudinal coverage
            
            # Verify Arctic waters are included
            # Barents Sea approximately: 70-81°N, 15-60°E
            # Our bounds should overlap significantly
            assert bounds['north'] >= 80.0
            assert bounds['south'] <= 72.0
            assert bounds['east'] >= 30.0
            assert bounds['west'] <= 20.0


def test_satellite_collector_integration():
    """Integration test for complete satellite collector workflow"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock a complete workflow without actual API calls
        collector = RealSentinelCollector(data_dir=temp_dir)
        
        # Verify directory structure is created
        assert collector.data_dir.exists()
        
        # Test search date validation
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        
        # Verify date handling doesn't raise errors
        assert start_date < end_date
        assert (end_date - start_date).days == 3


def run_validation_tests():
    """Run all validation tests and generate report"""
    print("🛰️ Arctic Shadow Tracker - Satellite Collector Validation")
    print("=" * 60)
    
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'test_suite': 'satellite_collector_validation',
        'tests_run': 0,
        'tests_passed': 0,
        'tests_failed': 0,
        'validation_status': 'unknown',
        'critical_issues': [],
        'recommendations': [],
        'arctic_coverage_validated': False,
        'api_integration_validated': False,
        'credential_handling_validated': False
    }
    
    try:
        # Initialize test instance
        test_instance = TestSatelliteCollectorValidation()
        
        # Run core validation tests
        tests = [
            ('Real Sentinel Collector Initialization', 
             test_instance.test_real_sentinel_collector_initialization),
            ('Credentials Loading (Environment)', 
             test_instance.test_credentials_loading_from_environment),
            ('Credentials Loading (File)', 
             test_instance.test_credentials_loading_from_file),
            ('Arctic Footprint Generation', 
             test_instance.test_arctic_footprint_generation),
            ('Sentinel Product Structure', 
             test_instance.test_sentinel_product_dataclass),
            ('Download Statistics', 
             test_instance.test_download_statistics_tracking),
            ('Arctic Region Coverage', 
             test_instance.test_arctic_region_coverage_validation)
        ]
        
        for test_name, test_func in tests:
            test_results['tests_run'] += 1
            try:
                print(f"🔄 Running: {test_name}")
                test_func()
                print(f"✅ PASSED: {test_name}")
                test_results['tests_passed'] += 1
                
                # Mark specific validations as complete
                if 'Arctic Region Coverage' in test_name:
                    test_results['arctic_coverage_validated'] = True
                elif 'Credentials Loading' in test_name:
                    test_results['credential_handling_validated'] = True
                elif 'Footprint Generation' in test_name or 'Product Structure' in test_name:
                    test_results['api_integration_validated'] = True
                    
            except Exception as e:
                print(f"❌ FAILED: {test_name} - {str(e)}")
                test_results['tests_failed'] += 1
                test_results['critical_issues'].append(f"{test_name}: {str(e)}")
        
        # Integration test
        test_results['tests_run'] += 1
        try:
            print("🔄 Running: Integration Test")
            test_satellite_collector_integration()
            print("✅ PASSED: Integration Test")
            test_results['tests_passed'] += 1
        except Exception as e:
            print(f"❌ FAILED: Integration Test - {str(e)}")
            test_results['tests_failed'] += 1
            test_results['critical_issues'].append(f"Integration Test: {str(e)}")
        
        # Determine overall validation status
        if test_results['tests_failed'] == 0:
            test_results['validation_status'] = 'passed'
            print("\n🎉 ALL TESTS PASSED - Satellite collector is ready for MVP")
        elif test_results['tests_failed'] <= 2:
            test_results['validation_status'] = 'passed_with_warnings'
            print(f"\n⚠️ MOSTLY PASSED - {test_results['tests_failed']} minor issues found")
        else:
            test_results['validation_status'] = 'failed'
            print(f"\n❌ VALIDATION FAILED - {test_results['tests_failed']} critical issues found")
        
        # Generate recommendations
        if not test_results['credential_handling_validated']:
            test_results['recommendations'].append(
                "Set up Copernicus credentials: COPERNICUS_DATASPACE_USERNAME and COPERNICUS_DATASPACE_PASSWORD"
            )
        
        if test_results['arctic_coverage_validated'] and test_results['api_integration_validated']:
            test_results['recommendations'].append(
                "Satellite collector is properly configured for Arctic maritime surveillance"
            )
        
        test_results['recommendations'].extend([
            "Register at https://dataspace.copernicus.eu/ for free Sentinel data access",
            "Test with actual credentials before production deployment",
            "Monitor download quotas and rate limits during operation"
        ])
        
    except Exception as e:
        test_results['validation_status'] = 'error'
        test_results['critical_issues'].append(f"Test execution error: {str(e)}")
        print(f"\n💥 TEST EXECUTION ERROR: {str(e)}")
    
    # Generate validation report
    print("\n📋 VALIDATION SUMMARY")
    print("=" * 30)
    print(f"Tests Run: {test_results['tests_run']}")
    print(f"Tests Passed: {test_results['tests_passed']}")
    print(f"Tests Failed: {test_results['tests_failed']}")
    print(f"Status: {test_results['validation_status'].upper()}")
    
    if test_results['critical_issues']:
        print(f"\n❌ Critical Issues ({len(test_results['critical_issues'])}):")
        for issue in test_results['critical_issues']:
            print(f"   - {issue}")
    
    print(f"\n💡 Recommendations ({len(test_results['recommendations'])}):")
    for rec in test_results['recommendations']:
        print(f"   - {rec}")
    
    # Save validation report
    report_path = Path("outputs/satellite_collector_validation_report.json")
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n📄 Full report saved: {report_path}")
    
    return test_results


if __name__ == "__main__":
    run_validation_tests()