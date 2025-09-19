#!/usr/bin/env python3
"""
Simple test to show BarentsWatch streaming works
"""

import os
import sys
import json
import time
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    print("❌ requests module not found")
    print("💡 Run: pip install requests")
    REQUESTS_AVAILABLE = False

def test_stream_connection():
    """Test streaming connection to BarentsWatch."""
    print("🌊 Testing BarentsWatch Stream Connection")
    print("=" * 50)
    
    if not REQUESTS_AVAILABLE:
        print("❌ Cannot test - requests module missing")
        return False
    
    # Get secret from config file or environment
    client_secret = None
    
    # Try config file first
    try:
        import yaml
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        client_secret = config['barentswatch']['client_secret']
        print("🔑 Using secret from config.yaml")
    except:
        # Fallback to environment variable
        client_secret = os.getenv('BARENTSWATCH_CLIENT_SECRET')
        if client_secret:
            print("🔑 Using secret from environment variable")
    
    if not client_secret:
        print("❌ BARENTSWATCH_CLIENT_SECRET not found")
        print("💡 Either:")
        print("   1. Add to config.yaml under barentswatch.client_secret")
        print("   2. Run: export BARENTSWATCH_CLIENT_SECRET='your_secret'")
        return False
    
    print("🔑 Getting access token...")
    
    # Get access token
    auth_url = "https://id.barentswatch.no/connect/token"
    auth_data = {
        'client_id': 'henrikformoe@gmail.com:ArcticShadowTrackerAIS',
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': 'ais'
    }
    
    try:
        auth_response = requests.post(auth_url, data=auth_data, timeout=30)
        
        if auth_response.status_code != 200:
            print(f"❌ Auth failed: {auth_response.status_code}")
            print(f"Response: {auth_response.text}")
            return False
        
        token_data = auth_response.json()
        access_token = token_data.get('access_token')
        
        print("✅ Got access token")
        print("🌊 Connecting to live stream...")
        
        # Connect to stream
        stream_url = "https://live.ais.barentswatch.no/v1/combined"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Simple filter for Arctic vessels
        filter_data = {
            "shipTypes": [30, 70],  # Fishing and cargo
            "Downsample": False
        }
        
        # Start streaming (limit to 10 vessels for demo)
        response = requests.post(
            stream_url,
            headers=headers,
            json=filter_data,
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Connected to stream!")
            print("📡 Receiving live vessel data...\n")
            
            vessel_count = 0
            start_time = time.time()
            
            for line in response.iter_lines():
                if line:
                    try:
                        vessel = json.loads(line.decode('utf-8'))
                        vessel_count += 1
                        
                        # Show vessel info
                        print(f"🚢 Vessel #{vessel_count}")
                        print(f"   MMSI: {vessel.get('mmsi', 'Unknown')}")
                        print(f"   Name: {vessel.get('name', 'Unknown')}")
                        print(f"   Position: {vessel.get('latitude', 0):.3f}°N, {vessel.get('longitude', 0):.3f}°E")
                        print(f"   Speed: {vessel.get('speedOverGround', 0):.1f} knots")
                        print(f"   Time: {vessel.get('msgtime', 'Unknown')}")
                        print("-" * 40)
                        
                        # Stop after 5 vessels or 30 seconds for demo
                        if vessel_count >= 5 or (time.time() - start_time) > 30:
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            print(f"\n✅ Stream test complete!")
            print(f"📊 Received {vessel_count} live vessels in {time.time() - start_time:.1f} seconds")
            print("🎯 Streaming works! This would run 24/7 in production.")
            return True
            
        else:
            print(f"❌ Stream connection failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_latest_endpoint():
    """Test the latest position endpoint as backup."""
    print("\n🔄 Testing latest position endpoint...")
    
    client_secret = os.getenv('BARENTSWATCH_CLIENT_SECRET')
    if not client_secret:
        return False
    
    # Get token
    auth_url = "https://id.barentswatch.no/connect/token"
    auth_data = {
        'client_id': 'henrikformoe@gmail.com:ArcticShadowTrackerAIS',
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': 'ais'
    }
    
    try:
        auth_response = requests.post(auth_url, data=auth_data, timeout=30)
        token_data = auth_response.json()
        access_token = token_data.get('access_token')
        
        # Get latest positions
        latest_url = "https://live.ais.barentswatch.no/v1/latest/combined"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        response = requests.get(latest_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            vessels = response.json()
            print(f"✅ Got {len(vessels)} latest vessel positions")
            
            # Show first 3
            for i, vessel in enumerate(vessels[:3]):
                print(f"🚢 {vessel.get('name', 'Unknown')} (MMSI: {vessel.get('mmsi', 'Unknown')})")
                print(f"   📍 {vessel.get('latitude', 0):.3f}°N, {vessel.get('longitude', 0):.3f}°E")
            
            return True
        else:
            print(f"❌ Latest endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Latest test error: {e}")
        return False

if __name__ == "__main__":
    print("🇳🇴 BarentsWatch Streaming Test")
    print("=" * 40)
    
    # Test streaming
    stream_works = test_stream_connection()
    
    # Test latest as backup
    latest_works = test_latest_endpoint()
    
    print("\n📋 Test Summary:")
    print(f"🌊 Stream API: {'✅ Works' if stream_works else '❌ Failed'}")
    print(f"📍 Latest API: {'✅ Works' if latest_works else '❌ Failed'}")
    
    if stream_works:
        print("\n🎯 Ready for 24/7 streaming!")
        print("💡 Run: python barentswatch_stream_collector.py")
    else:
        print("\n💡 Check your BARENTSWATCH_CLIENT_SECRET")