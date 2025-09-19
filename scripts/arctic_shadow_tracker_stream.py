#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Streaming Version
Real-time Arctic maritime surveillance system

Based on barentswatch_test_v2.ipynb - transforms notebook functions into streaming script
Runs every 30 minutes to detect dark vessels and monitor submarine cables

Features:
- Real BarentsWatch AIS data collection
- Norwegian vessel filtering (MMSI 257-259)
- Submarine cable proximity monitoring
- Dark vessel detection (2-48 hour AIS gaps)
- SAR satellite imagery correlation
- CSV database for time-series analysis
- Interactive HTML dashboard
"""

import yaml
import requests
import json
import pandas as pd
import numpy as np
import folium
import matplotlib.pyplot as plt
import time
import schedule
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arctic_surveillance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

class ArcticConfig:
    """Configuration for Arctic surveillance system"""
    
    # Arctic surveillance regions (from notebook)
    ARCTIC_REGIONS = {
        'svalbard': {
            'name': 'Svalbard Waters',
            'bbox': [10.0, 76.0, 35.0, 81.0],
            'priority': 'HIGH'
        },
        'north_norway': {
            'name': 'Northern Norway Coast',
            'bbox': [15.0, 68.0, 32.0, 71.5],
            'priority': 'HIGH'
        },
        'barents_sea': {
            'name': 'Central Barents Sea',
            'bbox': [20.0, 72.0, 40.0, 76.0],
            'priority': 'CRITICAL'
        }
    }
    
    # Submarine cables (from notebook)
    SUBMARINE_CABLES = {
        'svalbard_cable': {
            'name': 'Svalbard Undersea Cable System',
            'coordinates': [[78.9, 11.9], [71.0, 25.8]],
            'status': 'CRITICAL',
            'alert_distance_km': 10
        },
        'lofoten_vesteralen': {
            'name': 'Lofoten-Vesterålen Cable',
            'coordinates': [[68.8, 13.6], [69.3, 16.0]],
            'status': 'HIGH',
            'alert_distance_km': 5
        },
        'norway_uk': {
            'name': 'Norway-UK Cable (Arctic Section)',
            'coordinates': [[70.0, 23.0], [69.0, 18.0]],
            'status': 'HIGH',
            'alert_distance_km': 8
        }
    }
    
    # Norwegian vessel filtering patterns (from notebook)
    NORWEGIAN_MMSI_PREFIXES = ('257', '258', '259')
    NORWEGIAN_NAME_PATTERNS = [
        'NO ', 'NORGE', 'NORSK', 'BERGEN', 'OSLO', 'STAVANGER', 'TROMSOE', 'TROMSO',
        'HAVILA', 'HURTIGRUTEN', 'FJORD', 'STIND', 'FISK', 'FROST', 'POLAR',
        'KVAL', 'SUND', 'BORG', 'HOLM', 'NESS', 'VIK', 'HAUG', 'STRAND'
    ]
    
    # Dark vessel detection parameters
    DARK_VESSEL_MIN_HOURS = 2
    DARK_VESSEL_MAX_HOURS = 48
    
    # Data paths
    DATA_DIR = Path('data_stream')
    CSV_DIR = DATA_DIR / 'csv'
    INTELLIGENCE_DIR = DATA_DIR / 'intelligence'
    DASHBOARD_DIR = DATA_DIR / 'dashboard'

    def __init__(self):
        # Create directories
        for dir_path in [self.DATA_DIR, self.CSV_DIR, self.INTELLIGENCE_DIR, self.DASHBOARD_DIR]:
            dir_path.mkdir(exist_ok=True)

# Initialize configuration
config = ArcticConfig()

# =============================================================================
# API MANAGEMENT
# =============================================================================

class APIManager:
    """Manage API connections and authentication"""
    
    def __init__(self):
        self.barents_config = None
        self.sentinel_config = None
        self.load_config()
    
    def load_config(self):
        """Load API credentials from config.yaml"""
        try:
            with open('config.yaml', 'r') as f:
                yaml_config = yaml.safe_load(f)
            
            # BarentsWatch config
            if 'barentswatch' in yaml_config:
                self.barents_config = yaml_config['barentswatch']
                logger.info("✅ BarentsWatch API configured")
            
            # Sentinel Hub config (for future SAR integration)
            if 'sentinel_hub' in yaml_config:
                self.sentinel_config = yaml_config['sentinel_hub']
                logger.info("✅ Sentinel Hub API configured")
                
        except FileNotFoundError:
            logger.error("❌ config.yaml not found")
        except Exception as e:
            logger.error(f"❌ Error loading config: {e}")
    
    def get_barentswatch_token(self) -> Optional[str]:
        """Get access token for BarentsWatch API"""
        if not self.barents_config:
            logger.error("❌ BarentsWatch config not available")
            return None
        
        token_url = "https://id.barentswatch.no/connect/token"
        data = {
            'client_id': self.barents_config['client_id'],
            'client_secret': self.barents_config['client_secret'],
            'scope': self.barents_config['scope'],
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(token_url, data=data, timeout=30)
            response.raise_for_status()
            return response.json()['access_token']
        except Exception as e:
            logger.error(f"❌ Token request failed: {e}")
            return None

# Initialize API manager
api_manager = APIManager()

# =============================================================================
# DATA COLLECTION
# =============================================================================

class AISDataCollector:
    """Collect and filter AIS data from BarentsWatch"""
    
    def __init__(self, api_manager: APIManager):
        self.api_manager = api_manager
    
    def is_norwegian_vessel(self, mmsi: str, name: str) -> bool:
        """Check if vessel is Norwegian based on MMSI and name patterns"""
        # Check MMSI prefix
        if mmsi and str(mmsi).startswith(config.NORWEGIAN_MMSI_PREFIXES):
            return True
        
        # Check name patterns
        if name and any(pattern in name.upper() for pattern in config.NORWEGIAN_NAME_PATTERNS):
            return True
        
        return False
    
    def collect_ais_data(self) -> List[Dict]:
        """Collect current AIS vessel positions (excluding Norwegian vessels)"""
        logger.info("📡 Collecting AIS data from BarentsWatch...")
        
        token = self.api_manager.get_barentswatch_token()
        if not token:
            logger.error("❌ Cannot get BarentsWatch token")
            return []
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        
        try:
            url = "https://live.ais.barentswatch.no/v1/latest/combined"
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            all_vessels = response.json()
            arctic_vessels = []
            norwegian_filtered = 0
            
            for vessel in all_vessels:
                lat = vessel.get('latitude', 0)
                if lat >= 65.0:  # Arctic threshold
                    mmsi = vessel.get('mmsi', '')
                    name = vessel.get('name', 'Unknown')
                    
                    if not self.is_norwegian_vessel(mmsi, name):
                        # Create simplified vessel record
                        vessel_data = {
                            'mmsi': mmsi,
                            'name': name,
                            'latitude': lat,
                            'longitude': vessel.get('longitude', 0),
                            'speed': vessel.get('speedOverGround', 0),
                            'course': vessel.get('courseOverGround', 0),
                            'timestamp': datetime.now().isoformat(),
                            'vessel_type': vessel.get('shipType', 'Unknown'),
                            'collection_time': datetime.now()
                        }
                        arctic_vessels.append(vessel_data)
                    else:
                        norwegian_filtered += 1
            
            logger.info(f"✅ Found {len(arctic_vessels)} non-Norwegian Arctic vessels")
            logger.info(f"🇳🇴 Filtered {norwegian_filtered} Norwegian vessels")
            return arctic_vessels
            
        except Exception as e:
            logger.error(f"❌ AIS collection failed: {e}")
            return []

# =============================================================================
# DARK VESSEL DETECTION
# =============================================================================

class DarkVesselDetector:
    """Detect vessels that have gone dark (turned off AIS)"""
    
    def __init__(self):
        self.history_file = config.CSV_DIR / 'ais_history.csv'
        self.dark_vessels_file = config.CSV_DIR / 'dark_vessels.csv'
    
    def load_vessel_history(self) -> pd.DataFrame:
        """Load historical AIS data"""
        if self.history_file.exists():
            try:
                return pd.read_csv(self.history_file, parse_dates=['timestamp', 'collection_time'])
            except Exception as e:
                logger.error(f"Error loading history: {e}")
                return pd.DataFrame()
        return pd.DataFrame()
    
    def save_vessel_history(self, df: pd.DataFrame):
        """Save vessel history to CSV"""
        try:
            df.to_csv(self.history_file, index=False)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    def update_history(self, current_vessels: List[Dict]) -> pd.DataFrame:
        """Update vessel history with current data"""
        # Load existing history
        history_df = self.load_vessel_history()
        
        # Convert current vessels to DataFrame
        if current_vessels:
            current_df = pd.DataFrame(current_vessels)
            current_df['timestamp'] = pd.to_datetime(current_df['timestamp'])
            current_df['collection_time'] = pd.to_datetime(current_df['collection_time'])
            
            # Append to history
            if not history_df.empty:
                history_df = pd.concat([history_df, current_df], ignore_index=True)
            else:
                history_df = current_df
            
            # Keep only last 7 days of data for performance
            cutoff_date = datetime.now() - timedelta(days=7)
            history_df = history_df[history_df['collection_time'] >= cutoff_date]
            
            # Save updated history
            self.save_vessel_history(history_df)
        
        return history_df
    
    def detect_dark_vessels(self, current_vessels: List[Dict], history_df: pd.DataFrame) -> List[Dict]:
        """Detect vessels that have gone dark"""
        logger.info("🌑 Detecting dark vessels...")
        
        current_time = datetime.now()
        current_mmsis = {str(vessel['mmsi']) for vessel in current_vessels if vessel['mmsi']}
        
        dark_vessels = []
        
        if history_df.empty:
            logger.info("✅ No historical data for dark vessel detection")
            return dark_vessels
        
        # Get vessels seen in last 48 hours
        recent_cutoff = current_time - timedelta(hours=config.DARK_VESSEL_MAX_HOURS)
        recent_vessels = history_df[history_df['collection_time'] >= recent_cutoff]
        
        # Group by MMSI to find last seen times
        for mmsi, vessel_group in recent_vessels.groupby('mmsi'):
            mmsi_str = str(mmsi)
            if mmsi_str not in current_mmsis:
                # Vessel not in current data - check if it went dark
                last_record = vessel_group.loc[vessel_group['collection_time'].idxmax()]
                last_seen = last_record['collection_time']
                hours_since_seen = (current_time - last_seen).total_seconds() / 3600
                
                # Check if within dark vessel detection window
                if config.DARK_VESSEL_MIN_HOURS <= hours_since_seen <= config.DARK_VESSEL_MAX_HOURS:
                    dark_vessel = {
                        'mmsi': mmsi,
                        'name': last_record['name'],
                        'last_seen': last_seen.isoformat(),
                        'hours_since_seen': round(hours_since_seen, 1),
                        'last_latitude': last_record['latitude'],
                        'last_longitude': last_record['longitude'],
                        'last_speed': last_record['speed'],
                        'detection_time': current_time.isoformat(),
                        'status': 'DARK_VESSEL_SUSPECTED'
                    }
                    dark_vessels.append(dark_vessel)
        
        if dark_vessels:
            logger.warning(f"🚨 Found {len(dark_vessels)} suspected dark vessels!")
            for vessel in dark_vessels:
                logger.warning(f"   📍 {vessel['name']} (MMSI: {vessel['mmsi']}) - Dark for {vessel['hours_since_seen']}h")
            
            # Save dark vessels to CSV
            dark_df = pd.DataFrame(dark_vessels)
            if self.dark_vessels_file.exists():
                existing_dark = pd.read_csv(self.dark_vessels_file)
                dark_df = pd.concat([existing_dark, dark_df], ignore_index=True)
            dark_df.to_csv(self.dark_vessels_file, index=False)
        else:
            logger.info("✅ No dark vessels detected")
        
        return dark_vessels

# =============================================================================
# CABLE MONITORING
# =============================================================================

class CableMonitor:
    """Monitor vessel proximity to submarine cables"""
    
    def __init__(self):
        self.cable_alerts_file = config.CSV_DIR / 'cable_alerts.csv'
    
    @staticmethod
    def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        from math import radians, cos, sin, asin, sqrt
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return c * 6371  # Earth radius in km
    
    def point_to_line_distance(self, px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate minimum distance from point to line segment"""
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return self.calculate_distance_km(px, py, x1, y1)
        
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        return self.calculate_distance_km(px, py, closest_x, closest_y)
    
    def check_cable_proximity(self, vessels: List[Dict]) -> List[Dict]:
        """Check if vessels are near submarine cables"""
        logger.info("🔌 Checking vessel proximity to submarine cables...")
        
        cable_alerts = []
        
        for vessel in vessels:
            vessel_lat = vessel['latitude']
            vessel_lon = vessel['longitude']
            
            for cable_id, cable in config.SUBMARINE_CABLES.items():
                coords = cable['coordinates']
                if len(coords) >= 2:
                    start_lat, start_lon = coords[0]
                    end_lat, end_lon = coords[1]
                    
                    distance = self.point_to_line_distance(
                        vessel_lat, vessel_lon,
                        start_lat, start_lon,
                        end_lat, end_lon
                    )
                    
                    if distance <= cable['alert_distance_km']:
                        alert = {
                            'timestamp': datetime.now().isoformat(),
                            'vessel_mmsi': vessel['mmsi'],
                            'vessel_name': vessel['name'],
                            'cable_id': cable_id,
                            'cable_name': cable['name'],
                            'distance_km': round(distance, 2),
                            'alert_threshold': cable['alert_distance_km'],
                            'cable_status': cable['status'],
                            'vessel_latitude': vessel_lat,
                            'vessel_longitude': vessel_lon,
                            'vessel_speed': vessel['speed']
                        }
                        cable_alerts.append(alert)
        
        if cable_alerts:
            logger.warning(f"⚠️ {len(cable_alerts)} cable proximity alerts!")
            for alert in cable_alerts:
                logger.warning(f"   🚢 {alert['vessel_name']} near {alert['cable_name']} ({alert['distance_km']}km)")
            
            # Save alerts to CSV
            alerts_df = pd.DataFrame(cable_alerts)
            if self.cable_alerts_file.exists():
                existing_alerts = pd.read_csv(self.cable_alerts_file)
                alerts_df = pd.concat([existing_alerts, alerts_df], ignore_index=True)
            alerts_df.to_csv(self.cable_alerts_file, index=False)
        else:
            logger.info("✅ No vessels near critical cables")
        
        return cable_alerts

