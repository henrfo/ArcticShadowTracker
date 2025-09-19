#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Free AIS Data Collector
Uses completely FREE AIS data sources for Arctic maritime surveillance.
"""

import asyncio
import websockets
import json
import socket
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, AsyncGenerator
from pathlib import Path
import time

logger = logging.getLogger(__name__)

class FreeArcticAISCollector:
    """
    Free AIS data collector using completely free sources.
    Perfect for Arctic surveillance without monthly costs.
    """
    
    def __init__(self):
        """Initialize with free AIS data sources."""
        
        # Arctic regions for focused surveillance
        self.arctic_regions = {
            'svalbard': {
                'bbox': [[10, 76], [35, 81]],
                'name': 'Svalbard/Spitsbergen'
            },
            'barents_sea': {
                'bbox': [[15, 70], [60, 82]], 
                'name': 'Barents Sea'
            },
            'kola_waters': {
                'bbox': [[28, 66], [42, 70]],
                'name': 'Kola Peninsula Waters'
            },
            'franz_josef': {
                'bbox': [[44, 79], [62, 82]],
                'name': 'Franz Josef Land'
            }
        }
        
        # Free AIS sources
        self.free_sources = {
            'aisstream': {
                'url': 'wss://stream.aisstream.io/v0/stream',
                'type': 'websocket',
                'free_tier': True,
                'arctic_coverage': 'excellent',
                'registration_url': 'https://aisstream.io/'
            },
            'norwegian_coastal': {
                'url': 'ais1.kystverket.no',
                'port': 4001,
                'type': 'tcp',
                'free_tier': True, 
                'arctic_coverage': 'svalbard+barents',
                'registration_url': 'https://kystdatahuset.no/'
            },
            'aishub_free': {
                'url': 'http://data.aishub.net/ws.php',
                'type': 'http',
                'free_tier': True,
                'arctic_coverage': 'limited',
                'registration_url': 'https://www.aishub.net/'
            }
        }
        
        # Data storage
        self.data_dir = Path('data/operational/daily')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("FreeArcticAISCollector initialized")
    
    async def collect_aisstream_data(self, region: str = 'svalbard', duration_minutes: int = 5) -> List[Dict]:
        """
        Collect free AIS data from aisstream.io WebSocket.
        
        Args:
            region: Arctic region to monitor
            duration_minutes: How long to collect data
            
        Returns:
            List of vessel positions collected
        """
        logger.info(f"Collecting FREE AIS data from aisstream.io for {region}")
        
        # Check for API key (free registration)
        api_key = self._get_aisstream_key()
        if not api_key:
            logger.warning("No aisstream.io API key found")
            return []
        
        vessels_collected = []
        
        try:
            # Connect to free WebSocket stream
            async with websockets.connect(self.free_sources['aisstream']['url']) as websocket:
                
                # Subscribe to Arctic region
                bbox = self.arctic_regions.get(region, {}).get('bbox', [[10, 76], [35, 81]])
                
                subscribe_message = {
                    "APIKey": api_key,
                    "BoundingBoxes": [bbox],
                    "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
                }
                
                await websocket.send(json.dumps(subscribe_message))
                logger.info(f"Subscribed to {region} region: {bbox}")
                
                # Collect data for specified duration
                start_time = datetime.now()
                end_time = start_time + timedelta(minutes=duration_minutes)
                
                while datetime.now() < end_time:
                    try:
                        # Set timeout to avoid hanging
                        message_json = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        message = json.loads(message_json)
                        
                        if 'Message' in message:
                            vessel_data = self._normalize_aisstream_vessel(message)
                            if vessel_data:
                                vessels_collected.append(vessel_data)
                                
                                if len(vessels_collected) % 10 == 0:
                                    logger.info(f"Collected {len(vessels_collected)} vessels so far...")
                    
                    except asyncio.TimeoutError:
                        logger.warning("WebSocket timeout - continuing...")
                        continue
                    except Exception as e:
                        logger.error(f"Error receiving message: {e}")
                        break
                
                logger.info(f"Completed aisstream.io collection: {len(vessels_collected)} vessels")
                return vessels_collected
                
        except Exception as e:
            logger.error(f"aisstream.io connection failed: {e}")
            return []
    
    def collect_norwegian_coastal_data(self) -> List[Dict]:
        """
        Collect free AIS data from Norwegian Coastal Administration.
        Covers Svalbard and Norwegian Arctic waters.
        """
        logger.info("Collecting FREE AIS data from Norwegian Coastal Administration")
        
        vessels_collected = []
        
        try:
            # Try different Norwegian AIS endpoints
            endpoints = [
                {
                    'url': 'https://www.kystverket.no/globalassets/ais-data/ais_current.json',
                    'type': 'http'
                },
                {
                    'url': 'https://ais.kystverket.no/api/v1/ais/current',
                    'type': 'http'
                },
                {
                    'host': 'ais1.kystverket.no',
                    'port': 4001,
                    'type': 'tcp'
                }
            ]
            
            for endpoint in endpoints:
                try:
                    if endpoint['type'] == 'http':
                        vessels = self._collect_norwegian_http(endpoint['url'])
                        if vessels:
                            vessels_collected.extend(vessels)
                            logger.info(f"Norwegian HTTP: collected {len(vessels)} vessels")
                            break
                    
                    elif endpoint['type'] == 'tcp':
                        vessels = self._collect_norwegian_tcp(endpoint['host'], endpoint['port'])
                        if vessels:
                            vessels_collected.extend(vessels)
                            logger.info(f"Norwegian TCP: collected {len(vessels)} vessels")
                            break
                
                except Exception as e:
                    logger.debug(f"Norwegian endpoint {endpoint} failed: {e}")
                    continue
            
            # Filter for Arctic region
            arctic_vessels = self._filter_for_arctic(vessels_collected)
            logger.info(f"Norwegian Coastal: {len(arctic_vessels)} Arctic vessels")
            
            return arctic_vessels
            
        except Exception as e:
            logger.error(f"Norwegian Coastal collection failed: {e}")
            return []
    
    def collect_aishub_free_data(self) -> List[Dict]:
        """
        Collect from AISHub free tier (limited but still useful).
        """
        logger.info("Collecting from AISHub free tier")
        
        try:
            # Try free access without credentials first
            url = self.free_sources['aishub_free']['url']
            
            params = {
                'format': '1',
                'output': 'json',
                'compress': '0',
                'latmin': '69',
                'latmax': '82', 
                'lonmin': '5',
                'lonmax': '35'
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    if isinstance(data, list) and len(data) > 0:
                        # Check for error messages
                        if data[0].get('ERROR'):
                            logger.warning(f"AISHub free tier: {data[0].get('ERROR_MESSAGE', 'Unknown error')}")
                            return []
                        
                        vessels = []
                        for vessel_data in data:
                            vessel = self._normalize_aishub_vessel(vessel_data)
                            if vessel:
                                vessels.append(vessel)
                        
                        logger.info(f"AISHub free: collected {len(vessels)} vessels")
                        return vessels
                
                except json.JSONDecodeError:
                    logger.warning("AISHub free: Invalid JSON response")
                    return []
            
            return []
            
        except Exception as e:
            logger.error(f"AISHub free collection failed: {e}")
            return []
    
    def collect_all_free_sources(self, duration_minutes: int = 3) -> List[Dict]:
        """
        Collect from all available free sources.
        
        Args:
            duration_minutes: How long to collect streaming data
            
        Returns:
            Combined list of vessels from all sources
        """
        logger.info("Collecting from ALL free AIS sources")
        
        all_vessels = []
        
        # 1. Try aisstream.io (real-time streaming)
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an event loop, create a task
                task = loop.create_task(
                    self.collect_aisstream_data('svalbard', duration_minutes)
                )
                aisstream_vessels = []  # Skip for now to avoid blocking
                logger.info("aisstream.io: Skipped (async context)")
            except RuntimeError:
                # No event loop, safe to use asyncio.run
                aisstream_vessels = asyncio.run(
                    self.collect_aisstream_data('svalbard', duration_minutes)
                )
                if aisstream_vessels:
                    all_vessels.extend(aisstream_vessels)
                    logger.info(f"aisstream.io: {len(aisstream_vessels)} vessels")
        except Exception as e:
            logger.error(f"aisstream.io failed: {e}")
        
        # 2. Try Norwegian Coastal
        try:
            norwegian_vessels = self.collect_norwegian_coastal_data()
            if norwegian_vessels:
                all_vessels.extend(norwegian_vessels)
                logger.info(f"Norwegian Coastal: {len(norwegian_vessels)} vessels")
        except Exception as e:
            logger.error(f"Norwegian Coastal failed: {e}")
        
        # 3. Try AISHub free tier
        try:
            aishub_vessels = self.collect_aishub_free_data()
            if aishub_vessels:
                all_vessels.extend(aishub_vessels)
                logger.info(f"AISHub free: {len(aishub_vessels)} vessels")
        except Exception as e:
            logger.error(f"AISHub free failed: {e}")
        
        # Remove duplicates
        unique_vessels = self._deduplicate_vessels(all_vessels)
        
        logger.info(f"FREE AIS COLLECTION COMPLETE: {len(unique_vessels)} unique vessels")
        return unique_vessels
    
    def _get_aisstream_key(self) -> Optional[str]:
        """Get aisstream.io API key from environment or config."""
        import os
        
        # Try environment variable
        api_key = os.getenv('AISSTREAM_API_KEY')
        if api_key:
            return api_key
        
        # Try config file
        config_file = Path('config/aisstream_config.json')
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                return config.get('api_key')
            except:
                pass
        
        # Instructions for getting free key
        logger.info("🔑 To get FREE aisstream.io API key:")
        logger.info("1. Visit: https://aisstream.io/")
        logger.info("2. Register for free account")
        logger.info("3. Set: export AISSTREAM_API_KEY='your_free_key'")
        
        return None
    
    def _normalize_aisstream_vessel(self, message_data: Dict) -> Optional[Dict]:
        """Normalize aisstream.io vessel data."""
        try:
            # Extract MMSI from MetaData
            metadata = message_data.get('MetaData', {})
            mmsi = str(metadata.get('MMSI', 'unknown'))
            
            # Extract position data from Message
            message = message_data.get('Message', {})
            
            # Handle PositionReport
            if 'PositionReport' in message:
                pos_report = message['PositionReport']
                
                vessel = {
                    'mmsi': mmsi,
                    'latitude': float(pos_report.get('Latitude', 0)),
                    'longitude': float(pos_report.get('Longitude', 0)),
                    'speed': float(pos_report.get('Sog', 0)),  # Speed over ground
                    'course': float(pos_report.get('Cog', 0)),  # Course over ground
                    'timestamp': datetime.now().isoformat(),
                    'name': f"VESSEL_{mmsi}",
                    'type': 'Unknown',
                    'source': 'aisstream_free',
                    'data_quality': 'real_free',
                    'nav_status': pos_report.get('NavigationalStatus', 'Unknown')
                }
                
                # Validate coordinates
                if vessel['latitude'] == 0 and vessel['longitude'] == 0:
                    return None
                
                return vessel
            
            # Handle ShipStaticData (contains ship name and type)
            elif 'ShipStaticData' in message:
                static_data = message['ShipStaticData']
                
                vessel = {
                    'mmsi': mmsi,
                    'latitude': 0,  # Static data doesn't have position
                    'longitude': 0,
                    'speed': 0,
                    'course': 0,
                    'timestamp': datetime.now().isoformat(),
                    'name': static_data.get('ShipName', f"VESSEL_{mmsi}").strip(),
                    'type': static_data.get('ShipType', 'Unknown'),
                    'source': 'aisstream_free',
                    'data_quality': 'real_free',
                    'dimensions': {
                        'length': static_data.get('DimToBow', 0) + static_data.get('DimToStern', 0),
                        'width': static_data.get('DimToPort', 0) + static_data.get('DimToStarboard', 0)
                    }
                }
                
                # Don't return static data without position for now
                return None
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to normalize aisstream vessel: {e}")
            return None
    
    def _collect_norwegian_http(self, url: str) -> List[Dict]:
        """Collect from Norwegian HTTP endpoints."""
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            vessels = []
            
            # Process Norwegian data format
            if isinstance(data, list):
                for item in data:
                    vessel = self._normalize_norwegian_vessel(item)
                    if vessel:
                        vessels.append(vessel)
            
            return vessels
            
        except Exception as e:
            logger.debug(f"Norwegian HTTP {url} failed: {e}")
            return []
    
    def _collect_norwegian_tcp(self, host: str, port: int) -> List[Dict]:
        """Collect from Norwegian TCP stream."""
        vessels = []
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((host, port))
            
            # Collect for a few seconds
            start_time = time.time()
            while time.time() - start_time < 5:
                try:
                    data = sock.recv(1024)
                    if data:
                        ais_sentence = data.decode('utf-8', errors='ignore')
                        # Parse NMEA AIS sentences here
                        # This would require AIS message parsing
                        logger.debug(f"Norwegian AIS: {ais_sentence[:50]}...")
                except:
                    break
            
            sock.close()
            return vessels
            
        except Exception as e:
            logger.debug(f"Norwegian TCP failed: {e}")
            return []
    
    def _normalize_norwegian_vessel(self, vessel_data: Dict) -> Optional[Dict]:
        """Normalize Norwegian Coastal data."""
        try:
            vessel = {
                'mmsi': str(vessel_data.get('mmsi', 'unknown')),
                'latitude': float(vessel_data.get('lat', 0)),
                'longitude': float(vessel_data.get('lon', 0)),
                'speed': float(vessel_data.get('speed', 0)),
                'course': float(vessel_data.get('course', 0)),
                'timestamp': datetime.now().isoformat(),
                'name': vessel_data.get('name', f"VESSEL_{vessel_data.get('mmsi', 'UNK')}"),
                'type': vessel_data.get('type', 'Unknown'),
                'source': 'norwegian_coastal_free',
                'data_quality': 'real_free'
            }
            
            return vessel if vessel['latitude'] != 0 and vessel['longitude'] != 0 else None
            
        except Exception as e:
            logger.warning(f"Failed to normalize Norwegian vessel: {e}")
            return None
    
    def _normalize_aishub_vessel(self, vessel_data: Dict) -> Optional[Dict]:
        """Normalize AISHub free tier data."""
        try:
            vessel = {
                'mmsi': str(vessel_data.get('MMSI', 'unknown')),
                'latitude': float(vessel_data.get('LATITUDE', 0)),
                'longitude': float(vessel_data.get('LONGITUDE', 0)),
                'speed': float(vessel_data.get('SOG', 0)),
                'course': float(vessel_data.get('COG', 0)),
                'timestamp': datetime.now().isoformat(),
                'name': vessel_data.get('SHIPNAME', f"VESSEL_{vessel_data.get('MMSI', 'UNK')}"),
                'type': vessel_data.get('SHIP_TYPE', 'Unknown'),
                'source': 'aishub_free',
                'data_quality': 'real_free'
            }
            
            return vessel if vessel['latitude'] != 0 and vessel['longitude'] != 0 else None
            
        except Exception as e:
            logger.warning(f"Failed to normalize AISHub vessel: {e}")
            return None
    
    def _filter_for_arctic(self, vessels: List[Dict]) -> List[Dict]:
        """Filter vessels for Arctic region."""
        arctic_vessels = []
        
        # Combined Arctic bounds
        arctic_bounds = {
            'south': 66.0,  # Arctic Circle
            'north': 85.0,  # North Pole
            'west': -10.0,  # Greenland Sea
            'east': 70.0    # Laptev Sea
        }
        
        for vessel in vessels:
            try:
                lat = float(vessel['latitude'])
                lon = float(vessel['longitude'])
                
                if (arctic_bounds['south'] <= lat <= arctic_bounds['north'] and
                    arctic_bounds['west'] <= lon <= arctic_bounds['east']):
                    arctic_vessels.append(vessel)
            except:
                continue
        
        return arctic_vessels
    
    def _deduplicate_vessels(self, vessels: List[Dict]) -> List[Dict]:
        """Remove duplicate vessels based on MMSI."""
        seen_mmsi = set()
        unique_vessels = []
        
        for vessel in vessels:
            mmsi = vessel.get('mmsi', 'unknown')
            if mmsi not in seen_mmsi:
                seen_mmsi.add(mmsi)
                unique_vessels.append(vessel)
        
        return unique_vessels
    
    def save_free_data(self, vessels: List[Dict]) -> str:
        """Save free AIS data with timestamp."""
        if not vessels:
            return ""
        
        # Create today's directory
        today = datetime.now().strftime('%Y-%m-%d')
        today_dir = self.data_dir / today
        today_dir.mkdir(exist_ok=True)
        
        # Save with timestamp
        timestamp = datetime.now().strftime('%H%M%S')
        filename = f"free_ais_data_{timestamp}.json"
        file_path = today_dir / filename
        
        # Save data
        with open(file_path, 'w') as f:
            json.dump(vessels, f, indent=2)
        
        # Also save as latest
        latest_file = today_dir / "latest_free_ais.json"
        with open(latest_file, 'w') as f:
            json.dump(vessels, f, indent=2)
        
        logger.info(f"Saved {len(vessels)} FREE vessels to {file_path}")
        return str(file_path)
    
    def load_demo_data(self) -> List[Dict]:
        """Load demo free AIS data for testing."""
        demo_file = self.data_dir / datetime.now().strftime('%Y-%m-%d') / 'demo_free_ais_data.json'
        
        if demo_file.exists():
            try:
                with open(demo_file, 'r') as f:
                    demo_data = json.load(f)
                logger.info(f"Loaded {len(demo_data)} demo vessels")
                return demo_data
            except Exception as e:
                logger.error(f"Failed to load demo data: {e}")
        
        return []
    
    def validate_data_quality(self, vessels: List[Dict]) -> Dict[str, float]:
        """Simple data quality validation for free sources."""
        if not vessels:
            return {'completeness': 0.0, 'accuracy': 0.0, 'score': 0.0}
        
        total_vessels = len(vessels)
        valid_coords = 0
        valid_mmsi = 0
        
        for vessel in vessels:
            # Check coordinates
            lat = vessel.get('latitude', 0)
            lon = vessel.get('longitude', 0)
            if -90 <= lat <= 90 and -180 <= lon <= 180 and lat != 0 and lon != 0:
                valid_coords += 1
            
            # Check MMSI
            mmsi = vessel.get('mmsi', '')
            if mmsi and mmsi != 'unknown' and len(mmsi) >= 6:
                valid_mmsi += 1
        
        accuracy = valid_coords / total_vessels
        completeness = valid_mmsi / total_vessels
        overall_score = (accuracy + completeness) / 2
        
        return {
            'completeness': completeness,
            'accuracy': accuracy,
            'score': overall_score,
            'total_vessels': total_vessels
        }

# Test function
async def test_free_ais_collection():
    """Test all free AIS sources."""
    print("🌊 Testing FREE Arctic AIS Data Collection")
    print("=" * 50)
    
    collector = FreeArcticAISCollector()
    
    # Test all free sources
    vessels = collector.collect_all_free_sources(duration_minutes=2)
    
    if vessels:
        print(f"\n✅ SUCCESS: Collected {len(vessels)} FREE vessels!")
        print("\n🚢 Sample vessels:")
        for vessel in vessels[:5]:
            print(f"   • {vessel['name']} (MMSI: {vessel['mmsi']})")
            print(f"     Position: {vessel['latitude']:.2f}°N, {vessel['longitude']:.2f}°E")
            print(f"     Source: {vessel['source']}")
        
        # Save the data
        saved_file = collector.save_free_data(vessels)
        print(f"\n💾 Data saved to: {saved_file}")
        
    else:
        print("\n❌ No free AIS data collected")
        print("\n💡 Setup instructions:")
        print("1. Register free at: https://aisstream.io/")
        print("2. Set API key: export AISSTREAM_API_KEY='your_free_key'")
        print("3. Re-run this test")

if __name__ == "__main__":
    asyncio.run(test_free_ais_collection())