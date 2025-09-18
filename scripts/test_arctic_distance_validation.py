#!/usr/bin/env python3
"""
Arctic Distance Calculation Validation Test Suite
Tests the geodesic distance calculation fixes for Arctic maritime surveillance.
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from detection.advanced_cable_monitor import CableMonitor
from geopy.distance import geodesic


class ArcticDistanceValidator:
    """Validates Arctic distance calculations using geodesic methods"""
    
    def __init__(self):
        self.cable_monitor = CableMonitor()
        self.test_results = []
        
    def test_arctic_coordinate_precision(self):
        """Test distance calculation precision at Arctic latitudes"""
        print("🧪 Testing Arctic coordinate precision...")
        
        # Arctic test coordinates (near Svalbard)
        arctic_coords = [
            (78.9249, 11.9312),  # Ny-Ålesund, Svalbard
            (79.8963, 20.3789),  # North of Svalbard
            (80.5000, 16.0000),  # High Arctic
            (81.0000, 25.0000),  # Near pole
        ]
        
        # Test with known cable coordinates
        longyearbyen_cable = (78.2232, 15.6267)  # Approximate cable endpoint
        
        test_results = []
        
        for vessel_coord in arctic_coords:
            # Calculate using geodesic (correct method)
            geodesic_distance = geodesic(vessel_coord, longyearbyen_cable).kilometers
            
            # Test CableMonitor's distance calculation
            test_vessel = {
                'vessel_id': 'TEST_VESSEL',
                'latitude': vessel_coord[0],
                'longitude': vessel_coord[1],
                'timestamp': datetime.now().isoformat()
            }
            
            # Create mock cable for testing (using the expected format)
            test_cable = {
                'id': 'TEST_CABLE',
                'name': 'Test Arctic Cable',
                'route': [longyearbyen_cable]
            }
            
            # Calculate distance using cable monitor's internal method
            cable_distance = self.cable_monitor._distance_to_cable(
                test_vessel['latitude'], test_vessel['longitude'], test_cable
            )
            
            # Calculate error
            error_percent = abs(geodesic_distance - cable_distance) / geodesic_distance * 100
            
            result = {
                'vessel_lat': vessel_coord[0],
                'vessel_lon': vessel_coord[1],
                'cable_lat': longyearbyen_cable[0],
                'cable_lon': longyearbyen_cable[1],
                'geodesic_distance_km': geodesic_distance,
                'calculated_distance_km': cable_distance,
                'error_percent': error_percent,
                'accuracy_level': 'HIGH' if error_percent < 1 else 'MEDIUM' if error_percent < 5 else 'LOW'
            }
            
            test_results.append(result)
            
            print(f"   📍 {vessel_coord[0]:.3f}°N, {vessel_coord[1]:.3f}°E:")
            print(f"      Geodesic: {geodesic_distance:.2f}km")
            print(f"      Calculated: {cable_distance:.2f}km")
            print(f"      Error: {error_percent:.2f}% ({result['accuracy_level']})")
            
        return test_results
    
    def test_cable_proximity_detection(self):
        """Test cable proximity detection with Arctic scenarios"""
        print("\n🔌 Testing cable proximity detection...")
        
        # Create test vessels at various distances from real cables
        test_scenarios = [
            {
                'name': 'Critical proximity',
                'vessel': {'latitude': 78.9250, 'longitude': 11.9310},  # Very close to Ny-Ålesund
                'expected_alert': True,
                'expected_level': 'CRITICAL'
            },
            {
                'name': 'Warning proximity', 
                'vessel': {'latitude': 78.9000, 'longitude': 12.0000},  # 5km from cable
                'expected_alert': True,
                'expected_level': 'WARNING'
            },
            {
                'name': 'Safe distance',
                'vessel': {'latitude': 78.5000, 'longitude': 10.0000},  # Far from cables
                'expected_alert': False,
                'expected_level': 'SAFE'
            },
            {
                'name': 'Barents Sea patrol',
                'vessel': {'latitude': 74.5000, 'longitude': 19.0000},  # Barents Sea
                'expected_alert': False,
                'expected_level': 'SAFE'
            }
        ]
        
        proximity_results = []
        
        for scenario in test_scenarios:
            test_vessel = {
                'vessel_id': f'TEST_{scenario["name"].upper().replace(" ", "_")}',
                'latitude': scenario['vessel']['latitude'],
                'longitude': scenario['vessel']['longitude'],
                'timestamp': datetime.now().isoformat(),
                'vessel_name': f'Test Vessel - {scenario["name"]}',
                'has_ais': True
            }
            
            # Check proximity to all cables
            vessels_with_proximity = self.cable_monitor.check_vessel_cable_proximity([test_vessel])
            vessel_result = vessels_with_proximity[0]
            
            is_near_cable = vessel_result.get('near_cable', False)
            distance_km = vessel_result.get('distance_to_cable_km', 999)
            closest_cable = vessel_result.get('closest_cable', 'None')
            
            # Determine alert level
            actual_level = 'SAFE'
            if is_near_cable:
                if distance_km < 2:
                    actual_level = 'CRITICAL'
                elif distance_km < 10:
                    actual_level = 'WARNING'
            
            test_passed = (
                (scenario['expected_alert'] and is_near_cable) or
                (not scenario['expected_alert'] and not is_near_cable)
            )
            
            result = {
                'scenario': scenario['name'],
                'vessel_position': f"{test_vessel['latitude']:.3f}°N, {test_vessel['longitude']:.3f}°E",
                'near_cable': is_near_cable,
                'distance_km': distance_km,
                'closest_cable': closest_cable,
                'expected_alert': scenario['expected_alert'],
                'expected_level': scenario['expected_level'],
                'actual_level': actual_level,
                'test_passed': test_passed
            }
            
            proximity_results.append(result)
            
            status_icon = "✅" if test_passed else "❌"
            print(f"   {status_icon} {scenario['name']}:")
            print(f"      Position: {result['vessel_position']}")
            print(f"      Near cable: {is_near_cable}")
            print(f"      Distance: {distance_km:.1f}km")
            print(f"      Level: {actual_level} (expected: {scenario['expected_level']})")
            
        return proximity_results
    
    def test_performance_with_real_data_volumes(self):
        """Test performance with realistic data volumes"""
        print("\n⚡ Testing performance with realistic data volumes...")
        
        # Generate realistic Arctic vessel data
        num_vessels = 100  # Typical for Arctic monitoring
        arctic_vessels = []
        
        # Arctic operational area
        lat_range = (69.0, 81.0)  # Arctic waters
        lon_range = (5.0, 30.0)   # Barents Sea to Kara Sea
        
        np.random.seed(42)  # Reproducible results
        
        for i in range(num_vessels):
            vessel = {
                'vessel_id': f'VESSEL_{i:03d}',
                'latitude': np.random.uniform(lat_range[0], lat_range[1]),
                'longitude': np.random.uniform(lon_range[0], lon_range[1]),
                'timestamp': datetime.now().isoformat(),
                'vessel_name': f'Test Vessel {i}',
                'has_ais': np.random.choice([True, False], p=[0.95, 0.05])  # 5% dark vessels
            }
            arctic_vessels.append(vessel)
        
        # Measure processing time
        start_time = datetime.now()
        
        vessels_with_proximity = self.cable_monitor.check_vessel_cable_proximity(arctic_vessels)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Analyze results
        vessels_near_cables = [v for v in vessels_with_proximity if v.get('near_cable', False)]
        performance_metrics = {
            'total_vessels': len(arctic_vessels),
            'processing_time_seconds': processing_time,
            'vessels_per_second': len(arctic_vessels) / processing_time,
            'vessels_near_cables': len(vessels_near_cables),
            'proximity_detection_rate': len(vessels_near_cables) / len(arctic_vessels) * 100,
            'performance_rating': 'EXCELLENT' if processing_time < 1 else 'GOOD' if processing_time < 5 else 'NEEDS_OPTIMIZATION'
        }
        
        print(f"   📊 Processed {performance_metrics['total_vessels']} vessels in {processing_time:.2f}s")
        print(f"   ⚡ Rate: {performance_metrics['vessels_per_second']:.1f} vessels/second")
        print(f"   🎯 Found {performance_metrics['vessels_near_cables']} vessels near cables")
        print(f"   📈 Performance: {performance_metrics['performance_rating']}")
        
        return performance_metrics
    
    def test_edge_cases(self):
        """Test edge cases and boundary conditions"""
        print("\n🔬 Testing edge cases and boundary conditions...")
        
        edge_cases = [
            {
                'name': 'North Pole proximity',
                'vessel': {'latitude': 89.0, 'longitude': 0.0},
                'description': 'Near North Pole coordinates'
            },
            {
                'name': 'Longitude wraparound',
                'vessel': {'latitude': 79.0, 'longitude': 179.5},
                'description': 'Near 180° longitude'
            },
            {
                'name': 'Negative longitude',
                'vessel': {'latitude': 75.0, 'longitude': -10.0},
                'description': 'Negative longitude coordinates'
            },
            {
                'name': 'Exact cable coordinate',
                'vessel': {'latitude': 78.9249, 'longitude': 11.9312},
                'description': 'Exactly on cable coordinates'
            }
        ]
        
        edge_case_results = []
        
        for case in edge_cases:
            try:
                test_vessel = {
                    'vessel_id': f'EDGE_CASE_{case["name"].upper().replace(" ", "_")}',
                    'latitude': case['vessel']['latitude'],
                    'longitude': case['vessel']['longitude'],
                    'timestamp': datetime.now().isoformat(),
                    'vessel_name': f'Edge Case - {case["name"]}',
                    'has_ais': True
                }
                
                vessels_with_proximity = self.cable_monitor.check_vessel_cable_proximity([test_vessel])
                vessel_result = vessels_with_proximity[0]
                
                result = {
                    'case_name': case['name'],
                    'description': case['description'],
                    'coordinates': f"{case['vessel']['latitude']:.3f}°N, {case['vessel']['longitude']:.3f}°E",
                    'calculation_successful': True,
                    'near_cable': vessel_result.get('near_cable', False),
                    'distance_km': vessel_result.get('distance_to_cable_km', 999),
                    'error': None
                }
                
                print(f"   ✅ {case['name']}: {result['coordinates']}")
                print(f"      Distance: {result['distance_km']:.1f}km")
                
            except Exception as e:
                result = {
                    'case_name': case['name'],
                    'description': case['description'],
                    'coordinates': f"{case['vessel']['latitude']:.3f}°N, {case['vessel']['longitude']:.3f}°E",
                    'calculation_successful': False,
                    'error': str(e)
                }
                
                print(f"   ❌ {case['name']}: FAILED - {str(e)}")
            
            edge_case_results.append(result)
        
        return edge_case_results
    
    def run_comprehensive_validation(self):
        """Run all validation tests and generate report"""
        print("🔬 Arctic Distance Calculation Validation Suite")
        print("=" * 60)
        
        # Run all tests
        precision_results = self.test_arctic_coordinate_precision()
        proximity_results = self.test_cable_proximity_detection()
        performance_results = self.test_performance_with_real_data_volumes()
        edge_case_results = self.test_edge_cases()
        
        # Generate comprehensive report
        validation_report = {
            'timestamp': datetime.now().isoformat(),
            'test_summary': {
                'precision_tests': len(precision_results),
                'proximity_tests': len(proximity_results),
                'edge_case_tests': len(edge_case_results),
                'performance_test_completed': True
            },
            'precision_results': precision_results,
            'proximity_results': proximity_results,
            'performance_results': performance_results,
            'edge_case_results': edge_case_results,
            'overall_assessment': self.generate_overall_assessment(
                precision_results, proximity_results, performance_results, edge_case_results
            )
        }
        
        # Save report
        os.makedirs('outputs/test_reports', exist_ok=True)
        report_filename = f"outputs/test_reports/arctic_distance_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_filename, 'w') as f:
            json.dump(validation_report, f, indent=2)
        
        print(f"\n💾 Validation report saved: {report_filename}")
        
        return validation_report
    
    def generate_overall_assessment(self, precision_results, proximity_results, performance_results, edge_case_results):
        """Generate overall system assessment"""
        
        # Analyze precision
        high_precision_count = sum(1 for r in precision_results if r['accuracy_level'] == 'HIGH')
        precision_score = high_precision_count / len(precision_results) * 100
        
        # Analyze proximity detection
        proximity_passed = sum(1 for r in proximity_results if r['test_passed'])
        proximity_score = proximity_passed / len(proximity_results) * 100
        
        # Analyze edge cases
        edge_cases_passed = sum(1 for r in edge_case_results if r['calculation_successful'])
        edge_case_score = edge_cases_passed / len(edge_case_results) * 100
        
        # Performance assessment
        performance_rating = performance_results['performance_rating']
        
        # Overall rating
        overall_score = (precision_score + proximity_score + edge_case_score) / 3
        
        if overall_score >= 90 and performance_rating in ['EXCELLENT', 'GOOD']:
            overall_rating = 'OPERATIONAL_READY'
        elif overall_score >= 75:
            overall_rating = 'NEEDS_MINOR_FIXES'
        else:
            overall_rating = 'NEEDS_MAJOR_IMPROVEMENTS'
        
        assessment = {
            'precision_score': precision_score,
            'proximity_detection_score': proximity_score,
            'edge_case_score': edge_case_score,
            'performance_rating': performance_rating,
            'overall_score': overall_score,
            'overall_rating': overall_rating,
            'recommendations': []
        }
        
        # Generate recommendations
        if precision_score < 90:
            assessment['recommendations'].append("Improve distance calculation precision for Arctic coordinates")
        
        if proximity_score < 90:
            assessment['recommendations'].append("Review proximity detection thresholds and logic")
        
        if edge_case_score < 80:
            assessment['recommendations'].append("Enhance error handling for boundary conditions")
        
        if performance_rating == 'NEEDS_OPTIMIZATION':
            assessment['recommendations'].append("Optimize processing performance for large vessel datasets")
        
        if not assessment['recommendations']:
            assessment['recommendations'].append("System performing excellently - ready for operational deployment")
        
        return assessment


if __name__ == "__main__":
    validator = ArcticDistanceValidator()
    report = validator.run_comprehensive_validation()
    
    print("\n📊 VALIDATION SUMMARY:")
    print(f"   Overall Score: {report['overall_assessment']['overall_score']:.1f}%")
    print(f"   Rating: {report['overall_assessment']['overall_rating']}")
    print(f"   Performance: {report['performance_results']['performance_rating']}")
    
    print("\n📋 RECOMMENDATIONS:")
    for rec in report['overall_assessment']['recommendations']:
        print(f"   • {rec}")