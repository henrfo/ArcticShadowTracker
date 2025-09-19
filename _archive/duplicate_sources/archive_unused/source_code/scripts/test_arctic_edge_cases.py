#!/usr/bin/env python3
"""
Arctic Edge Cases and Performance Validation Test Suite
Tests extreme Arctic conditions and edge cases for distance calculations.
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
from geopy.distance import geodesic


class ArcticEdgeCaseValidator:
    """Validates system behavior under extreme Arctic conditions"""
    
    def __init__(self):
        self.cable_monitor = CableMonitor()
        self.results = {}
        
    def test_extreme_arctic_coordinates(self):
        """Test with extreme Arctic coordinates near the pole"""
        print("🧊 Testing extreme Arctic coordinates...")
        
        extreme_cases = [
            {
                'name': 'Near North Pole',
                'coordinates': (89.5, 0.0),
                'description': 'Very close to North Pole'
            },
            {
                'name': 'North Pole',
                'coordinates': (90.0, 0.0),
                'description': 'Exactly at North Pole'
            },
            {
                'name': 'High Arctic East',
                'coordinates': (85.0, 179.0),
                'description': 'High Arctic near date line'
            },
            {
                'name': 'High Arctic West',
                'coordinates': (85.0, -179.0),
                'description': 'High Arctic, negative longitude'
            },
            {
                'name': 'Franz Josef Land',
                'coordinates': (80.8, 55.0),
                'description': 'Remote Arctic archipelago'
            }
        ]
        
        results = []
        
        for case in extreme_cases:
            try:
                lat, lon = case['coordinates']
                
                test_vessel = [{
                    'vessel_id': f'EXTREME_{case["name"].upper().replace(" ", "_")}',
                    'latitude': lat,
                    'longitude': lon,
                    'timestamp': datetime.now().isoformat(),
                    'vessel_name': f'Test - {case["name"]}',
                    'has_ais': True
                }]
                
                # Test system processing
                start_time = time.time()
                vessels_with_proximity = self.cable_monitor.check_vessel_cable_proximity(test_vessel)
                processing_time = time.time() - start_time
                
                vessel_result = vessels_with_proximity[0]
                distance_km = vessel_result.get('distance_to_cable_km', float('inf'))
                
                result = {
                    'case_name': case['name'],
                    'coordinates': f"{lat:.1f}°N, {lon:.1f}°E",
                    'description': case['description'],
                    'processing_successful': True,
                    'processing_time_ms': processing_time * 1000,
                    'distance_to_closest_cable_km': distance_km,
                    'closest_cable': vessel_result.get('closest_cable', 'None'),
                    'realistic_distance': distance_km > 0 and distance_km < 10000  # Sanity check
                }
                
                results.append(result)
                
                print(f"   ✅ {case['name']}: {result['coordinates']}")
                print(f"      Distance: {distance_km:.1f}km, Time: {processing_time*1000:.1f}ms")
                
            except Exception as e:
                result = {
                    'case_name': case['name'],
                    'coordinates': f"{lat:.1f}°N, {lon:.1f}°E",
                    'description': case['description'],
                    'processing_successful': False,
                    'error': str(e)
                }
                results.append(result)
                print(f"   ❌ {case['name']}: FAILED - {str(e)}")
        
        self.results['extreme_arctic_coordinates'] = results
        return results
    
    def test_coordinate_precision_boundaries(self):
        """Test coordinate precision at various Arctic latitudes"""
        print("\n📐 Testing coordinate precision boundaries...")
        
        # Test at different Arctic latitudes to verify geodesic accuracy
        precision_tests = [
            {'lat': 70.0, 'description': 'Southern Arctic boundary'},
            {'lat': 75.0, 'description': 'Mid Arctic'},
            {'lat': 80.0, 'description': 'High Arctic'},
            {'lat': 85.0, 'description': 'Very high Arctic'},
            {'lat': 88.0, 'description': 'Near polar region'}
        ]
        
        # Reference cable point (Longyearbyen)
        reference_point = (78.22, 15.63)
        
        results = []
        
        for test in precision_tests:
            test_lat = test['lat']
            
            # Test at multiple longitudes around this latitude
            longitude_tests = [0.0, 15.63, 90.0, 180.0, -90.0]  # Various longitudes
            
            for lon in longitude_tests:
                test_point = (test_lat, lon)
                
                # Calculate geodesic distance as reference
                geodesic_distance = geodesic(test_point, reference_point).kilometers
                
                # Test system calculation
                test_vessel = [{
                    'vessel_id': f'PRECISION_TEST_{test_lat}_{lon}',
                    'latitude': test_lat,
                    'longitude': lon,
                    'timestamp': datetime.now().isoformat()
                }]
                
                vessels_with_proximity = self.cable_monitor.check_vessel_cable_proximity(test_vessel)
                system_distance = vessels_with_proximity[0].get('distance_to_cable_km', float('inf'))
                
                # For this test, we need to check if system found the same closest cable
                # and if the distance is reasonable
                error_percent = abs(geodesic_distance - system_distance) / geodesic_distance * 100 if geodesic_distance > 0 else 0
                
                result = {
                    'test_latitude': test_lat,
                    'test_longitude': lon,
                    'description': test['description'],
                    'geodesic_reference_km': geodesic_distance,
                    'system_calculated_km': system_distance,
                    'error_percent': error_percent,
                    'precision_good': error_percent < 5.0  # Within 5% is acceptable
                }
                
                results.append(result)
        
        # Summary statistics
        good_precision_count = sum(1 for r in results if r['precision_good'])
        precision_rate = good_precision_count / len(results) * 100
        
        print(f"   📊 Precision tests: {good_precision_count}/{len(results)} passed ({precision_rate:.1f}%)")
        
        self.results['coordinate_precision'] = {
            'individual_tests': results,
            'summary': {
                'total_tests': len(results),
                'good_precision_count': good_precision_count,
                'precision_rate_percent': precision_rate
            }
        }
        
        return results
    
    def test_performance_with_concurrent_vessels(self):
        """Test performance with many vessels processed simultaneously"""
        print("\n⚡ Testing concurrent vessel processing performance...")
        
        vessel_counts = [10, 50, 100, 250, 500, 1000]
        performance_results = []
        
        for vessel_count in vessel_counts:
            print(f"   🔧 Testing {vessel_count} concurrent vessels...")
            
            # Generate realistic Arctic vessel distribution
            vessels = self.generate_arctic_vessel_fleet(vessel_count)
            
            # Measure processing performance
            start_time = time.time()
            vessels_with_proximity = self.cable_monitor.check_vessel_cable_proximity(vessels)
            end_time = time.time()
            
            processing_time = end_time - start_time
            vessels_per_second = vessel_count / processing_time
            
            # Count vessels near cables
            vessels_near_cables = sum(1 for v in vessels_with_proximity if v.get('near_cable', False))
            
            result = {
                'vessel_count': vessel_count,
                'processing_time_seconds': processing_time,
                'vessels_per_second': vessels_per_second,
                'vessels_near_cables': vessels_near_cables,
                'memory_efficient': processing_time < vessel_count * 0.01,  # Less than 10ms per vessel
                'performance_rating': self.rate_performance(vessels_per_second)
            }
            
            performance_results.append(result)
            
            print(f"      ⏱️ {processing_time:.3f}s ({vessels_per_second:.1f} vessels/sec)")
            print(f"      🎯 {vessels_near_cables} vessels near cables")
            print(f"      📈 Rating: {result['performance_rating']}")
        
        self.results['concurrent_performance'] = performance_results
        return performance_results
    
    def test_cable_route_edge_cases(self):
        """Test edge cases specific to cable route geometry"""
        print("\n🔌 Testing cable route geometry edge cases...")
        
        # Test vessels at various positions relative to cable segments
        cable_geometry_tests = [
            {
                'name': 'Vessel on cable endpoint',
                'position': (78.22, 15.63),  # Exact Longyearbyen cable endpoint
                'expected_distance': 0.0,
                'tolerance': 0.1
            },
            {
                'name': 'Vessel perpendicular to cable segment',
                'position': (77.85, 15.82),  # Perpendicular to SUCS cable
                'expected_distance': 20.0,  # Approximate
                'tolerance': 10.0
            },
            {
                'name': 'Vessel beyond cable extension',
                'position': (70.0, 26.0),  # Beyond Hammerfest endpoint
                'expected_distance': 130.0,  # Approximate
                'tolerance': 20.0
            },
            {
                'name': 'Vessel at cable intersection area',
                'position': (78.22, 15.63),  # Where multiple cables meet
                'expected_multiple_alerts': True
            }
        ]
        
        results = []
        
        for test in cable_geometry_tests:
            lat, lon = test['position']
            
            test_vessel = [{
                'vessel_id': f'GEOMETRY_TEST_{test["name"].upper().replace(" ", "_")}',
                'latitude': lat,
                'longitude': lon,
                'timestamp': datetime.now().isoformat(),
                'vessel_name': f'Geometry Test - {test["name"]}'
            }]
            
            vessels_with_proximity = self.cable_monitor.check_vessel_cable_proximity(test_vessel)
            vessel_result = vessels_with_proximity[0]
            
            distance_km = vessel_result.get('distance_to_cable_km', float('inf'))
            cable_alerts = vessel_result.get('cable_alerts', [])
            
            result = {
                'test_name': test['name'],
                'position': f"{lat:.3f}°N, {lon:.3f}°E",
                'calculated_distance_km': distance_km,
                'cable_alerts_count': len(cable_alerts),
                'closest_cable': vessel_result.get('closest_cable', 'None')
            }
            
            # Check expectations
            if 'expected_distance' in test:
                expected = test['expected_distance']
                tolerance = test['tolerance']
                distance_check = abs(distance_km - expected) <= tolerance
                result['distance_expectation_met'] = distance_check
                result['expected_distance_km'] = expected
                
                print(f"   {'✅' if distance_check else '❌'} {test['name']}")
                print(f"      Distance: {distance_km:.2f}km (expected: {expected:.1f}±{tolerance:.1f}km)")
            
            if test.get('expected_multiple_alerts', False):
                multiple_alerts = len(cable_alerts) > 1
                result['multiple_alerts_check'] = multiple_alerts
                
                print(f"   {'✅' if multiple_alerts else '❌'} {test['name']}")
                print(f"      Alerts: {len(cable_alerts)} cables")
            
            results.append(result)
        
        self.results['cable_geometry_edge_cases'] = results
        return results
    
    def generate_arctic_vessel_fleet(self, count):
        """Generate realistic Arctic vessel distribution"""
        vessels = []
        
        # Define Arctic operational zones with different vessel densities
        zones = [
            {'center': (78.2, 15.6), 'radius': 2.0, 'density': 0.4},    # Svalbard area - high density
            {'center': (74.0, 19.0), 'radius': 5.0, 'density': 0.3},   # Bear Island area
            {'center': (72.0, 35.0), 'radius': 8.0, 'density': 0.2},   # Barents Sea
            {'center': (76.0, 25.0), 'radius': 10.0, 'density': 0.1}   # Central Arctic
        ]
        
        np.random.seed(42)  # Reproducible
        
        for i in range(count):
            # Choose zone based on density
            zone_weights = [z['density'] for z in zones]
            zone_weights = [w / sum(zone_weights) for w in zone_weights]  # Normalize
            
            zone = np.random.choice(zones, p=zone_weights)
            
            # Generate position within zone
            angle = np.random.uniform(0, 2 * np.pi)
            radius = np.random.exponential(zone['radius'] / 3)  # Exponential distribution
            radius = min(radius, zone['radius'])  # Cap at zone boundary
            
            lat_offset = radius * np.cos(angle) / 111.0  # Approximate degree conversion
            lon_offset = radius * np.sin(angle) / (111.0 * np.cos(np.radians(zone['center'][0])))
            
            vessel_lat = zone['center'][0] + lat_offset
            vessel_lon = zone['center'][1] + lon_offset
            
            # Ensure within Arctic bounds
            vessel_lat = max(69.0, min(89.0, vessel_lat))
            vessel_lon = max(-180.0, min(180.0, vessel_lon))
            
            vessel = {
                'vessel_id': f'FLEET_{i:04d}',
                'latitude': vessel_lat,
                'longitude': vessel_lon,
                'timestamp': datetime.now().isoformat(),
                'vessel_name': f'Fleet Vessel {i}',
                'vessel_type': np.random.choice(['Cargo', 'Fishing', 'Research', 'Support']),
                'has_ais': np.random.choice([True, False], p=[0.95, 0.05])  # 5% dark vessels
            }
            vessels.append(vessel)
        
        return vessels
    
    def rate_performance(self, vessels_per_second):
        """Rate processing performance"""
        if vessels_per_second > 500:
            return 'EXCELLENT'
        elif vessels_per_second > 200:
            return 'GOOD'
        elif vessels_per_second > 50:
            return 'ACCEPTABLE'
        else:
            return 'NEEDS_OPTIMIZATION'
    
    def run_comprehensive_edge_case_validation(self):
        """Run all edge case tests and generate report"""
        print("🔬 Arctic Edge Cases and Performance Validation")
        print("=" * 60)
        
        start_time = datetime.now()
        
        # Run all test suites
        extreme_results = self.test_extreme_arctic_coordinates()
        precision_results = self.test_coordinate_precision_boundaries()
        performance_results = self.test_performance_with_concurrent_vessels()
        geometry_results = self.test_cable_route_edge_cases()
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Generate assessment
        assessment = self.generate_edge_case_assessment()
        
        # Create comprehensive report
        validation_report = {
            'test_info': {
                'timestamp': end_time.isoformat(),
                'duration_seconds': total_duration,
                'test_type': 'arctic_edge_cases_and_performance'
            },
            'test_results': self.results,
            'assessment': assessment
        }
        
        # Save report
        os.makedirs('outputs/test_reports', exist_ok=True)
        report_filename = f"outputs/test_reports/arctic_edge_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_filename, 'w') as f:
            json.dump(validation_report, f, indent=2)
        
        print(f"\n💾 Edge case validation report saved: {report_filename}")
        
        # Display summary
        self.display_edge_case_summary(assessment)
        
        return validation_report
    
    def generate_edge_case_assessment(self):
        """Generate overall assessment of edge case handling"""
        
        # Extreme coordinates test
        extreme_tests = self.results.get('extreme_arctic_coordinates', [])
        extreme_success_rate = sum(1 for t in extreme_tests if t.get('processing_successful', False)) / len(extreme_tests) * 100 if extreme_tests else 0
        
        # Precision tests
        precision_summary = self.results.get('coordinate_precision', {}).get('summary', {})
        precision_rate = precision_summary.get('precision_rate_percent', 0)
        
        # Performance tests
        performance_tests = self.results.get('concurrent_performance', [])
        excellent_performance_count = sum(1 for t in performance_tests if t.get('performance_rating') == 'EXCELLENT')
        performance_score = excellent_performance_count / len(performance_tests) * 100 if performance_tests else 0
        
        # Geometry tests
        geometry_tests = self.results.get('cable_geometry_edge_cases', [])
        
        # Overall scoring
        scores = [extreme_success_rate, precision_rate, performance_score]
        overall_score = sum(scores) / len(scores)
        
        # Determine readiness level
        if overall_score >= 90:
            readiness_level = 'PRODUCTION_READY'
        elif overall_score >= 75:
            readiness_level = 'OPERATIONAL_READY'
        elif overall_score >= 60:
            readiness_level = 'TESTING_PHASE'
        else:
            readiness_level = 'DEVELOPMENT_NEEDED'
        
        assessment = {
            'overall_score': overall_score,
            'readiness_level': readiness_level,
            'extreme_coordinates_success_rate': extreme_success_rate,
            'coordinate_precision_rate': precision_rate,
            'performance_excellence_rate': performance_score,
            'recommendations': self.generate_edge_case_recommendations(overall_score)
        }
        
        return assessment
    
    def generate_edge_case_recommendations(self, overall_score):
        """Generate recommendations based on edge case testing"""
        recommendations = []
        
        if overall_score >= 90:
            recommendations.append("System demonstrates excellent handling of Arctic edge cases")
            recommendations.append("Ready for operational deployment in extreme Arctic conditions")
        elif overall_score >= 75:
            recommendations.append("System handles most Arctic edge cases well")
            recommendations.append("Monitor performance in extreme conditions during initial deployment")
        else:
            recommendations.append("Address failing edge case scenarios before deployment")
            recommendations.append("Improve handling of extreme Arctic coordinates")
        
        # Specific recommendations based on test results
        extreme_tests = self.results.get('extreme_arctic_coordinates', [])
        failed_extreme = [t for t in extreme_tests if not t.get('processing_successful', False)]
        if failed_extreme:
            recommendations.append("Fix processing failures for extreme Arctic coordinates")
        
        precision_rate = self.results.get('coordinate_precision', {}).get('summary', {}).get('precision_rate_percent', 0)
        if precision_rate < 80:
            recommendations.append("Improve coordinate precision accuracy for Arctic calculations")
        
        performance_tests = self.results.get('concurrent_performance', [])
        slow_performance = [t for t in performance_tests if t.get('performance_rating') in ['NEEDS_OPTIMIZATION']]
        if slow_performance:
            recommendations.append("Optimize performance for high vessel count scenarios")
        
        return recommendations
    
    def display_edge_case_summary(self, assessment):
        """Display summary of edge case testing"""
        print("\n" + "="*60)
        print("📊 ARCTIC EDGE CASE VALIDATION SUMMARY")
        print("="*60)
        
        print(f"🎯 Overall Score: {assessment['overall_score']:.1f}%")
        print(f"🚀 Readiness Level: {assessment['readiness_level']}")
        print(f"🧊 Extreme Coordinates: {assessment['extreme_coordinates_success_rate']:.1f}% success")
        print(f"📐 Coordinate Precision: {assessment['coordinate_precision_rate']:.1f}% accurate")
        print(f"⚡ Performance Excellence: {assessment['performance_excellence_rate']:.1f}% of tests")
        
        print(f"\n📋 RECOMMENDATIONS:")
        for i, rec in enumerate(assessment['recommendations'], 1):
            print(f"   {i}. {rec}")
        
        # Final status
        readiness = assessment['readiness_level']
        if readiness == 'PRODUCTION_READY':
            print(f"\n✅ STATUS: Arctic Shadow Tracker handles all edge cases excellently")
        elif readiness == 'OPERATIONAL_READY':
            print(f"\n🟡 STATUS: Arctic Shadow Tracker ready for operational use")
        else:
            print(f"\n🟠 STATUS: Arctic Shadow Tracker needs additional development")


if __name__ == "__main__":
    validator = ArcticEdgeCaseValidator()
    report = validator.run_comprehensive_edge_case_validation()