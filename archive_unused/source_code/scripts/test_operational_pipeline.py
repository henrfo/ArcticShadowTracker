#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Operational Pipeline Test Suite
Comprehensive testing of the Arctic distance calculation fixes and end-to-end pipeline.
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import time

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from detection.advanced_cable_monitor import CableMonitor
from detection.advanced_dark_vessels import DarkVesselDetector
from models.advanced_autoencoder import MaritimeAnomalyDetector
from geopy.distance import geodesic


class OperationalPipelineTest:
    """Comprehensive test suite for the operational pipeline"""
    
    def __init__(self):
        print("🎯 Arctic Shadow Tracker - Operational Pipeline Test")
        print("=" * 60)
        
        # Initialize core systems
        self.cable_monitor = CableMonitor(proximity_threshold_km=10)
        self.vessel_detector = DarkVesselDetector()
        self.test_results = {}
        self.start_time = datetime.now()
        
    def test_system_initialization(self):
        """Test that all core systems initialize correctly"""
        print("🔧 Testing system initialization...")
        
        tests = {
            'cable_monitor': {
                'instance': self.cable_monitor,
                'cables_loaded': len(self.cable_monitor.cables) > 0,
                'expected_cables': 4
            },
            'vessel_detector': {
                'instance': self.vessel_detector,
                'initialized': True
            }
        }
        
        results = {}
        for system_name, test_data in tests.items():
            try:
                instance = test_data['instance']
                if system_name == 'cable_monitor':
                    cables_count = len(instance.cables)
                    test_passed = cables_count == test_data['expected_cables']
                    results[system_name] = {
                        'initialized': True,
                        'cables_loaded': cables_count,
                        'test_passed': test_passed
                    }
                    print(f"   ✅ {system_name}: {cables_count} cables loaded")
                else:
                    results[system_name] = {
                        'initialized': True,
                        'test_passed': True
                    }
                    print(f"   ✅ {system_name}: initialized successfully")
                    
            except Exception as e:
                results[system_name] = {
                    'initialized': False,
                    'error': str(e),
                    'test_passed': False
                }
                print(f"   ❌ {system_name}: initialization failed - {e}")
        
        self.test_results['system_initialization'] = results
        return results
    
    def test_arctic_distance_calculations(self):
        """Test Arctic distance calculation accuracy using real cable coordinates"""
        print("\n🧪 Testing Arctic distance calculations...")
        
        # Use real cable coordinates from the system
        test_scenarios = [
            {
                'name': 'Close to Longyearbyen cable',
                'vessel_pos': (78.22, 15.63),  # Exact cable endpoint
                'expected_min_distance': 0.0,
                'tolerance_km': 0.1
            },
            {
                'name': 'Near SUCS cable midpoint',
                'vessel_pos': (77.5, 16.0),  # SUCS cable midpoint
                'expected_min_distance': 0.0,
                'tolerance_km': 0.1
            },
            {
                'name': '5km from cable',
                'vessel_pos': (78.27, 15.63),  # ~5km from Longyearbyen
                'expected_min_distance': 5.0,
                'tolerance_km': 1.0
            },
            {
                'name': 'Remote Arctic location',
                'vessel_pos': (82.0, 10.0),  # Far north
                'expected_min_distance': 300.0,  # Should be far from any cable
                'tolerance_km': 50.0
            }
        ]
        
        distance_test_results = []
        
        for scenario in test_scenarios:
            vessel_lat, vessel_lon = scenario['vessel_pos']
            
            # Calculate distance to closest cable using system method
            test_vessel = [{
                'vessel_id': 'TEST_VESSEL',
                'latitude': vessel_lat,
                'longitude': vessel_lon,
                'timestamp': datetime.now().isoformat()
            }]
            
            vessels_with_proximity = self.cable_monitor.check_vessel_cable_proximity(test_vessel)
            calculated_distance = vessels_with_proximity[0].get('distance_to_cable_km', float('inf'))
            closest_cable = vessels_with_proximity[0].get('closest_cable', 'None')
            
            # Verify with manual geodesic calculation
            manual_min_distance = float('inf')
            manual_closest_cable = None
            
            for cable in self.cable_monitor.cables:
                for point in cable['route']:
                    distance = geodesic((vessel_lat, vessel_lon), point).kilometers
                    if distance < manual_min_distance:
                        manual_min_distance = distance
                        manual_closest_cable = cable['name']
            
            # Check accuracy
            distance_error = abs(calculated_distance - manual_min_distance)
            accuracy_good = distance_error < 1.0  # Within 1km
            
            # Check if meets expectation
            expected_distance = scenario['expected_min_distance']
            tolerance = scenario['tolerance_km']
            expectation_met = abs(calculated_distance - expected_distance) <= tolerance
            
            result = {
                'scenario': scenario['name'],
                'vessel_position': f"{vessel_lat:.3f}°N, {vessel_lon:.3f}°E",
                'calculated_distance_km': calculated_distance,
                'manual_verification_km': manual_min_distance,
                'distance_error_km': distance_error,
                'closest_cable': closest_cable,
                'manual_closest_cable': manual_closest_cable,
                'accuracy_good': accuracy_good,
                'expected_distance_km': expected_distance,
                'expectation_met': expectation_met,
                'test_passed': accuracy_good and expectation_met
            }
            
            distance_test_results.append(result)
            
            status_icon = "✅" if result['test_passed'] else "❌"
            print(f"   {status_icon} {scenario['name']}:")
            print(f"      Position: {result['vessel_position']}")
            print(f"      Distance: {calculated_distance:.2f}km (manual: {manual_min_distance:.2f}km)")
            print(f"      Error: {distance_error:.2f}km")
            print(f"      Cable: {closest_cable}")
        
        self.test_results['arctic_distance_calculations'] = distance_test_results
        return distance_test_results
    
    def test_cable_proximity_detection(self):
        """Test cable proximity detection with realistic Arctic scenarios"""
        print("\n🔌 Testing cable proximity detection...")
        
        # Create realistic test vessels around Svalbard area
        test_vessels = [
            # Very close to cables (should trigger alerts)
            {
                'vessel_id': 'CRITICAL_001',
                'latitude': 78.221, 'longitude': 15.631,  # 100m from Longyearbyen cable
                'vessel_name': 'Test Critical Vessel',
                'timestamp': datetime.now().isoformat(),
                'expected_alert': True,
                'expected_level': 'CRITICAL'
            },
            # Moderately close (should trigger warning)
            {
                'vessel_id': 'WARNING_001', 
                'latitude': 78.25, 'longitude': 15.65,  # ~3km from cable
                'vessel_name': 'Test Warning Vessel',
                'timestamp': datetime.now().isoformat(),
                'expected_alert': True,
                'expected_level': 'WARNING'
            },
            # Within monitoring zone but safe
            {
                'vessel_id': 'MONITOR_001',
                'latitude': 78.30, 'longitude': 15.70,  # ~9km from cable
                'vessel_name': 'Test Monitor Vessel', 
                'timestamp': datetime.now().isoformat(),
                'expected_alert': True,
                'expected_level': 'LOW'
            },
            # Safe distance
            {
                'vessel_id': 'SAFE_001',
                'latitude': 78.50, 'longitude': 16.50,  # >20km from cables
                'vessel_name': 'Test Safe Vessel',
                'timestamp': datetime.now().isoformat(),
                'expected_alert': False,
                'expected_level': 'SAFE'
            }
        ]
        
        # Process vessels through proximity detection
        vessels_with_proximity = self.cable_monitor.check_vessel_cable_proximity(test_vessels)
        
        proximity_results = []
        
        for i, vessel in enumerate(vessels_with_proximity):
            original_vessel = test_vessels[i]
            
            is_near_cable = vessel.get('near_cable', False)
            distance_km = vessel.get('distance_to_cable_km', 999)
            cable_alerts = vessel.get('cable_alerts', [])
            
            # Determine actual alert level
            if cable_alerts:
                actual_level = max(alert['alert_level'] for alert in cable_alerts)
            else:
                actual_level = 'SAFE'
            
            # Check if expectations met
            expected_alert = original_vessel['expected_alert']
            expected_level = original_vessel['expected_level']
            
            alert_expectation_met = (expected_alert and is_near_cable) or (not expected_alert and not is_near_cable)
            
            result = {
                'vessel_id': vessel['vessel_id'],
                'position': f"{vessel['latitude']:.3f}°N, {vessel['longitude']:.3f}°E",
                'near_cable': is_near_cable,
                'distance_km': distance_km,
                'actual_level': actual_level,
                'expected_alert': expected_alert,
                'expected_level': expected_level,
                'alert_expectation_met': alert_expectation_met,
                'num_alerts': len(cable_alerts),
                'test_passed': alert_expectation_met
            }
            
            proximity_results.append(result)
            
            status_icon = "✅" if result['test_passed'] else "❌"
            print(f"   {status_icon} {original_vessel['vessel_name']}:")
            print(f"      Position: {result['position']}")
            print(f"      Near cable: {is_near_cable}, Distance: {distance_km:.2f}km")
            print(f"      Alert level: {actual_level} (expected: {expected_level})")
            print(f"      Alerts: {len(cable_alerts)}")
        
        self.test_results['cable_proximity_detection'] = proximity_results
        return proximity_results
    
    def test_end_to_end_pipeline(self):
        """Test the complete operational pipeline"""
        print("\n🔄 Testing end-to-end operational pipeline...")
        
        # Create synthetic Arctic vessel data
        synthetic_vessels = self.generate_synthetic_arctic_vessels(50)
        
        pipeline_start_time = time.time()
        
        # Step 1: Cable proximity analysis
        print("   📡 Step 1: Cable proximity analysis...")
        vessels_with_cable_info = self.cable_monitor.check_vessel_cable_proximity(synthetic_vessels)
        
        # Step 2: Threat assessment
        print("   ⚠️ Step 2: Threat assessment...")
        threats = [v for v in vessels_with_cable_info if v.get('near_cable', False)]
        
        # Step 3: Report generation
        print("   📋 Step 3: Report generation...")
        threat_report = self.cable_monitor.generate_cable_threat_report(vessels_with_cable_info, [])
        
        pipeline_end_time = time.time()
        processing_time = pipeline_end_time - pipeline_start_time
        
        # Analyze results
        pipeline_results = {
            'total_vessels_processed': len(synthetic_vessels),
            'vessels_near_cables': len(threats),
            'processing_time_seconds': processing_time,
            'vessels_per_second': len(synthetic_vessels) / processing_time,
            'report_generated': threat_report is not None,
            'report_summary': threat_report.get('summary', {}),
            'performance_rating': 'EXCELLENT' if processing_time < 1 else 'GOOD' if processing_time < 3 else 'NEEDS_OPTIMIZATION'
        }
        
        print(f"   📊 Processed {pipeline_results['total_vessels_processed']} vessels in {processing_time:.2f}s")
        print(f"   ⚡ Rate: {pipeline_results['vessels_per_second']:.1f} vessels/second")
        print(f"   🎯 Threats detected: {pipeline_results['vessels_near_cables']}")
        print(f"   📈 Performance: {pipeline_results['performance_rating']}")
        
        self.test_results['end_to_end_pipeline'] = pipeline_results
        return pipeline_results
    
    def test_performance_under_load(self):
        """Test system performance with larger datasets"""
        print("\n⚡ Testing performance under load...")
        
        load_tests = [
            {'vessel_count': 100, 'description': 'Normal load'},
            {'vessel_count': 500, 'description': 'High load'}, 
            {'vessel_count': 1000, 'description': 'Peak load'}
        ]
        
        performance_results = []
        
        for load_test in load_tests:
            vessel_count = load_test['vessel_count']
            description = load_test['description']
            
            print(f"   🔧 Testing {description}: {vessel_count} vessels...")
            
            # Generate test data
            test_vessels = self.generate_synthetic_arctic_vessels(vessel_count)
            
            # Measure processing time
            start_time = time.time()
            vessels_with_proximity = self.cable_monitor.check_vessel_cable_proximity(test_vessels)
            end_time = time.time()
            
            processing_time = end_time - start_time
            vessels_per_second = vessel_count / processing_time
            
            result = {
                'vessel_count': vessel_count,
                'description': description,
                'processing_time_seconds': processing_time,
                'vessels_per_second': vessels_per_second,
                'performance_rating': 'EXCELLENT' if vessels_per_second > 200 else 'GOOD' if vessels_per_second > 50 else 'NEEDS_OPTIMIZATION'
            }
            
            performance_results.append(result)
            
            print(f"      ⏱️ Time: {processing_time:.2f}s ({vessels_per_second:.1f} vessels/sec)")
            print(f"      📈 Rating: {result['performance_rating']}")
        
        self.test_results['performance_under_load'] = performance_results
        return performance_results
    
    def generate_synthetic_arctic_vessels(self, count):
        """Generate realistic Arctic vessel data for testing"""
        vessels = []
        
        # Arctic operational area around Svalbard
        lat_bounds = (70.0, 82.0)
        lon_bounds = (5.0, 35.0)
        
        np.random.seed(42)  # Reproducible results
        
        for i in range(count):
            # Generate position with higher density near cable areas
            if np.random.random() < 0.3:  # 30% near cables
                # Position near Svalbard cables
                lat = np.random.normal(78.2, 0.5)  # Around Longyearbyen
                lon = np.random.normal(15.6, 1.0)
            else:
                # Random Arctic position
                lat = np.random.uniform(lat_bounds[0], lat_bounds[1])
                lon = np.random.uniform(lon_bounds[0], lon_bounds[1])
            
            vessel = {
                'vessel_id': f'SYNTH_{i:03d}',
                'latitude': lat,
                'longitude': lon,
                'timestamp': datetime.now().isoformat(),
                'vessel_name': f'Synthetic Vessel {i}',
                'vessel_type': np.random.choice(['Cargo', 'Fishing', 'Research', 'Naval']),
                'has_ais': np.random.choice([True, False], p=[0.95, 0.05])  # 5% dark vessels
            }
            vessels.append(vessel)
        
        return vessels
    
    def run_comprehensive_test_suite(self):
        """Run all tests and generate comprehensive report"""
        print("\n" + "="*60)
        print("🔬 RUNNING COMPREHENSIVE TEST SUITE")
        print("="*60)
        
        # Run all test modules
        print("\n1️⃣ System Initialization Tests")
        init_results = self.test_system_initialization()
        
        print("\n2️⃣ Arctic Distance Calculation Tests")
        distance_results = self.test_arctic_distance_calculations()
        
        print("\n3️⃣ Cable Proximity Detection Tests")
        proximity_results = self.test_cable_proximity_detection()
        
        print("\n4️⃣ End-to-End Pipeline Tests")
        pipeline_results = self.test_end_to_end_pipeline()
        
        print("\n5️⃣ Performance Under Load Tests")
        performance_results = self.test_performance_under_load()
        
        # Generate overall assessment
        overall_assessment = self.generate_overall_assessment()
        
        # Create comprehensive test report
        test_report = {
            'test_suite_info': {
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
                'arctic_shadow_tracker_version': '1.0.0',
                'test_environment': 'Development'
            },
            'test_results': self.test_results,
            'overall_assessment': overall_assessment
        }
        
        # Save report
        os.makedirs('outputs/test_reports', exist_ok=True)
        report_filename = f"outputs/test_reports/operational_pipeline_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_filename, 'w') as f:
            json.dump(test_report, f, indent=2)
        
        print(f"\n💾 Comprehensive test report saved: {report_filename}")
        
        # Display summary
        self.display_test_summary(overall_assessment)
        
        return test_report
    
    def generate_overall_assessment(self):
        """Generate overall system assessment based on all tests"""
        
        # Count passed tests
        init_passed = all(result.get('test_passed', False) for result in self.test_results.get('system_initialization', {}).values())
        
        distance_passed_count = sum(1 for result in self.test_results.get('arctic_distance_calculations', []) if result.get('test_passed', False))
        distance_total = len(self.test_results.get('arctic_distance_calculations', []))
        distance_score = (distance_passed_count / distance_total * 100) if distance_total > 0 else 0
        
        proximity_passed_count = sum(1 for result in self.test_results.get('cable_proximity_detection', []) if result.get('test_passed', False))
        proximity_total = len(self.test_results.get('cable_proximity_detection', []))
        proximity_score = (proximity_passed_count / proximity_total * 100) if proximity_total > 0 else 0
        
        pipeline_performance = self.test_results.get('end_to_end_pipeline', {}).get('performance_rating', 'UNKNOWN')
        
        # Calculate overall score
        scores = [
            100 if init_passed else 0,
            distance_score,
            proximity_score,
            100 if pipeline_performance in ['EXCELLENT', 'GOOD'] else 50 if pipeline_performance == 'NEEDS_OPTIMIZATION' else 0
        ]
        
        overall_score = sum(scores) / len(scores)
        
        # Determine operational readiness
        if overall_score >= 90:
            operational_readiness = 'FULLY_OPERATIONAL'
        elif overall_score >= 75:
            operational_readiness = 'OPERATIONAL_WITH_MONITORING'
        elif overall_score >= 50:
            operational_readiness = 'LIMITED_OPERATIONAL'
        else:
            operational_readiness = 'NOT_OPERATIONAL'
        
        assessment = {
            'overall_score': overall_score,
            'operational_readiness': operational_readiness,
            'system_initialization': 'PASS' if init_passed else 'FAIL',
            'distance_calculation_accuracy': f"{distance_score:.1f}%",
            'proximity_detection_accuracy': f"{proximity_score:.1f}%", 
            'pipeline_performance': pipeline_performance,
            'recommendations': self.generate_recommendations(overall_score, pipeline_performance)
        }
        
        return assessment
    
    def generate_recommendations(self, overall_score, pipeline_performance):
        """Generate recommendations based on test results"""
        recommendations = []
        
        if overall_score < 75:
            recommendations.append("Address failing test cases before operational deployment")
        
        if pipeline_performance == 'NEEDS_OPTIMIZATION':
            recommendations.append("Optimize processing pipeline for better performance")
        
        # Check specific test results for detailed recommendations
        distance_results = self.test_results.get('arctic_distance_calculations', [])
        if distance_results:
            failed_distance_tests = [r for r in distance_results if not r.get('test_passed', False)]
            if failed_distance_tests:
                recommendations.append("Review Arctic distance calculation implementation")
        
        proximity_results = self.test_results.get('cable_proximity_detection', [])
        if proximity_results:
            failed_proximity_tests = [r for r in proximity_results if not r.get('test_passed', False)]
            if failed_proximity_tests:
                recommendations.append("Adjust cable proximity detection thresholds")
        
        if overall_score >= 90:
            recommendations.append("System ready for operational deployment")
        elif overall_score >= 75:
            recommendations.append("System suitable for operational use with monitoring")
        
        recommendations.append("Continue regular testing and validation")
        
        return recommendations
    
    def display_test_summary(self, assessment):
        """Display comprehensive test summary"""
        print("\n" + "="*60)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("="*60)
        
        print(f"🎯 Overall Score: {assessment['overall_score']:.1f}%")
        print(f"🚀 Operational Readiness: {assessment['operational_readiness']}")
        print(f"🔧 System Initialization: {assessment['system_initialization']}")
        print(f"📏 Distance Calculation: {assessment['distance_calculation_accuracy']}")
        print(f"🔌 Proximity Detection: {assessment['proximity_detection_accuracy']}")
        print(f"⚡ Pipeline Performance: {assessment['pipeline_performance']}")
        
        print(f"\n📋 RECOMMENDATIONS:")
        for i, rec in enumerate(assessment['recommendations'], 1):
            print(f"   {i}. {rec}")
        
        # Status indicator
        readiness = assessment['operational_readiness']
        if readiness == 'FULLY_OPERATIONAL':
            print(f"\n✅ STATUS: Arctic Shadow Tracker is READY for operational deployment")
        elif readiness == 'OPERATIONAL_WITH_MONITORING':
            print(f"\n🟡 STATUS: Arctic Shadow Tracker is operational but requires monitoring")
        elif readiness == 'LIMITED_OPERATIONAL':
            print(f"\n🟠 STATUS: Arctic Shadow Tracker has limited operational capability")
        else:
            print(f"\n❌ STATUS: Arctic Shadow Tracker is NOT ready for operational use")


if __name__ == "__main__":
    tester = OperationalPipelineTest()
    report = tester.run_comprehensive_test_suite()