#!/usr/bin/env python3
"""
BarentsWatch Streaming AIS Collector
Converts from one-time fetch to continuous 24/7 streaming data collection.
"""

import requests
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Generator
from pathlib import Path

logger = logging.getLogger(__name__)

class BarentsWatchStreamCollector:
    """Stream AIS data 24/7 from BarentsWatch Live API."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.stream_url = "https://live.ais.barentswatch.no/v1/combined"
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Arctic filter for Norwegian waters
        self.arctic_filter = {
            "shipTypes": [30, 70, 80],  # Fishing, Cargo, Tankers
            "Downsample": False,
            "modelType": "Full",
            "modelFormat": "Geojson"
        }
        
        # Storage
        self.data_dir = Path('data/stream')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("BarentsWatch stream collector initialized")
    
    def stream_arctic_vessels(self) -> Generator[Dict, None, None]:
        """
        Stream Arctic vessels 24/7. 
        Yields vessel data as it arrives from the API.
        """
        logger.info("🌊 Starting 24/7 Arctic vessel stream...")
        
        while True:
            try:
                # Create streaming request
                response = requests.post(
                    self.stream_url,
                    headers=self.headers,
                    json=self.arctic_filter,
                    stream=True,
                    timeout=None  # No timeout - stream forever
                )
                
                if response.status_code == 200:
                    logger.info("✅ Connected to BarentsWatch stream")
                    
                    # Process streaming response
                    for line in response.iter_lines():
                        if line:
                            try:
                                # Parse JSON vessel data
                                vessel_data = json.loads(line.decode('utf-8'))
                                
                                # Normalize to our format
                                normalized = self._normalize_stream_vessel(vessel_data)
                                if normalized:
                                    yield normalized
                                    
                            except json.JSONDecodeError:
                                # Skip malformed lines
                                continue
                                
                else:
                    logger.error(f"Stream connection failed: {response.status_code}")
                    logger.info("Retrying in 30 seconds...")
                    time.sleep(30)
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Stream error: {e}")
                logger.info("Reconnecting in 30 seconds...")
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("Stream stopped by user")
                break
                
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(30)
    
    def _normalize_stream_vessel(self, vessel_data: Dict) -> Optional[Dict]:
        """Normalize streaming vessel data to standard format."""
        try:
            # Handle GeoJSON format
            if vessel_data.get('type') == 'Feature':
                geometry = vessel_data.get('geometry', {})
                properties = vessel_data.get('properties', {})
                
                coords = geometry.get('coordinates', [])
                if len(coords) < 2:
                    return None
                
                return {
                    'mmsi': str(properties.get('mmsi', '')),
                    'name': properties.get('name', f"VESSEL_{properties.get('mmsi', 'UNKNOWN')}"),
                    'latitude': float(coords[1]),
                    'longitude': float(coords[0]),
                    'speed': float(properties.get('speedOverGround', 0)),
                    'course': float(properties.get('courseOverGround', 0)),
                    'type': properties.get('shipType', 'Unknown'),
                    'timestamp': properties.get('msgtime', datetime.now().isoformat()),
                    'source': 'barentswatch_stream',
                    'status': properties.get('navigationalStatus', 'Unknown')
                }
            
            # Handle direct JSON format
            else:
                if not all(k in vessel_data for k in ['mmsi', 'latitude', 'longitude']):
                    return None
                
                return {
                    'mmsi': str(vessel_data.get('mmsi', '')),
                    'name': vessel_data.get('name', f"VESSEL_{vessel_data.get('mmsi', 'UNKNOWN')}"),
                    'latitude': float(vessel_data['latitude']),
                    'longitude': float(vessel_data['longitude']),
                    'speed': float(vessel_data.get('speedOverGround', 0)),
                    'course': float(vessel_data.get('courseOverGround', 0)),
                    'type': vessel_data.get('shipType', 'Unknown'),
                    'timestamp': vessel_data.get('msgtime', datetime.now().isoformat()),
                    'source': 'barentswatch_stream'
                }
                
        except Exception as e:
            logger.warning(f"Failed to normalize vessel: {e}")
            return None
    
    def run_continuous_collection(self, save_interval: int = 300):
        """
        Run 24/7 collection, saving data every X seconds.
        
        Args:
            save_interval: Save accumulated data every X seconds (default: 5 minutes)
        """
        logger.info(f"🚀 Starting 24/7 collection (saving every {save_interval}s)")
        
        vessel_buffer = []
        last_save = time.time()
        
        for vessel in self.stream_arctic_vessels():
            vessel_buffer.append(vessel)
            
            # Save every N seconds
            if time.time() - last_save >= save_interval:
                if vessel_buffer:
                    self._save_batch(vessel_buffer)
                    logger.info(f"💾 Saved {len(vessel_buffer)} vessels")
                    vessel_buffer = []
                    last_save = time.time()
    
    def _save_batch(self, vessels: List[Dict]):
        """Save batch of vessels with timestamp."""
        if not vessels:
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"stream_batch_{timestamp}.json"
        filepath = self.data_dir / filename
        
        data = {
            'collection_time': datetime.now().isoformat(),
            'source': 'barentswatch_stream',
            'vessel_count': len(vessels),
            'vessels': vessels
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Also save as latest
        latest_file = self.data_dir / 'latest_stream.json'
        with open(latest_file, 'w') as f:
            json.dump(data, f, indent=2)

# Simple usage example
def start_24x7_collection():
    """Start 24/7 streaming collection."""
    
    # Get your access token
    access_token = "YOUR_ACCESS_TOKEN_HERE"  # Replace with actual token
    
    # Create collector
    collector = BarentsWatchStreamCollector(access_token)
    
    # Start continuous collection
    collector.run_continuous_collection(save_interval=300)  # Save every 5 minutes

if __name__ == "__main__":
    start_24x7_collection()