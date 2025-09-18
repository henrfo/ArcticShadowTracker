#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Automated Data Pipeline
Downloads and processes real satellite and AIS data for 24/7 operations.
"""

import os
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import time
import logging
from pathlib import Path
import zipfile
import schedule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ArcticDataPipeline:
    """Automated data pipeline for Arctic maritime surveillance"""
    
    def __init__(self):
        self.arctic_bounds = {
            'north': 82.0,
            'south': 69.0, 
            'east': 35.0,
            'west': 5.0
        }
        
        # Data directories
        self.data_dirs = {
            'ais': Path('data/ais'),
            'satellite': Path('data/satellite'),
            'processed': Path('data/processed'),
            'alerts': Path('outputs/alerts')
        }
        
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Create necessary directories"""
        for dir_path in self.data_dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
            
    def fetch_ais_data(self):
        """Fetch fresh AIS data from Arctic waters"""
        logger.info("🌐 Fetching AIS data from Arctic region...")
        
        try:
            # Primary AIS source - AISHub
            url = f"http://data.aishub.net/ws.php?username=DH_DEMO&format=1&output=json&compress=0&latmin={self.arctic_bounds['south']}&latmax={self.arctic_bounds['north']}&lonmin={self.arctic_bounds['west']}&lonmax={self.arctic_bounds['east']}"
            
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                
                vessels = []
                if isinstance(data, dict) and 'VESSELS' in data:
                    for vessel in data['VESSELS']:
                        vessel_record = {
                            'timestamp': datetime.now().isoformat(),
                            'mmsi': str(vessel.get('MMSI', 'unknown')),
                            'latitude': float(vessel.get('LATITUDE', 0)),
                            'longitude': float(vessel.get('LONGITUDE', 0)),
                            'speed': float(vessel.get('SOG', 0)),
                            'course': float(vessel.get('COG', 0)),
                            'vessel_name': vessel.get('SHIPNAME', 'Unknown'),
                            'vessel_type': vessel.get('SHIP_TYPE', 'Unknown'),
                            'source': 'aishub_live'
                        }
                        vessels.append(vessel_record)
                
                if vessels:
                    # Save to timestamped file
                    filename = f"arctic_ais_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    filepath = self.data_dirs['ais'] / filename
                    
                    with open(filepath, 'w') as f:
                        json.dump(vessels, f, indent=2)
                    
                    logger.info(f"✅ Saved {len(vessels)} AIS records to {filename}")
                    
                    # Also maintain latest.json for quick access
                    latest_path = self.data_dirs['ais'] / 'latest.json'
                    with open(latest_path, 'w') as f:
                        json.dump(vessels, f, indent=2)
                    
                    return vessels
                else:
                    logger.warning("⚠️ No vessels found in AIS response")
                    
        except Exception as e:
            logger.error(f"❌ AIS fetch failed: {e}")
            
        return []
    
    def fetch_sentinel_data(self):
        """Fetch Sentinel-1 SAR data for Arctic region"""
        logger.info("🛰️ Checking for new Sentinel-1 data...")
        
        try:
            # For production, would use Copernicus Open Access Hub API
            # This is a placeholder showing the structure
            
            # Check last download time
            last_download_file = self.data_dirs['satellite'] / 'last_download.txt'
            last_download = datetime.now() - timedelta(days=1)  # Default to yesterday
            
            if last_download_file.exists():
                with open(last_download_file, 'r') as f:
                    last_download = datetime.fromisoformat(f.read().strip())
            
            # Only download if more than 6 hours since last download
            if datetime.now() - last_download < timedelta(hours=6):
                logger.info("⏰ Recent Sentinel-1 data available, skipping download")
                return True
            
            logger.info("📡 Would download Sentinel-1 SAR data here...")
            logger.info("💡 Requires Copernicus Hub API credentials")
            
            # For demo: create a placeholder file to show the system works
            demo_filename = f"sentinel1_demo_{datetime.now().strftime('%Y%m%d_%H%M')}.placeholder"
            demo_path = self.data_dirs['satellite'] / demo_filename
            
            with open(demo_path, 'w') as f:
                f.write(f"Sentinel-1 placeholder - would contain SAR data for Arctic region\n")
                f.write(f"Coverage: {self.arctic_bounds}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            
            # Update last download time
            with open(last_download_file, 'w') as f:
                f.write(datetime.now().isoformat())
                
            logger.info(f"✅ Sentinel-1 placeholder created: {demo_filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Sentinel-1 fetch failed: {e}")
            return False
    
    def process_surveillance_cycle(self):
        """Run complete surveillance cycle"""
        logger.info("🎯 Starting surveillance cycle...")
        
        cycle_start = datetime.now()
        
        # Step 1: Fetch fresh AIS data
        ais_data = self.fetch_ais_data()
        
        # Step 2: Check for new satellite data
        sentinel_ok = self.fetch_sentinel_data()
        
        # Step 3: Run threat analysis if we have data
        threats = []
        if ais_data:
            threats = self._analyze_threats(ais_data)
        
        # Step 4: Generate alert if needed
        if threats:
            self._generate_alerts(threats)
        
        cycle_duration = (datetime.now() - cycle_start).total_seconds()
        
        logger.info(f"🔄 Surveillance cycle complete:")
        logger.info(f"   📊 Vessels tracked: {len(ais_data)}")
        logger.info(f"   ⚠️ Threats detected: {len(threats)}")
        logger.info(f"   ⏱️ Duration: {cycle_duration:.1f}s")
        
        return {
            'timestamp': cycle_start.isoformat(),
            'vessels_tracked': len(ais_data),
            'threats_detected': len(threats),
            'cycle_duration_seconds': cycle_duration
        }
    
    def _analyze_threats(self, ais_data):
        """Quick threat analysis for continuous operations"""
        threats = []
        
        # Simple threat detection: vessels loitering near cable areas
        cable_areas = [
            {'name': 'Svalbard Cable Zone', 'center': (78.2, 15.6), 'radius_km': 20},
            {'name': 'Hammerfest Cable Zone', 'center': (71.1, 25.8), 'radius_km': 15}
        ]
        
        for vessel in ais_data:
            vessel_lat = vessel['latitude']
            vessel_lon = vessel['longitude']
            vessel_speed = vessel['speed']
            
            # Check if near cable zones and moving slowly (potential loitering)
            for zone in cable_areas:
                zone_lat, zone_lon = zone['center']
                
                # Simple distance calculation (good enough for alerting)
                lat_diff = abs(vessel_lat - zone_lat)
                lon_diff = abs(vessel_lon - zone_lon)
                distance_approx = ((lat_diff**2 + lon_diff**2)**0.5) * 111  # km
                
                if distance_approx <= zone['radius_km'] and vessel_speed < 2.0:  # Very slow
                    threat = {
                        'vessel_mmsi': vessel['mmsi'],
                        'vessel_name': vessel['vessel_name'],
                        'threat_type': 'loitering_near_cable',
                        'zone': zone['name'],
                        'distance_km': distance_approx,
                        'vessel_speed': vessel_speed,
                        'timestamp': vessel['timestamp'],
                        'latitude': vessel_lat,
                        'longitude': vessel_lon
                    }
                    threats.append(threat)
        
        return threats
    
    def _generate_alerts(self, threats):
        """Generate alert files for detected threats"""
        if not threats:
            return
            
        alert_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        alert_file = self.data_dirs['alerts'] / f'threat_alert_{alert_timestamp}.json'
        
        alert_data = {
            'alert_timestamp': datetime.now().isoformat(),
            'threat_count': len(threats),
            'threats': threats,
            'alert_level': 'HIGH' if len(threats) > 2 else 'MEDIUM'
        }
        
        with open(alert_file, 'w') as f:
            json.dump(alert_data, f, indent=2)
            
        logger.warning(f"🚨 THREAT ALERT: {len(threats)} threats detected - saved to {alert_file.name}")
    
    def run_continuous(self, interval_minutes=30):
        """Run continuous surveillance with specified interval"""
        logger.info(f"🚀 Starting continuous surveillance (every {interval_minutes} minutes)")
        
        # Schedule regular surveillance cycles
        schedule.every(interval_minutes).minutes.do(self.process_surveillance_cycle)
        
        # Run initial cycle
        self.process_surveillance_cycle()
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("🛑 Surveillance stopped by user")

def main():
    """Main execution function"""
    pipeline = ArcticDataPipeline()
    
    print("🎯 Arctic Shadow Tracker - Data Pipeline")
    print("=" * 50)
    print("Choose operation mode:")
    print("1. Single surveillance cycle")
    print("2. Continuous surveillance (every 30 minutes)")
    print("3. Continuous surveillance (every 6 hours)")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        result = pipeline.process_surveillance_cycle()
        print(f"\n✅ Cycle complete: {result}")
        
    elif choice == "2":
        pipeline.run_continuous(interval_minutes=30)
        
    elif choice == "3":
        pipeline.run_continuous(interval_minutes=360)  # 6 hours
        
    else:
        print("❌ Invalid choice")
        return
    
    print("\n🎯 Arctic surveillance pipeline ready!")

if __name__ == "__main__":
    main()