# =============================================================================
# DASHBOARD GENERATOR
# =============================================================================

class DashboardGenerator:
    """Generate interactive HTML dashboard"""
    
    def __init__(self):
        self.dashboard_file = config.DASHBOARD_DIR / 'arctic_surveillance_dashboard.html'
    
    def create_dashboard(self, vessels: List[Dict], dark_vessels: List[Dict], cable_alerts: List[Dict]) -> str:
        """Create interactive HTML dashboard"""
        logger.info("🗺️ Creating surveillance dashboard...")
        
        # Center map on Arctic Norway
        m = folium.Map(location=[72.0, 25.0], zoom_start=4)
        
        # Add submarine cables
        for cable_id, cable in config.SUBMARINE_CABLES.items():
            coords = cable['coordinates']
            if len(coords) >= 2:
                folium.PolyLine(
                    locations=coords,
                    color='red',
                    weight=3,
                    opacity=0.8,
                    popup=f"🔌 {cable['name']} ({cable['status']})"
                ).add_to(m)
        
        # Add current vessels (sample for performance)
        vessel_sample = vessels[:100] if len(vessels) > 100 else vessels
        for vessel in vessel_sample:
            color = 'blue'
            if any(alert['vessel_mmsi'] == vessel['mmsi'] for alert in cable_alerts):
                color = 'orange'  # Near cable
            
            folium.CircleMarker(
                location=[vessel['latitude'], vessel['longitude']],
                radius=5,
                color=color,
                fillColor='lightblue' if color == 'blue' else 'orange',
                fillOpacity=0.7,
                popup=f"🚢 {vessel['name']}<br>MMSI: {vessel['mmsi']}<br>Speed: {vessel['speed']} knots"
            ).add_to(m)
        
        # Add dark vessels
        for vessel in dark_vessels:
            folium.CircleMarker(
                location=[vessel['last_latitude'], vessel['last_longitude']],
                radius=8,
                color='red',
                fillColor='darkred',
                fillOpacity=0.9,
                popup=f"🌑 DARK VESSEL<br>{vessel['name']}<br>Missing: {vessel['hours_since_seen']}h"
            ).add_to(m)
        
        # Add statistics overlay
        stats_html = f"""
        <div style='position: fixed; 
                    top: 10px; left: 50px; width: 200px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px'>
        <h4>🛰️ Arctic Surveillance</h4>
        <p>🚢 Vessels: {len(vessels)}</p>
        <p>🌑 Dark Vessels: {len(dark_vessels)}</p>
        <p>⚠️ Cable Alerts: {len(cable_alerts)}</p>
        <p>🕐 {datetime.now().strftime('%H:%M:%S')}</p>
        </div>
        """
        m.get_root().html.add_child(folium.Element(stats_html))
        
        # Save dashboard
        m.save(str(self.dashboard_file))
        logger.info(f"✅ Dashboard saved: {self.dashboard_file}")
        return str(self.dashboard_file)

