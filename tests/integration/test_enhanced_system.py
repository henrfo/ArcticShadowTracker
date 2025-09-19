#!/usr/bin/env python3
"""
Test the Enhanced Dark Vessel Detection System
Demonstrates the enhanced capabilities integrated with the streaming system

This script tests:
1. Enhanced dark vessel detection with real CSV data
2. Risk scoring and pattern analysis
3. Integration with existing streaming system
4. Dashboard compatibility
5. CSV output enhancements
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_enhanced_detection():
    """Test the enhanced dark vessel detection system"""
    
    print("\n" + "="*70)
    print("🧪 TESTING ENHANCED DARK VESSEL DETECTION SYSTEM")
    print("="*70)
    
    try:
        # Import enhanced detection
        from enhanced_dark_vessel_detection import EnhancedDarkVesselDetector
        from streaming_integration_patch import EnhancedDarkVesselDetectorProxy
        
        logger.info("✅ Enhanced detection modules imported successfully")
        
        # Test 1: Enhanced detector initialization
        print("\n📊 TEST 1: Enhanced Detector Initialization")
        detector = EnhancedDarkVesselDetector()
        logger.info(f"✅ Enhanced detector initialized with {detector.max_history_days} days history")
        
        # Test 2: Load existing data
        print("\n📊 TEST 2: Loading Existing Data")
        history_df = detector.load_vessel_history()
        logger.info(f"✅ Loaded {len(history_df)} historical AIS records")
        
        dark_history_df = detector.load_dark_vessel_history()
        logger.info(f"✅ Loaded {len(dark_history_df)} historical dark vessel records")
        
        # Test 3: Mock current vessels (empty to trigger dark vessel detection)
        print("\n📊 TEST 3: Enhanced Dark Vessel Detection")
        mock_current_vessels = []  # Empty list to test detection of vessels that went dark
        
        # Run enhanced detection
        results = detector.run_enhanced_detection(mock_current_vessels)
        
        print(f"✅ Detection completed in {results['processing_time_seconds']:.1f} seconds")
        print(f"📈 Dark vessels found: {results['statistics']['dark_vessels_found']}")
        print(f"🔴 High-risk events: {results['statistics']['high_risk_events']}")
        print(f"🔌 Cable proximity events: {results['statistics']['cable_proximity_events']}")
        
        # Test 4: Integration proxy
        print("\n📊 TEST 4: Streaming System Integration")
        proxy = EnhancedDarkVesselDetectorProxy()
        logger.info(f"✅ Proxy initialized, enhanced mode: {proxy.use_enhanced}")
        
        # Test proxy detection (maintains original interface)
        history_df = proxy.update_history(mock_current_vessels)
        dark_vessels = proxy.detect_dark_vessels(mock_current_vessels, history_df)
        logger.info(f"✅ Proxy detection found {len(dark_vessels)} dark vessels")
        
        # Test enhanced alerts
        enhanced_alerts = proxy.get_enhanced_alerts_for_dashboard()
        logger.info(f"✅ Enhanced alerts: {enhanced_alerts['summary']}")
        
        # Test 5: CSV Output Verification
        print("\n📊 TEST 5: CSV Output Verification")
        csv_dir = Path('data_stream/csv')
        
        if (csv_dir / 'enhanced_dark_vessel_events.csv').exists():
            enhanced_df = pd.read_csv(csv_dir / 'enhanced_dark_vessel_events.csv')
            logger.info(f"✅ Enhanced CSV contains {len(enhanced_df)} records")
            
            if not enhanced_df.empty:
                logger.info(f"📊 Risk levels in data: {enhanced_df['risk_level'].value_counts().to_dict()}")
        
        # Test 6: Pattern Analysis
        print("\n📊 TEST 6: Pattern Analysis Results")
        if results['dark_vessel_events']:
            for i, event in enumerate(results['dark_vessel_events'][:3]):  # Show first 3
                logger.info(f"🌑 Event {i+1}: {event['name']} (MMSI: {event['mmsi']})")
                logger.info(f"   Risk Level: {event['risk_level']} (Score: {event['risk_score']})")
                logger.info(f"   Patterns: {len(event['suspicious_patterns'])}")
                if event['cable_proximity_when_dark']:
                    logger.info(f"   Cable Proximity: {event['cable_proximity_when_dark']}km")
        
        print("\n" + "="*70)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*70)
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure enhanced_dark_vessel_detection.py is in the current directory")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def test_streaming_integration():
    """Test integration with the existing streaming system"""
    
    print("\n" + "="*70)
    print("🧪 TESTING STREAMING SYSTEM INTEGRATION")
    print("="*70)
    
    try:
        # Test standalone integration function
        from streaming_integration_patch import run_enhanced_surveillance_cycle
        
        logger.info("✅ Testing standalone enhanced surveillance cycle...")
        
        # Mock current vessels (could be real data from BarentsWatch)
        mock_vessels = []
        
        # Run enhanced surveillance
        surveillance_results = run_enhanced_surveillance_cycle(mock_vessels)
        
        logger.info(f"✅ Surveillance cycle completed")
        logger.info(f"📊 Found {len(surveillance_results['dark_vessels'])} dark vessels")
        
        if 'enhanced_results' in surveillance_results and surveillance_results['enhanced_results']:
            stats = surveillance_results['statistics']
            logger.info(f"🔴 High-risk events: {stats.get('high_risk_events', 0)}")
            logger.info(f"🔌 Cable proximity events: {stats.get('cable_proximity_events', 0)}")
        
        print("\n✅ STREAMING INTEGRATION TEST COMPLETED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Streaming integration test failed: {e}")
        return False

def demonstrate_csv_schemas():
    """Demonstrate the CSV output schemas"""
    
    print("\n" + "="*70)
    print("📋 CSV SCHEMA DEMONSTRATION")
    print("="*70)
    
    csv_dir = Path('data_stream/csv')
    
    # Check existing CSV files
    csv_files = {
        'AIS History': 'ais_history.csv',
        'Basic Dark Vessels': 'dark_vessel_events.csv', 
        'Enhanced Dark Vessels': 'enhanced_dark_vessel_events.csv',
        'Cable Alerts': 'cable_alerts.csv'
    }
    
    for name, filename in csv_files.items():
        file_path = csv_dir / filename
        if file_path.exists():
            try:
                df = pd.read_csv(file_path)
                logger.info(f"📄 {name}: {len(df)} records, {len(df.columns)} columns")
                logger.info(f"   Columns: {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}")
                
                if 'enhanced_dark_vessel' in filename.lower() and not df.empty:
                    logger.info(f"   Risk Levels: {df['risk_level'].value_counts().to_dict()}")
                    
            except Exception as e:
                logger.warning(f"❌ Could not read {name}: {e}")
        else:
            logger.info(f"📄 {name}: File not found")
    
    print("✅ CSV SCHEMA DEMONSTRATION COMPLETED")

def main():
    """Run all tests"""
    
    print("🛰️ ARCTIC SHADOW TRACKER - ENHANCED SYSTEM TESTING")
    print("="*70)
    print("Testing enhanced dark vessel detection capabilities")
    print("Building on the excellent foundation from barentswatch_test_v2.ipynb")
    print("="*70)
    
    # Run tests
    test_results = []
    
    # Test 1: Enhanced Detection
    test_results.append(("Enhanced Detection", test_enhanced_detection()))
    
    # Test 2: Streaming Integration  
    test_results.append(("Streaming Integration", test_streaming_integration()))
    
    # Test 3: CSV Schemas
    test_results.append(("CSV Schemas", demonstrate_csv_schemas()))
    
    # Summary
    print("\n" + "="*70)
    print("🏁 TEST SUMMARY")
    print("="*70)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:25} {status}")
    
    all_passed = all(result for _, result in test_results)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("Enhanced dark vessel detection is ready for production use.")
    else:
        print("\n⚠️  Some tests failed. Check the logs above.")
    
    print("\n📖 USAGE INSTRUCTIONS:")
    print("1. Use 'enhanced_dark_vessel_detection.py' standalone")
    print("2. Apply 'streaming_integration_patch.py' to existing streaming system")
    print("3. Enhanced CSV outputs available in data_stream/csv/")
    print("4. Dashboard will show risk-based vessel coloring")
    
    return all_passed

if __name__ == "__main__":
    main()