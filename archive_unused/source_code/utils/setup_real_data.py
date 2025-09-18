#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Real Data Setup
Downloads and prepares real maritime data for operational use.
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import json

def setup_directories():
    """Create necessary data directories"""
    dirs = [
        'data/ais',
        'data/satellite', 
        'data/cables',
        'outputs/operational_reports'
    ]
    
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
        print(f"✅ Created: {dir_path}")

def download_sample_ais_data():
    """Download real AIS data samples"""
    print("📡 Downloading sample AIS data...")
    
    # Try to get real AIS data from AISHub
    try:
        # Arctic bounds
        url = "http://data.aishub.net/ws.php?username=DH_DEMO&format=1&output=json&compress=0&latmin=69&latmax=81&lonmin=5&lonmax=30"
        response = requests.get(url, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and 'VESSELS' in data:
                vessels = data['VESSELS']
                
                # Convert to DataFrame
                ais_df = pd.DataFrame([{
                    'mmsi': vessel.get('MMSI', 'unknown'),
                    'latitude': vessel.get('LATITUDE', 0),
                    'longitude': vessel.get('LONGITUDE', 0),
                    'speed': vessel.get('SOG', 0),
                    'course': vessel.get('COG', 0),
                    'vessel_name': vessel.get('SHIPNAME', 'Unknown'),
                    'timestamp': datetime.now().isoformat()
                } for vessel in vessels])
                
                # Save to CSV
                filename = f"data/ais/arctic_ais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                ais_df.to_csv(filename, index=False)
                print(f"✅ Saved {len(ais_df)} AIS records to {filename}")
                return True
                
    except Exception as e:
        print(f"❌ AIS download failed: {e}")
    
    return False

def create_sample_data():
    """Create sample data files for testing"""
    print("📝 Creating sample test data...")
    
    # Sample AIS data for Arctic region
    sample_ais = pd.DataFrame([
        {
            'mmsi': '257001234',
            'latitude': 78.2,
            'longitude': 15.6, 
            'speed': 12.5,
            'course': 180,
            'vessel_name': 'ARCTIC_EXPLORER',
            'vessel_type': 'Cargo',
            'timestamp': datetime.now().isoformat()
        },
        {
            'mmsi': '257005678',
            'latitude': 71.1,
            'longitude': 25.8,
            'speed': 8.2,
            'course': 45,
            'vessel_name': 'BARENTS_FISHER',
            'vessel_type': 'Fishing',
            'timestamp': datetime.now().isoformat()
        },
        {
            'mmsi': '257009999',
            'latitude': 74.0,
            'longitude': 30.0,
            'speed': 0.1,  # Loitering
            'course': 0,
            'vessel_name': 'SUSPICIOUS_VESSEL',
            'vessel_type': 'Unknown',
            'timestamp': datetime.now().isoformat()
        }
    ])
    
    filename = f"data/ais/sample_arctic_vessels.csv"
    sample_ais.to_csv(filename, index=False)
    print(f"✅ Created sample AIS data: {filename}")

def main():
    """Main setup function"""
    print("🚀 Arctic Shadow Tracker - Real Data Setup")
    print("=" * 50)
    
    # Step 1: Create directories
    setup_directories()
    
    # Step 2: Try to download real data
    if not download_sample_ais_data():
        print("⚠️ Live AIS download failed, creating sample data...")
        create_sample_data()
    
    # Step 3: Ready message
    print("\n✅ Setup complete!")
    print("\n📋 Next steps:")
    print("1. pip install -r config/requirements.txt")
    print("2. jupyter notebook notebooks/operational/operational_arctic_surveillance.ipynb")
    print("3. Run all cells to start Arctic surveillance")
    
    print("\n📊 Data available:")
    if os.path.exists('data/ais'):
        ais_files = [f for f in os.listdir('data/ais') if f.endswith('.csv')]
        print(f"   🚢 AIS data files: {len(ais_files)}")
    
    print("\n🎯 Arctic Shadow Tracker is ready for operational use!")

if __name__ == "__main__":
    main()