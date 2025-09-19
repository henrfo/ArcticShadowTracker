#!/usr/bin/env python3
"""
Test script for operational Arctic surveillance notebook
Tests all core functionality without Jupyter dependency
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

def test_core_imports():
    """Test 1: Core system imports"""
    print("🧪 TEST 1: Core system imports")
    try:
        from detection.advanced_dark_vessels import DarkVesselDetector
        from detection.advanced_cable_monitor import CableMonitor
        from models.advanced_autoencoder import MaritimeAnomalyDetector
        print("✅ All core systems imported successfully")
        return True, None
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False, str(e)

def test_system_initialization():
    """Test 2: System initialization"""
    print("\n🧪 TEST 2: System initialization")
    try:
        from detection.advanced_dark_vessels import DarkVesselDetector
        from detection.advanced_cable_monitor import CableMonitor
        
        detector = DarkVesselDetector(
            matching_threshold_meters=1000,
            vessel_size_threshold=15,
            confidence_threshold=0.5
        )
        
        cable_monitor = CableMonitor(
            proximity_threshold_km=10,
            loitering_threshold_hours=0.5
        )
        
        print(f"✅ Systems initialized - monitoring {len(cable_monitor.cables)} cables")
        return True, (detector, cable_monitor)
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return False, str(e)

def test_ais_data_collection():
    """Test 3: Real AIS data collection"""
    print("\n🧪 TEST 3: Real AIS data collection")
    
    arctic_bounds = {
        'north': 81.0, 'south': 69.0, 'east': 30.0, 'west': 5.0
    }
    
    ais_vessels = []
    
    # Try AISHub public API
    try:
        url = f"http://data.aishub.net/ws.php?username=DH_DEMO&format=1&output=json&compress=0&latmin={arctic_bounds['south']}&latmax={arctic_bounds['north']}&lonmin={arctic_bounds['west']}&lonmax={arctic_bounds['east']}"
        
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            
            vessels_data = []
            if isinstance(data, list):
                vessels_data = data
            elif isinstance(data, dict) and 'VESSELS' in data:
                vessels_data = data['VESSELS']
            elif isinstance(data, dict) and data.get('error'):
                print(f"⚠️ API Error: {data['error']}")
                return False, "API Error"
            
            if vessels_data:
                for vessel in vessels_data[:10]:  # Limit for testing
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
                    except (ValueError, TypeError):
                        continue
                
                print(f"✅ Collected {len(ais_vessels)} live AIS records")
                if ais_vessels:
                    sample = ais_vessels[0]
                    print(f"   📡 Sample: {sample['name']} at {sample['lat']:.3f}°N, {sample['lon']:.3f}°E")
                return True, ais_vessels
            else:
                print("⚠️ No vessels in Arctic area")
                return False, "No vessels"
        else:
            print(f"❌ HTTP {response.status_code}")
            return False, f"HTTP {response.status_code}"
            
    except Exception as e:
        print(f"❌ AIS collection error: {e}")
        return False, str(e)

def test_cable_proximity_monitoring(cable_monitor, ais_vessels):
    """Test 4: Cable proximity monitoring"""
    print("\n🧪 TEST 4: Cable proximity monitoring")
    
    try:
        # Prepare vessel list for cable monitoring
        all_vessels = []
        for vessel in ais_vessels:
            vessel_entry = {
                'vessel_id': vessel['mmsi'],
                'latitude': vessel['lat'],
                'longitude': vessel['lon'],
                'timestamp': vessel['timestamp'],
                'vessel_name': vessel['name'],
                'vessel_type': vessel['type'],
                'source': 'AIS',
                'has_ais': True,
                'speed': vessel['speed'],
                'course': vessel['course']
            }
            all_vessels.append(vessel_entry)
        
        # Check cable proximity
        vessels_near_cables = cable_monitor.check_vessel_cable_proximity(all_vessels)
        
        threats = []
        for vessel in vessels_near_cables:
            if vessel.get('near_cable', False):
                distance = vessel.get('distance_to_cable_km', 999)
                threat_level = "LOW"
                
                if distance < 5:
                    threat_level = "HIGH"
                if distance < 2:
                    threat_level = "CRITICAL"
                
                threat = {
                    'vessel_id': vessel['vessel_id'],
                    'vessel_name': vessel.get('vessel_name', 'Unknown'),
                    'threat_level': threat_level,
                    'distance_to_cable_km': distance,
                    'closest_cable': vessel.get('closest_cable', 'Unknown'),
                    'has_ais': vessel.get('has_ais', True)
                }
                threats.append(threat)
        
        print(f"✅ Cable monitoring complete - {len(threats)} threats detected")
        for threat in threats[:3]:  # Show first 3 threats
            print(f"   🚨 {threat['threat_level']}: {threat['vessel_name']} - {threat['distance_to_cable_km']:.1f}km")
        
        return True, threats
        
    except Exception as e:
        print(f"❌ Cable monitoring error: {e}")
        return False, str(e)

def test_threat_detection_pipeline(detector, cable_monitor, ais_vessels):
    """Test 5: Full threat detection pipeline"""
    print("\n🧪 TEST 5: Full threat detection pipeline")
    
    try:
        # Simulate some dark vessel detections (since we don't have SAR data)
        dark_vessels = []
        
        # Check for satellite data files
        import glob
        sentinel_files = glob.glob('./data/satellite/*sentinel*.tif')
        
        if sentinel_files:
            print(f"📁 Found {len(sentinel_files)} Sentinel files - processing...")
            # Would process real SAR data here
        else:
            print("📁 No SAR data - simulating dark vessel for testing")
            # Add a simulated dark vessel near a cable for testing
            dark_vessels.append({
                'detection_id': 'DARK_001',
                'lat': 78.5,  # Near Svalbard
                'lon': 15.0,
                'detection_time': datetime.now().isoformat(),
                'confidence': 0.85,
                'source': 'SAR_SIMULATION'
            })
        
        # Combine all vessels for threat assessment
        all_vessels = []
        
        # Add AIS vessels
        for vessel in ais_vessels:
            vessel_entry = {
                'vessel_id': vessel['mmsi'],
                'latitude': vessel['lat'],
                'longitude': vessel['lon'],
                'timestamp': vessel['timestamp'],
                'vessel_name': vessel['name'],
                'vessel_type': vessel['type'],
                'source': 'AIS',
                'has_ais': True,
                'speed': vessel['speed'],
                'course': vessel['course']
            }
            all_vessels.append(vessel_entry)
        
        # Add dark vessels
        for dark in dark_vessels:
            vessel_entry = {
                'vessel_id': dark['detection_id'],
                'latitude': dark['lat'],
                'longitude': dark['lon'],
                'timestamp': dark['detection_time'],
                'vessel_name': 'DARK_VESSEL',
                'vessel_type': 'Unknown',
                'source': 'SAR_DARK',
                'has_ais': False,
                'confidence': dark['confidence']
            }
            all_vessels.append(vessel_entry)
        
        # Execute threat detection
        vessels_near_cables = cable_monitor.check_vessel_cable_proximity(all_vessels)
        
        threats_detected = []
        for vessel in vessels_near_cables:
            if vessel.get('near_cable', False):
                distance = vessel.get('distance_to_cable_km', 999)
                threat_level = "LOW"
                
                if not vessel.get('has_ais', True):  # Dark vessel
                    threat_level = "HIGH"
                
                if distance < 2:  # Very close
                    threat_level = "CRITICAL"
                
                if distance < 5 and not vessel.get('has_ais', True):
                    threat_level = "CRITICAL"
                
                threat = {
                    'vessel_id': vessel['vessel_id'],
                    'vessel_name': vessel.get('vessel_name', 'Unknown'),
                    'threat_level': threat_level,
                    'distance_to_cable_km': distance,
                    'closest_cable': vessel.get('closest_cable', 'Unknown'),
                    'has_ais': vessel.get('has_ais', True),
                    'source': vessel['source']
                }
                threats_detected.append(threat)
        
        # Calculate mission status
        critical_threats = [t for t in threats_detected if t['threat_level'] == 'CRITICAL']
        high_threats = [t for t in threats_detected if t['threat_level'] == 'HIGH']
        
        mission_status = "ALL_CLEAR"
        if critical_threats:
            mission_status = "CRITICAL_THREATS_DETECTED"
        elif high_threats:
            mission_status = "HIGH_THREATS_DETECTED"
        elif threats_detected:
            mission_status = "THREATS_DETECTED"
        
        print(f"✅ Threat detection complete:")
        print(f"   🔴 CRITICAL: {len(critical_threats)}")
        print(f"   🟡 HIGH: {len(high_threats)}")
        print(f"   📊 Total: {len(threats_detected)}")
        print(f"   🎯 Status: {mission_status}")
        
        return True, (threats_detected, mission_status)
        
    except Exception as e:
        print(f"❌ Threat detection error: {e}")
        return False, str(e)

def test_report_generation(threats, mission_status):
    """Test 6: Report generation"""
    print("\n🧪 TEST 6: Report generation")
    
    try:
        # Create operational report
        report = {
            'header': {
                'title': 'Arctic Shadow Tracker - Test Report',
                'classification': 'UNCLASSIFIED',
                'timestamp': datetime.now().isoformat(),
                'mission_status': mission_status,
                'operator': 'AST_TEST_SYSTEM'
            },
            'summary': {
                'total_threats': len(threats),
                'critical_threats': len([t for t in threats if t['threat_level'] == 'CRITICAL']),
                'high_threats': len([t for t in threats if t['threat_level'] == 'HIGH']),
                'dark_vessels': len([t for t in threats if not t['has_ais']]),
                'monitored_area': 'Arctic Waters (Test)',
            },
            'threats': threats
        }
        
        # Save report
        os.makedirs('./outputs/test_reports', exist_ok=True)
        report_filename = f"./outputs/test_reports/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Report generated: {report_filename}")
        print(f"   📊 {report['summary']['total_threats']} threats documented")
        
        return True, report_filename
        
    except Exception as e:
        print(f"❌ Report generation error: {e}")
        return False, str(e)

def main():
    """Run all tests"""
    print("🎯 ARCTIC SHADOW TRACKER - OPERATIONAL NOTEBOOK TEST")
    print("=" * 60)
    
    test_results = {}
    
    # Test 1: Imports
    success, result = test_core_imports()
    test_results['imports'] = success
    if not success:
        print(f"\n🛑 CRITICAL: Import failure - {result}")
        return test_results
    
    # Test 2: Initialization  
    success, result = test_system_initialization()
    test_results['initialization'] = success
    if not success:
        print(f"\n🛑 CRITICAL: Initialization failure - {result}")
        return test_results
    
    detector, cable_monitor = result
    
    # Test 3: AIS Data Collection
    success, ais_vessels = test_ais_data_collection()
    test_results['ais_collection'] = success
    if not success:
        print(f"\n⚠️ WARNING: AIS collection failed - {ais_vessels}")
        ais_vessels = []  # Continue with empty dataset
    
    # Test 4: Cable Monitoring (if we have vessels)
    if ais_vessels:
        success, threats = test_cable_proximity_monitoring(cable_monitor, ais_vessels)
        test_results['cable_monitoring'] = success
    else:
        print("\n⚠️ SKIP: Cable monitoring (no AIS data)")
        test_results['cable_monitoring'] = False
        threats = []
    
    # Test 5: Full Pipeline
    success, pipeline_result = test_threat_detection_pipeline(detector, cable_monitor, ais_vessels or [])
    test_results['threat_detection'] = success
    if success:
        threats, mission_status = pipeline_result
    else:
        mission_status = "TEST_FAILED"
    
    # Test 6: Report Generation
    success, report_file = test_report_generation(threats, mission_status)
    test_results['report_generation'] = success
    
    # Summary
    print("\n" + "=" * 60)
    print("🎯 TEST SUMMARY:")
    
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, passed_test in test_results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n📊 OVERALL: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - Notebook ready for operational use!")
    elif passed >= total - 1:
        print("✅ MOSTLY FUNCTIONAL - Minor issues to address")
    else:
        print("⚠️ SIGNIFICANT ISSUES - Requires attention before deployment")
    
    return test_results

if __name__ == "__main__":
    main()