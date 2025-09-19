#!/usr/bin/env python3
"""
Test script for Arctic Shadow Tracker streaming system
Validates integration with real BarentsWatch data
"""

import sys
import logging
from pathlib import Path

# Configure logging for testing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_streaming_system():
    """Test the complete streaming system"""
    
    logger.info("🧪 Testing Arctic Shadow Tracker Streaming System")
    logger.info("="*60)
    
    try:
        # Import main system
        from arctic_shadow_tracker_stream import ArcticSurveillanceSystem
        
        # Initialize system
        logger.info("1️⃣ Initializing surveillance system...")
        surveillance = ArcticSurveillanceSystem()
        
        # Test single cycle
        logger.info("2️⃣ Running test surveillance cycle...")
        result = surveillance.run_surveillance_cycle()
        
        if result:
            logger.info("✅ Test cycle completed successfully!")
            logger.info(f"   🚢 Vessels tracked: {result['statistics']['total_vessels']}")
            logger.info(f"   🌑 Dark vessels: {result['statistics']['dark_vessels_detected']}")
            logger.info(f"   ⚠️ Cable alerts: {result['statistics']['cable_alerts']}")
            logger.info(f"   ⏱️ Cycle time: {result['cycle_duration_seconds']:.1f}s")
            logger.info(f"   🗺️ Dashboard: {result['dashboard_path']}")
            
            # Check data files created
            data_dir = Path('data_stream')
            if data_dir.exists():
                csv_files = list((data_dir / 'csv').glob('*.csv'))
                dashboard_files = list((data_dir / 'dashboard').glob('*.html'))
                
                logger.info("3️⃣ Checking generated files...")
                logger.info(f"   📊 CSV files: {len(csv_files)}")
                for csv_file in csv_files:
                    logger.info(f"      - {csv_file.name}")
                
                logger.info(f"   🗺️ Dashboard files: {len(dashboard_files)}")
                for dashboard_file in dashboard_files:
                    logger.info(f"      - {dashboard_file.name}")
            
            return True
        else:
            logger.error("❌ Test cycle failed")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("💡 Make sure config.yaml is properly configured")
        return False
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def test_enhanced_detection():
    """Test enhanced dark vessel detection"""
    
    logger.info("🔍 Testing Enhanced Dark Vessel Detection")
    logger.info("="*50)
    
    try:
        from enhanced_dark_vessel_detection import EnhancedDarkVesselDetector
        import pandas as pd
        from datetime import datetime, timedelta
        
        # Create test detector
        detector = EnhancedDarkVesselDetector()
        
        # Create sample data for testing
        test_data = []
        base_time = datetime.now() - timedelta(hours=10)
        
        for i in range(10):
            test_data.append({
                'mmsi': 123456789,
                'name': 'TEST_VESSEL',
                'latitude': 70.0 + i * 0.01,
                'longitude': 25.0 + i * 0.01,
                'speed': 10 + i,
                'course': 45 + i * 10,
                'timestamp': base_time + timedelta(hours=i)
            })
        
        test_df = pd.DataFrame(test_data)
        test_df['timestamp'] = pd.to_datetime(test_df['timestamp'])
        
        # Test behavior analysis
        logger.info("1️⃣ Testing behavior analysis...")
        analysis = detector.analyze_vessel_behavior(test_df)
        
        if analysis and 'risk_assessment' in analysis:
            risk = analysis['risk_assessment']
            logger.info(f"   ✅ Risk analysis completed")
            logger.info(f"   📊 Risk level: {risk['risk_level']}")
            logger.info(f"   📊 Risk score: {risk['risk_score']:.2f}")
        else:
            logger.error("   ❌ Behavior analysis failed")
            return False
        
        # Test clustering (needs more data)
        logger.info("2️⃣ Testing behavior clustering...")
        clustering = detector.cluster_vessel_behaviors(test_df)
        
        if clustering and clustering.get('status') in ['completed', 'insufficient_vessels']:
            logger.info(f"   ✅ Clustering completed: {clustering['status']}")
        else:
            logger.error("   ❌ Clustering failed")
            return False
        
        logger.info("✅ Enhanced detection tests passed!")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Enhanced detection test failed: {e}")
        return False

def test_config_validation():
    """Test configuration file validation"""
    
    logger.info("⚙️ Testing Configuration")
    logger.info("="*30)
    
    config_file = Path('config.yaml')
    if not config_file.exists():
        logger.error("❌ config.yaml not found")
        logger.info("💡 Please create config.yaml with BarentsWatch API credentials")
        return False
    
    try:
        import yaml
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        required_sections = ['barentswatch', 'sentinel_hub']
        missing_sections = []
        
        for section in required_sections:
            if section not in config:
                missing_sections.append(section)
        
        if missing_sections:
            logger.warning(f"⚠️ Missing config sections: {missing_sections}")
        else:
            logger.info("✅ All required config sections present")
        
        # Check BarentsWatch credentials
        if 'barentswatch' in config:
            bw_config = config['barentswatch']
            required_keys = ['client_id', 'client_secret', 'scope']
            missing_keys = [key for key in required_keys if key not in bw_config]
            
            if missing_keys:
                logger.error(f"❌ Missing BarentsWatch keys: {missing_keys}")
                return False
            else:
                logger.info("✅ BarentsWatch configuration valid")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Config validation failed: {e}")
        return False

def main():
    """Run all tests"""
    
    logger.info("🚀 Arctic Shadow Tracker - System Integration Test")
    logger.info("="*70)
    
    all_tests_passed = True
    
    # Test 1: Configuration
    if not test_config_validation():
        all_tests_passed = False
        logger.error("💥 Configuration test failed - cannot continue")
        return False
    
    # Test 2: Enhanced Detection
    if not test_enhanced_detection():
        all_tests_passed = False
        logger.warning("⚠️ Enhanced detection test failed")
    
    # Test 3: Streaming System (requires working API)
    if not test_streaming_system():
        all_tests_passed = False
        logger.error("💥 Streaming system test failed")
    
    # Final result
    logger.info("="*70)
    if all_tests_passed:
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("✅ Arctic Shadow Tracker streaming system is ready")
        logger.info("")
        logger.info("🚀 To start streaming surveillance:")
        logger.info("   python arctic_shadow_tracker_stream.py")
        logger.info("")
        logger.info("🧪 To run single test cycle:")
        logger.info("   python arctic_shadow_tracker_stream.py test")
    else:
        logger.error("❌ Some tests failed - please check configuration and dependencies")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)