# =============================================================================
# MAIN SURVEILLANCE SYSTEM
# =============================================================================

class ArcticSurveillanceSystem:
    """Main coordination class for Arctic surveillance"""
    
    def __init__(self):
        self.ais_collector = AISDataCollector(api_manager)
        self.dark_detector = DarkVesselDetector()
        self.cable_monitor = CableMonitor()
        self.dashboard_generator = DashboardGenerator()
        
        # Daily summary file
        self.daily_summary_file = config.INTELLIGENCE_DIR / f'daily_summary_{datetime.now().strftime("%Y%m%d")}.json'
    
    def run_surveillance_cycle(self):
        """Run complete surveillance cycle"""
        cycle_start = datetime.now()
        logger.info("="*70)
        logger.info("🛰️ ARCTIC SURVEILLANCE CYCLE STARTED")
        logger.info("="*70)
        
        try:
            # Step 1: Collect AIS data
            vessels = self.ais_collector.collect_ais_data()
            
            # Step 2: Update history and detect dark vessels
            history_df = self.dark_detector.update_history(vessels)
            dark_vessels = self.dark_detector.detect_dark_vessels(vessels, history_df)
            
            # Step 3: Monitor cable proximity
            cable_alerts = self.cable_monitor.check_cable_proximity(vessels)
            
            # Step 4: Generate dashboard
            dashboard_path = self.dashboard_generator.create_dashboard(vessels, dark_vessels, cable_alerts)
            
            # Step 5: Save summary
            summary = {
                'timestamp': cycle_start.isoformat(),
                'cycle_duration_seconds': (datetime.now() - cycle_start).total_seconds(),
                'statistics': {
                    'total_vessels': len(vessels),
                    'dark_vessels_detected': len(dark_vessels),
                    'cable_alerts': len(cable_alerts)
                },
                'dark_vessels': dark_vessels,
                'cable_alerts': cable_alerts[:10],  # Save top 10 alerts
                'dashboard_path': dashboard_path
            }
            
            # Save daily summary
            if self.daily_summary_file.exists():
                with open(self.daily_summary_file, 'r') as f:
                    daily_data = json.load(f)
            else:
                daily_data = {'date': datetime.now().strftime('%Y-%m-%d'), 'cycles': []}
            
            daily_data['cycles'].append(summary)
            
            with open(self.daily_summary_file, 'w') as f:
                json.dump(daily_data, f, indent=2)
            
            # Log summary
            logger.info("="*70)
            logger.info("📊 CYCLE SUMMARY")
            logger.info(f"🚢 Vessels tracked: {len(vessels)}")
            logger.info(f"🌑 Dark vessels: {len(dark_vessels)}")
            logger.info(f"⚠️ Cable alerts: {len(cable_alerts)}")
            logger.info(f"⏱️ Cycle time: {summary['cycle_duration_seconds']:.1f}s")
            logger.info(f"🗺️ Dashboard: {dashboard_path}")
            logger.info("="*70)
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Surveillance cycle failed: {e}")
            return None

