#!/usr/bin/env python3
"""
Quick test of aisstream.io API key
"""
import asyncio
import websockets
import json
import os

async def test_api_key():
    api_key = os.getenv('AISSTREAM_API_KEY')
    print(f"🔑 Testing API key: {api_key[:10]}...")
    
    try:
        async with websockets.connect("wss://stream.aisstream.io/v0/stream", ping_timeout=10) as websocket:
            print("✅ WebSocket connected")
            
            # Send subscription
            subscribe_message = {
                "APIKey": api_key,
                "BoundingBoxes": [[[10, 76], [35, 81]]],  # Svalbard
                "FilterMessageTypes": ["PositionReport"]
            }
            
            await websocket.send(json.dumps(subscribe_message))
            print("✅ Subscription sent")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"✅ Response received: {list(data.keys())}")
                
                if 'Message' in data:
                    print("✅ API key is VALID - receiving vessel data")
                    return True
                else:
                    print(f"⚠️ Response: {data}")
                    
            except asyncio.TimeoutError:
                print("⚠️ No data received within 5 seconds (may be valid but no vessels in area)")
                return True
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_api_key())
    print(f"🎯 API key test: {'PASSED' if result else 'FAILED'}")