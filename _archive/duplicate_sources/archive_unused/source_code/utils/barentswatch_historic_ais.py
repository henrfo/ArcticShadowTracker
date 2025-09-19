#!/usr/bin/env python3
"""
BarentsWatch Historic AIS Collector
Uses the official Norwegian BarentsWatch historic AIS API for Arctic vessel tracking.
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import os

try:
    from .barentswatch_auth import BarentsWatchAuth
except ImportError:
    from barentswatch_auth import BarentsWatchAuth

logger = logging.getLogger(__name__)

class BarentsWatchHistoricAIS:
    """
    Collector for BarentsWatch historic AIS data.
    Uses the historic.ais.barentswatch.no endpoint for real vessel tracking.
    """
    
    def __init__(self):
        """Initialize with BarentsWatch historic AIS configuration."""
        self.auth = BarentsWatchAuth()
        # Note: Different base URL for historic AIS
        self.base_url = "https://historic.ais.barentswatch.no/v1"
        
        # Arctic MMSI ranges for Norwegian vessels
        self.norwegian_mmsi_ranges = [
            (257000000, 257999999),  # Norway
            (258000000, 258999999),  # Norway (alternate)
            (259000000, 259999999),  # Norway (alternate)
        ]
        
        # Test MMSIs for Arctic vessels
        self.test_mmsis = [
            257111020,  # Example from curl command
            258181000,  # Norwegian Coast Guard
            259513000,  # Research vessel
        ]
        
        logger.info("BarentsWatch Historic AIS collector initialized")
    
    def get_vessel_tracks_24h(self, mmsi: int) -> Optional[Dict]:
        """
        Get vessel tracks for the last 24 hours.
        
        Args:
            mmsi: Vessel MMSI number
            
        Returns:
            Vessel track data or None if not found
        """
        if not self.auth.authenticate():
            logger.error("Authentication failed")
            return None
            
        url = f"{self.base_url}/historic/trackslast24hours/{mmsi}"
        headers = self.auth.get_auth_headers()
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Retrieved track data for MMSI {mmsi}")
                return data
            elif response.status_code == 404:
                logger.debug(f"No data for MMSI {mmsi}")
                return None
            else:
                logger.warning(f"API error for MMSI {mmsi}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get tracks for {mmsi}: {e}")
            return None
    
    def get_latest_positions(self) -> List[Dict]:
        """
        Get latest positions from available Arctic vessels.
        
        Returns:
            List of vessel positions
        """
        if not self.auth.authenticate():
            logger.error("Authentication failed")
            return []
            
        url = f"{self.base_url}/historic/latest"
        headers = self.auth.get_auth_headers()
        
        try:
            # Try to get latest positions endpoint
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                vessels = []
                
                # Parse response based on actual structure
                if isinstance(data, list):
                    vessels = data
                elif isinstance(data, dict) and 'vessels' in data:
                    vessels = data['vessels']
                elif isinstance(data, dict) and 'features' in data:
                    # GeoJSON format
                    for feature in data['features']:
                        props = feature.get('properties', {})
                        coords = feature.get('geometry', {}).get('coordinates', [0, 0])
                        vessel = {
                            'mmsi': props.get('mmsi'),
                            'name': props.get('name', 'Unknown'),
                            'latitude': coords[1],
                            'longitude': coords[0],
                            'speed': props.get('speed', 0),
                            'course': props.get('course', 0),
                            'timestamp': props.get('timestamp', datetime.now().isoformat()),
                            'type': props.get('shipType', 'Unknown'),
                            'source': 'barentswatch_historic'
                        }
                        vessels.append(vessel)
                
                logger.info(f"Retrieved {len(vessels)} latest positions")
                return vessels
                
            else:
                logger.warning(f"Latest positions endpoint returned: {response.status_code}")
                # Fall back to scanning known vessels
                return self.scan_known_vessels()
                
        except Exception as e:
            logger.error(f"Failed to get latest positions: {e}")
            return self.scan_known_vessels()
    
    def scan_known_vessels(self) -> List[Dict]:
        """
        Scan known Arctic vessel MMSIs for recent positions.
        
        Returns:
            List of vessel positions found
        """
        vessels = []
        
        for mmsi in self.test_mmsis:
            track_data = self.get_vessel_tracks_24h(mmsi)
            if track_data:
                # Extract latest position from track data
                latest = self.extract_latest_position(track_data, mmsi)
                if latest:
                    vessels.append(latest)
            
            # Rate limiting
            time.sleep(0.5)
        
        logger.info(f"Found {len(vessels)} vessels from known MMSIs")
        return vessels
    
    def extract_latest_position(self, track_data, mmsi: int) -> Optional[Dict]:
        """
        Extract latest position from track data.
        
        Args:
            track_data: Raw track data from API (list of positions)
            mmsi: Vessel MMSI
            
        Returns:
            Latest position as standardized dict
        """
        try:
            # Track data is a list of positions
            if isinstance(track_data, list) and track_data:
                latest_point = track_data[-1]  # Last point is most recent
                
                vessel = {
                    'mmsi': str(mmsi),
                    'name': latest_point.get('name', 'Unknown'),
                    'latitude': latest_point.get('latitude', 0),
                    'longitude': latest_point.get('longitude', 0),
                    'speed': latest_point.get('speedOverGround', 0),
                    'course': latest_point.get('courseOverGround', 0),
                    'timestamp': latest_point.get('msgtime', datetime.now().isoformat()),
                    'type': self._get_ship_type_name(latest_point.get('shipType', 0)),
                    'heading': latest_point.get('trueHeading', 0),
                    'nav_status': latest_point.get('navigationalStatus', 0),
                    'source': 'barentswatch_historic',
                    'data_quality': 'official'
                }
                
                return vessel
                
        except Exception as e:
            logger.error(f"Failed to extract position for MMSI {mmsi}: {e}")
            
        return None
    
    def _get_ship_type_name(self, type_code: int) -> str:
        """Convert AIS ship type code to readable name."""
        ship_types = {
            0: 'Unknown',
            30: 'Fishing',
            31: 'Towing',
            32: 'Towing',
            33: 'Dredging',
            34: 'Diving',
            35: 'Military',
            36: 'Sailing',
            37: 'Pleasure',
            50: 'Pilot',
            51: 'Search/Rescue',
            52: 'Tug',
            53: 'Port Tender',
            54: 'Pollution Control',
            55: 'Law Enforcement',
            60: 'Passenger',
            70: 'Cargo',
            80: 'Tanker',
            90: 'Other'
        }
        return ship_types.get(type_code, f'Type-{type_code}')
    
    def collect_arctic_vessels(self) -> List[Dict]:
        """
        Main collection method for Arctic vessels.
        
        Returns:
            List of vessels in Arctic waters
        """
        logger.info("Collecting BarentsWatch historic AIS data...")
        
        # Try latest positions first
        vessels = self.get_latest_positions()
        
        if not vessels:
            # Fall back to scanning known vessels
            vessels = self.scan_known_vessels()
        
        # Filter for Arctic region (above 66°N)
        arctic_vessels = []
        for vessel in vessels:
            if vessel.get('latitude', 0) > 66:
                arctic_vessels.append(vessel)
        
        logger.info(f"Collected {len(arctic_vessels)} Arctic vessels from BarentsWatch")
        return arctic_vessels


# Test functionality
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    collector = BarentsWatchHistoricAIS()
    
    print("🇳🇴 Testing BarentsWatch Historic AIS API")
    print("=" * 60)
    
    # Test authentication
    if collector.auth.authenticate():
        print("✅ Authentication successful")
        
        # Test specific vessel
        test_mmsi = 257111020
        print(f"\n🚢 Testing vessel MMSI {test_mmsi}...")
        track_data = collector.get_vessel_tracks_24h(test_mmsi)
        
        if track_data:
            print(f"✅ Found track data for MMSI {test_mmsi}")
            latest = collector.extract_latest_position(track_data, test_mmsi)
            if latest:
                print(f"   Name: {latest['name']}")
                print(f"   Position: {latest['latitude']:.4f}°N, {latest['longitude']:.4f}°E")
                print(f"   Speed: {latest['speed']:.1f} knots")
        else:
            print(f"❌ No data for MMSI {test_mmsi}")
        
        # Test collection
        print("\n📊 Testing Arctic vessel collection...")
        vessels = collector.collect_arctic_vessels()
        print(f"Found {len(vessels)} Arctic vessels")
        
        for vessel in vessels[:5]:
            print(f"  • {vessel['name']} (MMSI: {vessel['mmsi']})")
            print(f"    📍 {vessel['latitude']:.4f}°N, {vessel['longitude']:.4f}°E")
    else:
        print("❌ Authentication failed - check credentials")