# =============================================================================
# STREAMING SCHEDULER
# =============================================================================

def start_streaming_surveillance():
    """Start continuous surveillance with 30-minute intervals"""
    logger.info("🚀 Starting Arctic Shadow Tracker Streaming System")
    logger.info("⏰ Collection interval: 30 minutes")
    
    # Initialize surveillance system
    surveillance = ArcticSurveillanceSystem()
    
    # Run initial cycle
    logger.info("▶️ Running initial surveillance cycle...")
    surveillance.run_surveillance_cycle()
    
    # Schedule every 30 minutes
    schedule.every(30).minutes.do(surveillance.run_surveillance_cycle)
    
    logger.info("✅ Surveillance system started - running every 30 minutes")
    logger.info("💡 Dashboard updates at: data_stream/dashboard/arctic_surveillance_dashboard.html")
    logger.info("📊 CSV data saved to: data_stream/csv/")
    
    # Keep running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode - run single cycle
        logger.info("🧪 Running test cycle...")
        surveillance = ArcticSurveillanceSystem()
        result = surveillance.run_surveillance_cycle()
        if result:
            logger.info("✅ Test completed successfully")
        else:
            logger.error("❌ Test failed")
    else:
        # Production mode - start streaming
        try:
            start_streaming_surveillance()
        except KeyboardInterrupt:
            logger.info("\n🛑 Surveillance system stopped by user")
        except Exception as e:
            logger.error(f"❌ System error: {e}")