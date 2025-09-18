#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Connect Real Data Sources
Demonstrates how to connect to actual AIS and SAR data sources.
"""

import os
import sys
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

def test_marinetraffic_api():
    """Test MarineTraffic API with real Arctic data."""
    api_key = os.getenv('MARINETRAFFIC_API_KEY')
    
    if not api_key:
        print("❌ MarineTraffic API key not found")
        print("💡 Set environment variable: export MARINETRAFFIC_API_KEY='your_key'")
        print("🔗 Sign up at: https://www.marinetraffic.com/en/ais-api-services")
        return False
    
    print("🔍 Testing MarineTraffic API...")
    
    try:
        # MarineTraffic PS01 API - Extended Vessel Details
        url = "https://services.marinetraffic.com/api/exportvessels/v:8"
        
        params = {
            'key': api_key,
            'protocol': 'jsono',
            'timespan': '180',  # Last 3 hours
            'minlat': '69',     # Arctic bounds
            'maxlat': '82',
            'minlon': '5', 
            'maxlon': '35'
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        vessels = response.json()
        
        if vessels and len(vessels) > 0:
            print(f"✅ MarineTraffic: Collected {len(vessels)} real vessels")
            
            # Show sample vessels
            for vessel in vessels[:3]:
                mmsi = vessel.get('MMSI', 'Unknown')
                name = vessel.get('SHIPNAME', 'Unknown')
                lat = vessel.get('LAT', 0)
                lon = vessel.get('LON', 0)
                print(f"   🚢 {name} (MMSI: {mmsi}): {lat}°N, {lon}°E")
            
            return True
        else:
            print("⚠️ MarineTraffic: No vessels in Arctic region")
            return True
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("❌ MarineTraffic: Invalid API key")
        elif e.response.status_code == 403:
            print("❌ MarineTraffic: API access denied")
        else:
            print(f"❌ MarineTraffic: HTTP error {e.response.status_code}")
        return False
    except Exception as e:
        print(f"❌ MarineTraffic: Connection failed - {e}")
        return False

def test_vesselfinder_api():
    """Test VesselFinder API."""
    api_key = os.getenv('VESSELFINDER_API_KEY')
    
    if not api_key:
        print("❌ VesselFinder API key not found")
        print("💡 Set environment variable: export VESSELFINDER_API_KEY='your_key'")
        print("🔗 Sign up at: https://www.vesselfinder.com/api")
        return False
    
    print("🔍 Testing VesselFinder API...")
    
    try:
        # VesselFinder API endpoint
        url = "https://api.vesselfinder.com/vesselslist"
        
        params = {
            'userkey': api_key,
            'format': 'json',
            'north': '82',
            'south': '69', 
            'east': '35',
            'west': '5'
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        vessels = data if isinstance(data, list) else data.get('vessels', [])
        
        if vessels:
            print(f"✅ VesselFinder: Collected {len(vessels)} real vessels")
            return True
        else:
            print("⚠️ VesselFinder: No vessels in Arctic region")
            return True
            
    except Exception as e:
        print(f"❌ VesselFinder: Connection failed - {e}")
        return False

def test_aishub_api():
    """Test AISHub API."""
    username = os.getenv('AISHUB_USERNAME')
    password = os.getenv('AISHUB_PASSWORD')
    
    if not username or not password:
        print("❌ AISHub credentials not found")
        print("💡 Set environment variables:")
        print("   export AISHUB_USERNAME='your_username'")
        print("   export AISHUB_PASSWORD='your_password'")
        print("🔗 Sign up at: https://www.aishub.net/")
        return False
    
    print("🔍 Testing AISHub API...")
    
    try:
        url = "http://data.aishub.net/ws.php"
        
        params = {
            'username': username,
            'format': '1',
            'output': 'json',
            'compress': '0',
            'latmin': '69',
            'latmax': '82',
            'lonmin': '5',
            'lonmax': '35'
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if isinstance(data, list) and len(data) > 0 and not data[0].get('ERROR'):
            vessels = data if isinstance(data, list) else data.get('VESSELS', [])
            print(f"✅ AISHub: Collected {len(vessels)} real vessels")
            return True
        else:
            error_msg = data[0].get('ERROR_MESSAGE', 'Unknown error') if isinstance(data, list) else 'No data'
            print(f"❌ AISHub: {error_msg}")
            return False
            
    except Exception as e:
        print(f"❌ AISHub: Connection failed - {e}")
        return False

def test_norwegian_coastal():
    """Test Norwegian Coastal Administration API."""
    print("🔍 Testing Norwegian Coastal Administration...")
    
    try:
        # Try Norwegian AIS endpoints
        endpoints = [
            "https://www.kystverket.no/api/ais/vessels",
            "https://ais.kystverket.no/api/vessels",
            "https://ais-no.herokuapp.com/ais"
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint, timeout=15)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"✅ Norwegian Coastal: Connected to {endpoint}")
                        print(f"   Response type: {type(data)}")
                        return True
                    except:
                        print(f"⚠️ Norwegian Coastal: {endpoint} - Not JSON response")
                        
            except Exception as e:
                print(f"❌ Norwegian Coastal: {endpoint} failed - {e}")
                continue
        
        print("❌ Norwegian Coastal: All endpoints failed")
        return False
        
    except Exception as e:
        print(f"❌ Norwegian Coastal: General error - {e}")
        return False

def test_copernicus_sar():
    """Test Copernicus Sentinel SAR data access."""
    username = os.getenv('COPERNICUS_USERNAME')
    password = os.getenv('COPERNICUS_PASSWORD')
    
    if not username or not password:
        print("❌ Copernicus credentials not found")
        print("💡 Set environment variables:")
        print("   export COPERNICUS_USERNAME='your_username'")
        print("   export COPERNICUS_PASSWORD='your_password'")
        print("🔗 Register at: https://dataspace.copernicus.eu/")
        return False
    
    print("🔍 Testing Copernicus Data Space...")
    
    try:
        # Copernicus Data Space API
        auth_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        
        auth_data = {
            'grant_type': 'password',
            'username': username,
            'password': password,
            'client_id': 'cdse-public'
        }
        
        auth_response = requests.post(auth_url, data=auth_data, timeout=30)
        auth_response.raise_for_status()
        
        token = auth_response.json()['access_token']
        
        # Search for Sentinel-1 products
        search_url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
        
        # Recent date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        params = {
            '$filter': f"Collection/Name eq 'SENTINEL-1' and "
                      f"ContentDate/Start ge {start_date.strftime('%Y-%m-%d')}T00:00:00.000Z and "
                      f"ContentDate/Start le {end_date.strftime('%Y-%m-%d')}T23:59:59.999Z and "
                      f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'beginPosition' and att/OData.CSC.DoubleAttribute/Value ge 69) and "
                      f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'endPosition' and att/OData.CSC.DoubleAttribute/Value le 82)",
            '$top': '10'
        }
        
        headers = {'Authorization': f'Bearer {token}'}
        
        response = requests.get(search_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        products = data.get('value', [])
        
        print(f"✅ Copernicus: Found {len(products)} Sentinel-1 products")
        
        if products:
            for product in products[:2]:
                name = product.get('Name', 'Unknown')
                date = product.get('ContentDate', {}).get('Start', 'Unknown')
                print(f"   🛰️ {name[:50]}... ({date[:10]})")
        
        return True
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("❌ Copernicus: Invalid credentials")
        else:
            print(f"❌ Copernicus: HTTP error {e.response.status_code}")
        return False
    except Exception as e:
        print(f"❌ Copernicus: Connection failed - {e}")
        return False

def generate_setup_instructions(test_results):
    """Generate setup instructions based on test results."""
    print("\n" + "="*60)
    print("📋 REAL DATA SETUP RESULTS")
    print("="*60)
    
    working_sources = [name for name, status in test_results.items() if status]
    failed_sources = [name for name, status in test_results.items() if not status]
    
    if working_sources:
        print(f"✅ Working data sources: {', '.join(working_sources)}")
    
    if failed_sources:
        print(f"❌ Failed data sources: {', '.join(failed_sources)}")
    
    print("\n🎯 NEXT STEPS:")
    
    if not any(test_results.values()):
        print("1. 🔑 Get API credentials for at least one AIS provider")
        print("2. 🛰️ Register for free Copernicus Sentinel data access")
        print("3. 📝 Set environment variables with your credentials")
        print("4. 🔄 Re-run this test script")
        print("\n💡 See REAL_DATA_SETUP.md for detailed instructions")
    
    elif working_sources:
        print("1. ✅ You have working data sources!")
        print("2. 🚀 Run the surveillance pipeline:")
        print("   python scripts/working_surveillance_pipeline.py --mode single")
        print("3. 📊 Check outputs in outputs/surveillance_runs/")
        
        if len(working_sources) < 2:
            print("4. 💡 Consider adding backup data sources for redundancy")
    
    print("\n💰 COST ESTIMATE:")
    if 'MarineTraffic' in working_sources:
        print("   📊 MarineTraffic API: ~$50-150/month")
    if 'Copernicus' in working_sources:
        print("   🛰️ Copernicus SAR: Free")
    if not any('MarineTraffic' in s or 'VesselFinder' in s for s in working_sources):
        print("   💡 Free sources have limited Arctic coverage")

def main():
    """Test all real data sources."""
    print("🌊 Arctic Shadow Tracker - Real Data Connection Test")
    print("="*60)
    print("Testing connections to actual AIS and SAR data sources...")
    print()
    
    test_results = {}
    
    # Test AIS sources
    test_results['MarineTraffic'] = test_marinetraffic_api()
    test_results['VesselFinder'] = test_vesselfinder_api() 
    test_results['AISHub'] = test_aishub_api()
    test_results['Norwegian_Coastal'] = test_norwegian_coastal()
    
    print()
    
    # Test SAR sources
    test_results['Copernicus'] = test_copernicus_sar()
    
    # Generate summary
    generate_setup_instructions(test_results)
    
    # Save test results
    output_dir = Path('outputs/data_tests')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = output_dir / f"real_data_test_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_results': test_results,
            'working_sources': [k for k, v in test_results.items() if v],
            'failed_sources': [k for k, v in test_results.items() if not v]
        }, f, indent=2)
    
    print(f"\n📁 Test results saved to: {results_file}")
    
    return test_results

if __name__ == "__main__":
    main()