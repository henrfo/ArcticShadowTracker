#!/usr/bin/env python3
"""
Comprehensive test suite for the operational Arctic surveillance notebook
Tests all functionality, error handling, and edge cases
"""

import sys
import os
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime, timedelta
import logging

# Add project root to path
project_root = os.path.abspath('.')
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class NotebookTester:
    def __init__(self):
        self.test_results = {}
        self.issues_found = []
        self.recommendations = []
        
    def log_issue(self, test_name, issue_description, severity="MEDIUM"):
        """Log an issue found during testing"""
        self.issues_found.append({
            'test': test_name,
            'issue': issue_description,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        })
        
    def log_recommendation(self, recommendation):
        """Log a recommendation for improvement"""
        self.recommendations.append(recommendation)

    def test_imports_and_dependencies(self):
        """Test all imports and dependencies"""
        print("🧪 Testing imports and dependencies...")
        
        try:
            # Core imports
            import pandas as pd
            import numpy as np
            import requests
            import json
            from datetime import datetime, timedelta
            
            # Project imports
            from detection.advanced_dark_vessels import DarkVesselDetector
            from detection.advanced_cable_monitor import CableMonitor
            from models.advanced_autoencoder import MaritimeAnomalyDetector
            
            print("✅ All imports successful")
            self.test_results['imports'] = True
            return True
            
        except ImportError as e:
            print(f"❌ Import error: {e}")
            self.log_issue('imports', f"Missing dependency: {e}", "CRITICAL")
            self.test_results['imports'] = False
            return False

    def test_system_initialization(self):
        """Test system initialization with various parameters"""
        print("🧪 Testing system initialization...")
        
        try:
            from detection.advanced_dark_vessels import DarkVesselDetector
            from detection.advanced_cable_monitor import CableMonitor
            
            # Test normal initialization
            detector = DarkVesselDetector(
                matching_threshold_meters=1000,
                vessel_size_threshold=15,
                confidence_threshold=0.5
            )
            
            cable_monitor = CableMonitor(
                proximity_threshold_km=10,
                loitering_threshold_hours=0.5
            )
            
            print(f"✅ Normal initialization successful")
            
            # Test edge case parameters
            try:
                detector_edge = DarkVesselDetector(
                    matching_threshold_meters=0.1,  # Very small
                    vessel_size_threshold=1,
                    confidence_threshold=0.01
                )
                print("✅ Edge case parameters accepted")
            except Exception as e:
                print(f"⚠️ Edge case parameter issue: {e}")
                self.log_issue('initialization', f"Edge case parameters not handled: {e}", "LOW")
            
            # Test invalid parameters
            try:
                detector_invalid = DarkVesselDetector(
                    matching_threshold_meters=-1000,  # Invalid
                )
                print("⚠️ Warning: Invalid parameters accepted")
                self.log_issue('initialization', "Negative threshold accepted", "MEDIUM")
            except Exception as e:
                print("✅ Invalid parameters properly rejected")
            
            self.test_results['initialization'] = True
            return True, (detector, cable_monitor)
            
        except Exception as e:
            print(f"❌ Initialization error: {e}")
            self.log_issue('initialization', f"System initialization failed: {e}", "CRITICAL")
            self.test_results['initialization'] = False
            return False, None

    def test_ais_data_collection_robustness(self):
        """Test AIS data collection with various scenarios"""
        print("🧪 Testing AIS data collection robustness...")
        
        # Test real API connection
        api_success = False
        ais_vessels = []
        
        try:
            arctic_bounds = {'north': 81.0, 'south': 69.0, 'east': 30.0, 'west': 5.0}
            url = f"http://data.aishub.net/ws.php?username=DH_DEMO&format=1&output=json&compress=0&latmin={arctic_bounds['south']}&latmax={arctic_bounds['north']}&lonmin={arctic_bounds['west']}&lonmax={arctic_bounds['east']}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                vessels_data = []
                if isinstance(data, list):
                    vessels_data = data
                elif isinstance(data, dict) and 'VESSELS' in data:
                    vessels_data = data['VESSELS']
                elif isinstance(data, dict) and data.get('error'):
                    print(f"⚠️ API Error: {data['error']}")
                    self.log_issue('ais_collection', f"API returned error: {data['error']}", "HIGH")
                
                if vessels_data:
                    for vessel in vessels_data[:5]:  # Process a few for testing
                        try:
                            ais_record = {
                                'mmsi': str(vessel.get('MMSI', 'unknown')),
                                'lat': float(vessel.get('LATITUDE', 0)),
                                'lon': float(vessel.get('LONGITUDE', 0)),
                                'speed': float(vessel.get('SOG', 0)),
                                'course': float(vessel.get('COG', 0)),
                                'timestamp': datetime.now().isoformat(),
                                'name': vessel.get('SHIPNAME', f'VESSEL_{vessel.get("MMSI", "UNK")}'),
                                'type': vessel.get('SHIP_TYPE', 'Unknown'),
                                'source': 'AIS_LIVE'
                            }
                            ais_vessels.append(ais_record)
                        except (ValueError, TypeError) as e:
                            print(f"⚠️ Data parsing issue: {e}")
                            self.log_issue('ais_collection', f"Data parsing error: {e}", "LOW")
                    
                    if ais_vessels:
                        print(f"✅ Successfully collected {len(ais_vessels)} AIS records")
                        api_success = True
                    else:
                        print("⚠️ No valid vessels parsed from API response")
                        self.log_issue('ais_collection', "No valid vessels in API response", "MEDIUM")
                else:
                    print("⚠️ No vessels in API response")
                    self.log_issue('ais_collection', "API returned no vessel data", "MEDIUM")
            else:
                print(f"❌ API returned HTTP {response.status_code}")
                self.log_issue('ais_collection', f"API HTTP error: {response.status_code}", "HIGH")
                
        except requests.RequestException as e:
            print(f"❌ Network error: {e}")
            self.log_issue('ais_collection', f"Network connection failed: {e}", "HIGH")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            self.log_issue('ais_collection', f"Unexpected error in AIS collection: {e}", "HIGH")
        
        self.test_results['ais_collection'] = api_success
        return api_success, ais_vessels

    def test_data_validation_and_error_handling(self, cable_monitor):
        """Test how system handles invalid and edge case data"""
        print("🧪 Testing data validation and error handling...")
        
        test_cases = [
            # Valid data
            {
                'name': 'valid_data',
                'vessels': [
                    {'vessel_id': 'TEST001', 'latitude': 78.5, 'longitude': 15.0, 'timestamp': datetime.now().isoformat(), 'vessel_name': 'Test Vessel', 'vessel_type': 'Cargo', 'source': 'TEST', 'has_ais': True, 'speed': 10.0, 'course': 45.0}
                ],
                'should_pass': True
            },
            # Empty data
            {
                'name': 'empty_data',
                'vessels': [],
                'should_pass': True
            },
            # Invalid coordinates
            {
                'name': 'invalid_coordinates',
                'vessels': [
                    {'vessel_id': 'TEST002', 'latitude': 'invalid', 'longitude': 15.0, 'timestamp': datetime.now().isoformat(), 'vessel_name': 'Test Vessel', 'vessel_type': 'Cargo', 'source': 'TEST', 'has_ais': True}
                ],
                'should_pass': False
            },
            # Out of bounds coordinates
            {
                'name': 'out_of_bounds',
                'vessels': [
                    {'vessel_id': 'TEST003', 'latitude': 91.0, 'longitude': 181.0, 'timestamp': datetime.now().isoformat(), 'vessel_name': 'Test Vessel', 'vessel_type': 'Cargo', 'source': 'TEST', 'has_ais': True}
                ],
                'should_pass': False
            },
            # Missing required fields
            {
                'name': 'missing_fields',
                'vessels': [
                    {'vessel_id': 'TEST004', 'latitude': 78.5}  # Missing longitude and other fields
                ],
                'should_pass': False
            }
        ]
        
        validation_results = {}
        
        for test_case in test_cases:
            try:
                print(f"   Testing: {test_case['name']}")
                result = cable_monitor.check_vessel_cable_proximity(test_case['vessels'])
                
                if test_case['should_pass']:
                    print(f"   ✅ {test_case['name']}: Handled correctly")
                    validation_results[test_case['name']] = True
                else:
                    print(f"   ⚠️ {test_case['name']}: Should have failed but didn't")
                    self.log_issue('data_validation', f"Invalid data accepted: {test_case['name']}", "MEDIUM")
                    validation_results[test_case['name']] = False
                    
            except Exception as e:
                if test_case['should_pass']:
                    print(f"   ❌ {test_case['name']}: Unexpected error: {e}")
                    self.log_issue('data_validation', f"Valid data caused error: {test_case['name']} - {e}", "HIGH")
                    validation_results[test_case['name']] = False
                else:
                    print(f"   ✅ {test_case['name']}: Properly rejected invalid data")
                    validation_results[test_case['name']] = True
        
        self.test_results['data_validation'] = validation_results
        return validation_results

    def test_threat_detection_scenarios(self, detector, cable_monitor):
        """Test various threat detection scenarios"""
        print("🧪 Testing threat detection scenarios...")
        
        # Create test scenarios
        scenarios = [
            {
                'name': 'vessel_near_cable',
                'description': 'AIS vessel very close to submarine cable',
                'vessels': [
                    {
                        'vessel_id': 'NEAR001',
                        'latitude': 78.9167,  # Very close to Svalbard cable
                        'longitude': 11.9333,
                        'timestamp': datetime.now().isoformat(),
                        'vessel_name': 'Close Vessel',
                        'vessel_type': 'Unknown',
                        'source': 'AIS',
                        'has_ais': True,
                        'speed': 5.0,
                        'course': 180.0
                    }
                ],
                'expected_threats': 1
            },
            {
                'name': 'dark_vessel_near_cable',
                'description': 'Dark vessel (no AIS) near submarine cable',
                'vessels': [
                    {
                        'vessel_id': 'DARK001',
                        'latitude': 78.9167,
                        'longitude': 11.9333,
                        'timestamp': datetime.now().isoformat(),
                        'vessel_name': 'DARK_VESSEL',
                        'vessel_type': 'Unknown',
                        'source': 'SAR_DARK',
                        'has_ais': False,
                        'confidence': 0.85
                    }
                ],
                'expected_threats': 1
            },
            {
                'name': 'vessel_far_from_cables',
                'description': 'Vessel far from any cables',
                'vessels': [
                    {
                        'vessel_id': 'FAR001',
                        'latitude': 70.0,  # Far from cables
                        'longitude': 20.0,
                        'timestamp': datetime.now().isoformat(),
                        'vessel_name': 'Far Vessel',
                        'vessel_type': 'Cargo',
                        'source': 'AIS',
                        'has_ais': True,
                        'speed': 15.0,
                        'course': 90.0
                    }
                ],
                'expected_threats': 0
            }
        ]
        
        scenario_results = {}
        
        for scenario in scenarios:
            try:
                print(f"   Testing scenario: {scenario['name']}")
                
                # Check vessel cable proximity
                vessels_with_cable_info = cable_monitor.check_vessel_cable_proximity(scenario['vessels'])
                
                # Count threats
                threats_detected = []
                for vessel in vessels_with_cable_info:
                    if vessel.get('near_cable', False):
                        distance = vessel.get('distance_to_cable_km', 999)
                        threat_level = "LOW"
                        
                        if not vessel.get('has_ais', True):
                            threat_level = "HIGH"
                        
                        if distance < 2:
                            threat_level = "CRITICAL"
                        
                        if distance < 5 and not vessel.get('has_ais', True):
                            threat_level = "CRITICAL"
                        
                        threats_detected.append({
                            'vessel_id': vessel['vessel_id'],
                            'threat_level': threat_level,
                            'distance': distance
                        })
                
                actual_threats = len(threats_detected)
                expected_threats = scenario['expected_threats']
                
                if actual_threats == expected_threats:
                    print(f"   ✅ {scenario['name']}: {actual_threats} threats detected (expected {expected_threats})")
                    scenario_results[scenario['name']] = True
                else:
                    print(f"   ⚠️ {scenario['name']}: {actual_threats} threats detected (expected {expected_threats})")
                    self.log_issue('threat_detection', f"Incorrect threat count in {scenario['name']}: got {actual_threats}, expected {expected_threats}", "MEDIUM")
                    scenario_results[scenario['name']] = False
                
            except Exception as e:
                print(f"   ❌ {scenario['name']}: Error: {e}")
                self.log_issue('threat_detection', f"Error in scenario {scenario['name']}: {e}", "HIGH")
                scenario_results[scenario['name']] = False
        
        self.test_results['threat_scenarios'] = scenario_results
        return scenario_results

    def test_performance_and_scalability(self, cable_monitor):
        """Test system performance with larger datasets"""
        print("🧪 Testing performance and scalability...")
        
        # Test with various dataset sizes
        test_sizes = [10, 100, 1000]
        performance_results = {}
        
        for size in test_sizes:
            try:
                print(f"   Testing with {size} vessels...")
                
                # Generate test vessel data
                test_vessels = []
                for i in range(size):
                    test_vessels.append({
                        'vessel_id': f'TEST_{i:04d}',
                        'latitude': 70.0 + (i % 10),  # Distribute across Arctic
                        'longitude': 10.0 + (i % 20),
                        'timestamp': datetime.now().isoformat(),
                        'vessel_name': f'Test Vessel {i}',
                        'vessel_type': 'Test',
                        'source': 'TEST',
                        'has_ais': True,
                        'speed': 10.0,
                        'course': 0.0
                    })
                
                # Time the operation
                start_time = datetime.now()
                result = cable_monitor.check_vessel_cable_proximity(test_vessels)
                end_time = datetime.now()
                
                processing_time = (end_time - start_time).total_seconds()
                vessels_per_second = size / processing_time if processing_time > 0 else float('inf')
                
                print(f"   ✅ {size} vessels processed in {processing_time:.2f}s ({vessels_per_second:.1f} vessels/sec)")
                
                performance_results[size] = {
                    'processing_time': processing_time,
                    'vessels_per_second': vessels_per_second,
                    'success': True
                }
                
                # Flag if performance is concerning
                if processing_time > 10 and size <= 100:
                    self.log_issue('performance', f"Slow processing: {size} vessels took {processing_time:.2f}s", "MEDIUM")
                
            except Exception as e:
                print(f"   ❌ {size} vessels: Error: {e}")
                self.log_issue('performance', f"Performance test failed for {size} vessels: {e}", "HIGH")
                performance_results[size] = {'success': False, 'error': str(e)}
        
        self.test_results['performance'] = performance_results
        return performance_results

    def generate_comprehensive_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("🎯 COMPREHENSIVE OPERATIONAL NOTEBOOK TEST REPORT")
        print("=" * 80)
        
        # Overall summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result is True or (isinstance(result, dict) and all(result.values())))
        
        print(f"\n📊 OVERALL TEST RESULTS: {passed_tests}/{total_tests} major test categories passed")
        
        # Detailed results
        print("\n🔍 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            if isinstance(result, bool):
                status = "✅ PASS" if result else "❌ FAIL"
                print(f"   {status} {test_name}")
            elif isinstance(result, dict):
                sub_passed = sum(1 for r in result.values() if r is True)
                sub_total = len(result)
                status = "✅ PASS" if sub_passed == sub_total else f"⚠️ PARTIAL ({sub_passed}/{sub_total})"
                print(f"   {status} {test_name}")
                
                if sub_passed != sub_total:
                    for sub_test, sub_result in result.items():
                        if not sub_result:
                            print(f"      ❌ {sub_test}")
        
        # Issues found
        print(f"\n⚠️ ISSUES FOUND: {len(self.issues_found)}")
        if self.issues_found:
            severity_counts = {}
            for issue in self.issues_found:
                severity = issue['severity']
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            for severity, count in severity_counts.items():
                print(f"   {severity}: {count} issues")
            
            print("\n🔍 ISSUE DETAILS:")
            for issue in self.issues_found:
                severity_icon = {"CRITICAL": "🔴", "HIGH": "🟡", "MEDIUM": "🟠", "LOW": "🟢"}.get(issue['severity'], "⚪")
                print(f"   {severity_icon} {issue['severity']}: {issue['issue']} (in {issue['test']})")
        
        # Recommendations
        self._generate_recommendations()
        
        if self.recommendations:
            print(f"\n💡 RECOMMENDATIONS ({len(self.recommendations)}):")
            for i, rec in enumerate(self.recommendations, 1):
                print(f"   {i}. {rec}")
        
        # Final assessment
        print("\n🎯 FINAL ASSESSMENT:")
        
        critical_issues = [i for i in self.issues_found if i['severity'] == 'CRITICAL']
        high_issues = [i for i in self.issues_found if i['severity'] == 'HIGH']
        
        if not critical_issues and not high_issues:
            if len(self.issues_found) == 0:
                assessment = "🎉 EXCELLENT: Notebook is production-ready with no issues detected"
            else:
                assessment = "✅ GOOD: Notebook is operational with only minor issues"
        elif critical_issues:
            assessment = "🛑 CRITICAL: Major issues prevent operational deployment"
        elif high_issues:
            assessment = "⚠️ WARNING: Significant issues require attention before deployment"
        else:
            assessment = "🔄 REVIEW: Minor improvements recommended"
        
        print(f"   {assessment}")
        
        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'test_results': self.test_results,
            'issues_found': self.issues_found,
            'recommendations': self.recommendations,
            'assessment': assessment,
            'summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'total_issues': len(self.issues_found),
                'critical_issues': len(critical_issues),
                'high_issues': len(high_issues)
            }
        }
        
        os.makedirs('./outputs/test_reports', exist_ok=True)
        report_file = f"./outputs/test_reports/comprehensive_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Full report saved: {report_file}")
        
        return report

    def _generate_recommendations(self):
        """Generate recommendations based on findings"""
        
        # Add data validation recommendations
        validation_issues = [i for i in self.issues_found if 'validation' in i['test']]
        if validation_issues:
            self.recommendations.append("Implement robust data validation with try-catch blocks for coordinate parsing")
            self.recommendations.append("Add input sanitization for vessel data before processing")
        
        # Add performance recommendations
        performance_issues = [i for i in self.issues_found if 'performance' in i['test']]
        if performance_issues:
            self.recommendations.append("Optimize vessel processing for larger datasets")
            self.recommendations.append("Consider implementing batch processing for high-volume scenarios")
        
        # Add API reliability recommendations
        api_issues = [i for i in self.issues_found if 'ais_collection' in i['test']]
        if api_issues:
            self.recommendations.append("Implement multiple backup AIS data sources")
            self.recommendations.append("Add retry logic with exponential backoff for API calls")
            self.recommendations.append("Store local cache of recent AIS data for offline operation")
        
        # General recommendations
        if len(self.issues_found) > 0:
            self.recommendations.append("Add comprehensive logging throughout the pipeline")
            self.recommendations.append("Implement health checks for all system components")
            self.recommendations.append("Create automated testing for continuous validation")


def main():
    """Run comprehensive notebook testing"""
    tester = NotebookTester()
    
    print("🎯 STARTING COMPREHENSIVE OPERATIONAL NOTEBOOK TESTING")
    print("=" * 60)
    
    # Test 1: Imports and Dependencies
    if not tester.test_imports_and_dependencies():
        print("🛑 Critical import failure - cannot continue testing")
        return tester.generate_comprehensive_report()
    
    # Test 2: System Initialization
    init_success, systems = tester.test_system_initialization()
    if not init_success:
        print("🛑 Critical initialization failure - cannot continue testing")
        return tester.generate_comprehensive_report()
    
    detector, cable_monitor = systems
    
    # Test 3: AIS Data Collection
    ais_success, ais_vessels = tester.test_ais_data_collection_robustness()
    
    # Test 4: Data Validation and Error Handling
    tester.test_data_validation_and_error_handling(cable_monitor)
    
    # Test 5: Threat Detection Scenarios
    tester.test_threat_detection_scenarios(detector, cable_monitor)
    
    # Test 6: Performance and Scalability
    tester.test_performance_and_scalability(cable_monitor)
    
    # Generate final report
    return tester.generate_comprehensive_report()


if __name__ == "__main__":
    main()