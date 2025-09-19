#!/usr/bin/env python3
"""
Super simple streaming demo that shows fetch vs stream
"""

def demo_fetch_vs_stream():
    """Show the difference between fetch and stream conceptually."""
    print("🌊 FETCH vs STREAM Demo")
    print("=" * 40)
    
    print("\n📦 FETCH (Old Way):")
    print("   1. Connect to API")
    print("   2. Get all data at once")
    print("   3. Connection closes")
    print("   4. Process data")
    print("   5. DONE - no more data")
    
    print("\n🌊 STREAM (New Way):")
    print("   1. Connect to API")
    print("   2. Keep connection open")
    print("   3. Receive data continuously")
    print("   4. Process each vessel as it arrives")
    print("   5. NEVER ENDS - data flows 24/7")
    
    print("\n🔄 Simulating Stream (for 10 seconds):")
    
    import time
    import random
    
    # Simulate streaming vessels
    vessel_names = ["ARCTIC_EXPLORER", "POLAR_STAR", "ICE_BREAKER", "FISHING_VESSEL_1", "CARGO_SHIP_42"]
    
    start_time = time.time()
    vessel_count = 0
    
    while time.time() - start_time < 10:  # Run for 10 seconds
        # Simulate receiving a vessel every 1-3 seconds
        time.sleep(random.uniform(1, 3))
        
        vessel_count += 1
        vessel_name = random.choice(vessel_names)
        lat = round(random.uniform(70, 82), 3)  # Arctic latitudes
        lon = round(random.uniform(10, 40), 3)  # Barents Sea
        speed = round(random.uniform(0, 15), 1)
        
        print(f"🚢 Vessel #{vessel_count}: {vessel_name}")
        print(f"   📍 {lat}°N, {lon}°E")
        print(f"   ⚡ {speed} knots")
        print(f"   ⏰ {time.strftime('%H:%M:%S')}")
        print("-" * 30)
    
    print(f"\n✅ Stream simulation complete!")
    print(f"📊 Received {vessel_count} vessels in 10 seconds")
    print("🎯 Real stream would run forever!")

def show_real_api_example():
    """Show what the real API calls look like."""
    print("\n🔧 Real API Examples:")
    print("=" * 30)
    
    print("📡 FETCH (one-time):")
    print("   curl 'https://live.ais.barentswatch.no/v1/latest/combined'")
    print("   → Returns: [vessel1, vessel2, ...] DONE")
    
    print("\n🌊 STREAM (continuous):")
    print("   curl 'https://live.ais.barentswatch.no/v1/combined' --stream")
    print("   → Returns: vessel1")
    print("   → Returns: vessel2")  
    print("   → Returns: vessel3")
    print("   → Returns: ... (never stops)")
    
    print("\n🐍 Python Implementation:")
    print("""
# FETCH
response = requests.get(url)
vessels = response.json()  # Get all at once
# Done

# STREAM  
response = requests.post(url, stream=True)
for line in response.iter_lines():  # Never ends
    vessel = json.loads(line)
    process(vessel)  # Handle each as it arrives
""")

if __name__ == "__main__":
    demo_fetch_vs_stream()
    show_real_api_example()
    
    print("\n🎯 Key Difference:")
    print("   FETCH: Get data → Process → Stop")
    print("   STREAM: Get data → Process → Get more → Process → ...")
    print("\n💡 For 24/7 surveillance, use STREAM!")