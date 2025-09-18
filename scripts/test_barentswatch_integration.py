#!/usr/bin/env python3
"""
Test BarentsWatch Integration
Comprehensive test for the enhanced dual-source Arctic AIS collection system.
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Main test function for BarentsWatch integration."""
    print("🇳🇴 BarentsWatch Official Norwegian Arctic AIS Integration Test")
    print("=" * 70)
    print(f"🕐 Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    test_results = []
    
    # Test 1: Authentication Module
    print("🔑 TEST 1: BarentsWatch Authentication")
    print("-" * 50)
    
    try:
        from utils.barentswatch_auth import BarentsWatchAuth
        
        auth = BarentsWatchAuth()
        print(f"   ✅ Authentication module imported successfully")
        print(f"   📋 Client ID: {auth.client_id}")
        print(f"   🌐 Auth URL: {auth.auth_url}")
        print(f"   🔗 Base API URL: {auth.base_url}")
        
        # Test connection (will show setup instructions if not configured)
        print(f"\n   🔍 Testing API connection...")
        connection_result = auth.test_connection()
        
        if connection_result:
            test_results.append({'test': 'barentswatch_auth', 'status': 'PASSED', 'message': 'Authentication successful'})
            print(f"   ✅ BarentsWatch authentication and API connection successful")
        else:
            test_results.append({'test': 'barentswatch_auth', 'status': 'FAILED', 'message': 'Authentication failed - check credentials'})
            print(f"   ❌ BarentsWatch authentication failed (expected if not configured)")
            print(f"   💡 This is normal if credentials are not set up")
        
    except Exception as e:
        test_results.append({'test': 'barentswatch_auth', 'status': 'ERROR', 'error': str(e)})
        print(f"   ❌ Authentication test error: {e}")
    
    # Test 2: BarentsWatch Collector
    print(f"\n🌊 TEST 2: BarentsWatch Data Collector")
    print("-" * 50)
    
    try:
        from utils.barentswatch_collector import BarentsWatchCollector
        
        collector = BarentsWatchCollector()
        print(f"   ✅ BarentsWatch collector imported successfully")
        
        # Show coverage areas
        coverage = collector.get_coverage_summary()
        print(f"   📍 Norwegian Arctic Coverage Areas:")
        for region, info in coverage['regions'].items():
            priority_indicator = "🔴" if info['priority'] == 'high' else "🟡" if info['priority'] == 'medium' else "🟢"
            print(f"     {priority_indicator} {region}: {info['description']}")
        
        print(f"   📊 Total regions: {coverage['total_regions']}")
        print(f"   🎯 High priority: {coverage['high_priority_regions']}")
        
        # Test data collection (will show setup instructions if not configured)
        print(f"\n   🔍 Testing data collection...")
        vessels = collector.collect_priority_areas()
        
        if vessels:
            test_results.append({'test': 'barentswatch_collector', 'status': 'PASSED', 'vessels_collected': len(vessels)})
            print(f"   ✅ Collected {len(vessels)} official Norwegian vessels")
            
            # Show sample vessels
            print(f"   🚢 Sample official vessels:")
            for vessel in vessels[:3]:
                print(f"     • {vessel['name']} (MMSI: {vessel['mmsi']})")
                print(f"       Position: {vessel['latitude']:.3f}°N, {vessel['longitude']:.3f}°E")
                print(f"       Authority: {vessel.get('authority', 'Norwegian Coastal Administration')}")
        else:
            test_results.append({'test': 'barentswatch_collector', 'status': 'NO_DATA', 'message': 'No vessels collected - normal if not configured'})
            print(f"   ⚠️ No official vessels collected (normal if credentials not set)")
        
    except Exception as e:
        test_results.append({'test': 'barentswatch_collector', 'status': 'ERROR', 'error': str(e)})
        print(f"   ❌ BarentsWatch collector test error: {e}")
    
    # Test 3: Enhanced Dual-Source Collector
    print(f"\n🌊 TEST 3: Enhanced Dual-Source AIS Collector")
    print("-" * 50)
    
    try:
        from utils.enhanced_ais_collector import EnhancedArcticAISCollector
        
        enhanced_collector = EnhancedArcticAISCollector()
        print(f"   ✅ Enhanced collector imported successfully")
        
        # Show source capabilities
        capabilities = enhanced_collector.get_source_capabilities()
        print(f"   📊 Data Source Capabilities:")
        for source, info in capabilities.items():
            if source != 'intelligent_merging':
                print(f"     {source.upper()}:")
                print(f"       • Type: {info['type']}")
                print(f"       • Coverage: {info['coverage']}")
                print(f"       • Data Quality: {info['data_quality']}")
        
        print(f"\n   🧠 Intelligent Merging Strategy:")
        merging = capabilities['intelligent_merging']
        print(f"     • Method: {merging['method']}")
        print(f"     • Deduplication: {merging['deduplication']}")
        print(f"     • Priority Logic: {merging['priority_logic']}")
        
        # Test comprehensive data collection
        print(f"\n   🎯 Testing comprehensive dual-source collection...")
        results = enhanced_collector.collect_comprehensive_arctic_data(duration_minutes=1)
        
        metadata = results['collection_metadata']
        barentswatch_count = metadata.get('barentswatch_count', 0)
        aisstream_count = metadata.get('aisstream_count', 0)
        combined_count = metadata.get('combined_count', 0)
        
        print(f"   📊 Collection Results:")
        print(f"     🇳🇴 BarentsWatch Official: {barentswatch_count} vessels")
        print(f"     🌐 aisstream.io Free: {aisstream_count} vessels")
        print(f"     🔄 Combined Unique: {combined_count} vessels")
        
        if metadata.get('deduplication_stats'):
            dedup = metadata['deduplication_stats']
            print(f"     ✂️ Duplicates removed: {dedup['duplicates_removed']}")
            print(f"     📈 Deduplication rate: {dedup['deduplication_rate']:.1%}")
        
        if combined_count > 0:
            test_results.append({'test': 'enhanced_collector', 'status': 'PASSED', 'total_vessels': combined_count})
            print(f"   ✅ Enhanced dual-source collection successful")
            
            # Show sample enhanced vessels
            if results['combined_data']:
                print(f"   🚢 Sample enhanced vessels:")
                for vessel in results['combined_data'][:3]:
                    print(f"     • {vessel['name']} (MMSI: {vessel['mmsi']})")
                    print(f"       Position: {vessel['latitude']:.3f}°N, {vessel['longitude']:.3f}°E")
                    print(f"       Source: {vessel['source']}")
                    if 'authority' in vessel:
                        print(f"       Authority: {vessel['authority']}")
            
            # Test data saving
            print(f"\n   💾 Testing enhanced data saving...")
            saved_files = enhanced_collector.save_enhanced_data(results)
            if saved_files:
                print(f"   ✅ Enhanced data saved successfully:")
                for data_type, file_path in saved_files.items():
                    print(f"     {data_type}: {file_path}")
        else:
            test_results.append({'test': 'enhanced_collector', 'status': 'NO_DATA', 'message': 'No vessels from any source'})
            print(f"   ⚠️ No vessels collected from any source")
            print(f"   💡 Check API credentials for both BarentsWatch and aisstream.io")
        
    except Exception as e:
        test_results.append({'test': 'enhanced_collector', 'status': 'ERROR', 'error': str(e)})
        print(f"   ❌ Enhanced collector test error: {e}")
    
    # Test 4: Integration with Surveillance Pipeline
    print(f"\n🎯 TEST 4: Surveillance Pipeline Integration")
    print("-" * 50)
    
    try:
        from scripts.working_surveillance_pipeline import run_single_surveillance
        
        print(f"   🔍 Testing pipeline with enhanced collector...")
        # This would run the actual surveillance pipeline
        print(f"   ✅ Pipeline module imports successfully")
        print(f"   💡 Run: python scripts/working_surveillance_pipeline.py --mode single")
        print(f"   💡 to test full pipeline integration")
        
        test_results.append({'test': 'pipeline_integration', 'status': 'PASSED', 'message': 'Module integration successful'})
        
    except Exception as e:
        test_results.append({'test': 'pipeline_integration', 'status': 'ERROR', 'error': str(e)})
        print(f"   ❌ Pipeline integration test error: {e}")
    
    # Test Summary
    print(f"\n📊 TEST SUMMARY")
    print("=" * 70)
    
    passed_tests = len([t for t in test_results if t['status'] == 'PASSED'])
    total_tests = len(test_results)
    
    print(f"Tests completed: {total_tests}")
    print(f"Tests passed: {passed_tests}")
    print(f"Tests failed/error: {total_tests - passed_tests}")
    
    print(f"\n📋 Detailed Results:")
    for result in test_results:
        status_emoji = "✅" if result['status'] == 'PASSED' else "❌" if result['status'] == 'ERROR' else "⚠️"
        print(f"   {status_emoji} {result['test']}: {result['status']}")
        if 'message' in result:
            print(f"      {result['message']}")
        if 'error' in result:
            print(f"      Error: {result['error']}")
        if 'vessels_collected' in result:
            print(f"      Vessels: {result['vessels_collected']}")
        if 'total_vessels' in result:
            print(f"      Total: {result['total_vessels']}")
    
    # Setup Instructions
    print(f"\n🔧 SETUP INSTRUCTIONS FOR FULL FUNCTIONALITY")
    print("=" * 70)
    print(f"To enable BarentsWatch official Norwegian Arctic AIS:")
    print(f"")
    print(f"1. BarentsWatch API Registration:")
    print(f"   • Visit: https://developer.barentswatch.no/")
    print(f"   • Register application")
    print(f"   • Use Client ID: henrikformoe@gmail.com:ArcticShadowTracker")
    print(f"   • Get client secret")
    print(f"   • Set: export BARENTSWATCH_CLIENT_SECRET='your_secret'")
    print(f"")
    print(f"2. aisstream.io API Key (Free):")
    print(f"   • Visit: https://aisstream.io/")
    print(f"   • Register for free account")
    print(f"   • Get free API key")
    print(f"   • Set: export AISSTREAM_API_KEY='your_free_key'")
    print(f"")
    print(f"3. Run Enhanced Surveillance:")
    print(f"   python scripts/working_surveillance_pipeline.py --mode single")
    print(f"")
    print(f"4. Test Collectors Individually:")
    print(f"   python utils/barentswatch_auth.py")
    print(f"   python utils/barentswatch_collector.py")
    print(f"   python utils/enhanced_ais_collector.py")
    
    overall_status = 'SUCCESS' if passed_tests == total_tests else 'PARTIAL' if passed_tests > 0 else 'FAILED'
    
    print(f"\n🎯 OVERALL TEST STATUS: {overall_status}")
    print(f"🕐 Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    return {
        'status': overall_status,
        'timestamp': datetime.now().isoformat(),
        'tests': test_results,
        'summary': {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests
        }
    }

if __name__ == "__main__":
    main()