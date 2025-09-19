#!/usr/bin/env python3
"""
BarentsWatch Official Norwegian Arctic AIS Collector
Collects real AIS data from official Norwegian government sources.
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .barentswatch_auth import BarentsWatchAuth

logger = logging.getLogger(__name__)

class BarentsWatchCollector:
    """
    Official BarentsWatch AIS data collector for Norwegian Arctic waters.
    Provides legitimate access to government AIS data with proper authentication.
    """
    
    def __init__(self):
        """Initialize BarentsWatch collector."""
        self.auth = BarentsWatchAuth()
        self.base_url = "https://www.barentswatch.no/bwapi/v1/"
        
        # Norwegian Arctic regions with precise bounding boxes
        self.norwegian_arctic_regions = {
            'svalbard_core': {
                'bbox': [10.0, 76.0, 35.0, 81.0],  # Main Svalbard archipelago
                'name': 'Svalbard Core Waters',
                'priority': 'high',
                'description': 'Primary Svalbard surveillance zone'
            },
            'svalbard_extended': {
                'bbox': [5.0, 74.0, 40.0, 82.0],  # Extended Svalbard waters
                'name': 'Extended Svalbard Waters',
                'priority': 'high',
                'description': 'Extended Svalbard monitoring area'
            },
            'barents_sea_west': {
                'bbox': [15.0, 70.0, 40.0, 78.0],  # Western Barents Sea
                'name': 'Western Barents Sea',
                'priority': 'high',
                'description': 'Norwegian sector of Barents Sea'
            },
            'barents_sea_central': {
                'bbox': [35.0, 70.0, 60.0, 80.0],  # Central Barents Sea
                'name': 'Central Barents Sea',
                'priority': 'medium',
                'description': 'Central Barents Sea monitoring'
            },
            'norwegian_sea_north': {
                'bbox': [0.0, 66.0, 20.0, 72.0],  # Northern Norwegian Sea
                'name': 'Northern Norwegian Sea',
                'priority': 'medium',
                'description': 'Northern approaches to Norwegian waters'
            },
            'jan_mayen': {
                'bbox': [-10.0, 70.0, -7.0, 72.0],  # Jan Mayen area
                'name': 'Jan Mayen Waters',
                'priority': 'low',
                'description': 'Jan Mayen island waters'
            }
        }
        
        # Data storage
        self.data_dir = Path('data/operational/daily')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("BarentsWatch collector initialized")
    
    def collect_region_data(self, region: str, limit: int = 1000) -> List[Dict]:
        """
        Collect AIS data for a specific Norwegian Arctic region.
        
        Args:
            region: Region name from norwegian_arctic_regions
            limit: Maximum number of vessels to collect
            
        Returns:
            List of normalized vessel data
        """
        if region not in self.norwegian_arctic_regions:
            logger.error(f"Unknown region: {region}")
            return []
        
        region_info = self.norwegian_arctic_regions[region]
        logger.info(f"Collecting BarentsWatch data for {region_info['name']}")
        
        try:
            # Authenticate if needed
            if not self.auth.authenticate():
                logger.error("BarentsWatch authentication failed")
                return []
            
            # Prepare API request
            url = f"{self.base_url}geodata/ais"
            headers = self.auth.get_auth_headers()
            
            # Format bounding box for API (west,south,east,north)
            bbox = region_info['bbox']
            bbox_str = f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}"
            
            params = {
                'bbox': bbox_str,
                'limit': limit,
                'format': 'geojson'
            }
            
            logger.info(f"Requesting AIS data for bbox: {bbox_str}")
            
            # Make API request
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                vessels = self._process_barentswatch_response(data, region)
                logger.info(f"BarentsWatch {region}: collected {len(vessels)} vessels")
                return vessels
            
            elif response.status_code == 401:
                logger.error("BarentsWatch authentication expired, retrying...")
                # Force re-authentication
                self.auth.access_token = None
                if self.auth.authenticate():
                    # Retry request once
                    headers = self.auth.get_auth_headers()
                    response = requests.get(url, headers=headers, params=params, timeout=60)
                    if response.status_code == 200:
                        data = response.json()
                        vessels = self._process_barentswatch_response(data, region)
                        logger.info(f"BarentsWatch {region} (retry): collected {len(vessels)} vessels")
                        return vessels
                
                logger.error("BarentsWatch re-authentication failed")
                return []
            
            else:
                logger.error(f"BarentsWatch API error: {response.status_code} {response.text}")
                return []
        
        except Exception as e:
            logger.error(f"BarentsWatch collection failed for {region}: {e}")
            return []
    
    def collect_all_norwegian_arctic(self, priority_filter: str = 'all') -> List[Dict]:
        """
        Collect AIS data from all Norwegian Arctic regions.
        
        Args:
            priority_filter: 'high', 'medium', 'low', or 'all'
            
        Returns:
            Combined list of vessels from all regions
        """
        logger.info(f"Collecting BarentsWatch data for all Norwegian Arctic regions (priority: {priority_filter})")
        
        all_vessels = []
        regions_processed = 0
        
        for region_name, region_info in self.norwegian_arctic_regions.items():
            # Filter by priority
            if priority_filter != 'all' and region_info['priority'] != priority_filter:
                continue
            
            try:
                vessels = self.collect_region_data(region_name, limit=500)
                if vessels:
                    all_vessels.extend(vessels)
                    regions_processed += 1
                    logger.info(f"Region {region_name}: {len(vessels)} vessels")
                else:
                    logger.warning(f"No data collected from {region_name}")
                
                # Small delay between regions to be respectful
                import time
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to collect from {region_name}: {e}")
                continue
        
        # Deduplicate vessels by MMSI
        unique_vessels = self._deduplicate_by_mmsi(all_vessels)
        
        logger.info(f"BarentsWatch collection complete:")
        logger.info(f"  Regions processed: {regions_processed}")
        logger.info(f"  Total vessels: {len(all_vessels)}")
        logger.info(f"  Unique vessels: {len(unique_vessels)}")
        
        return unique_vessels
    
    def collect_priority_areas(self) -> List[Dict]:
        """Collect data from high-priority Norwegian Arctic areas only."""
        return self.collect_all_norwegian_arctic(priority_filter='high')
    
    def _process_barentswatch_response(self, data: Dict, region: str) -> List[Dict]:
        """
        Process BarentsWatch GeoJSON response into normalized vessel data.
        
        Args:
            data: GeoJSON response from BarentsWatch API
            region: Region name for tracking
            
        Returns:
            List of normalized vessel dictionaries
        """
        vessels = []
        
        try:
            if data.get('type') == 'FeatureCollection':
                features = data.get('features', [])
                
                for feature in features:
                    vessel = self._normalize_barentswatch_vessel(feature, region)
                    if vessel:
                        vessels.append(vessel)
            
            elif isinstance(data, list):
                # Handle array response
                for item in data:
                    vessel = self._normalize_barentswatch_vessel(item, region)
                    if vessel:
                        vessels.append(vessel)
            
            else:
                logger.warning(f"Unexpected BarentsWatch response format: {type(data)}")
        
        except Exception as e:
            logger.error(f"Failed to process BarentsWatch response: {e}")
        
        return vessels
    
    def _normalize_barentswatch_vessel(self, feature: Dict, region: str) -> Optional[Dict]:
        """
        Normalize BarentsWatch vessel data to standard format.
        
        Args:
            feature: GeoJSON feature or vessel object
            region: Source region
            
        Returns:
            Normalized vessel dictionary or None if invalid
        """
        try:
            # Handle GeoJSON feature format
            if feature.get('type') == 'Feature':
                geometry = feature.get('geometry', {})
                properties = feature.get('properties', {})
                
                # Extract coordinates
                coordinates = geometry.get('coordinates', [])
                if len(coordinates) >= 2:
                    longitude = float(coordinates[0])
                    latitude = float(coordinates[1])
                else:
                    return None
                
                # Extract vessel properties
                mmsi = properties.get('mmsi') or properties.get('MMSI')
                name = properties.get('shipname') or properties.get('vesselName') or properties.get('name')
                vessel_type = properties.get('shipType') or properties.get('vesselType') or properties.get('type')
                speed = properties.get('sog') or properties.get('speed') or properties.get('SOG', 0)
                course = properties.get('cog') or properties.get('course') or properties.get('COG', 0)
                timestamp = properties.get('timestamp') or properties.get('lastUpdate')
            
            else:
                # Handle direct object format
                latitude = feature.get('latitude') or feature.get('lat')
                longitude = feature.get('longitude') or feature.get('lon') or feature.get('lng')
                mmsi = feature.get('mmsi') or feature.get('MMSI')
                name = feature.get('shipname') or feature.get('vesselName') or feature.get('name')
                vessel_type = feature.get('shipType') or feature.get('vesselType') or feature.get('type')
                speed = feature.get('sog') or feature.get('speed') or feature.get('SOG', 0)
                course = feature.get('cog') or feature.get('course') or feature.get('COG', 0)
                timestamp = feature.get('timestamp') or feature.get('lastUpdate')
            
            # Validate required fields
            if not all([latitude, longitude, mmsi]):
                return None
            
            # Convert to floats
            latitude = float(latitude)
            longitude = float(longitude)
            speed = float(speed) if speed else 0.0
            course = float(course) if course else 0.0
            
            # Validate coordinates
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                return None
            
            # Handle timestamp
            if not timestamp:
                timestamp = datetime.now().isoformat()
            
            # Create normalized vessel
            vessel = {
                'mmsi': str(mmsi),
                'latitude': latitude,
                'longitude': longitude,
                'speed': speed,
                'course': course,
                'timestamp': timestamp,
                'name': name or f"VESSEL_{mmsi}",
                'type': vessel_type or 'Unknown',
                'source': 'barentswatch_official',
                'region': region,
                'data_quality': 'official_norwegian',
                'authority': 'Norwegian Coastal Administration'
            }
            
            return vessel
        
        except Exception as e:
            logger.warning(f"Failed to normalize BarentsWatch vessel: {e}")
            return None
    
    def _deduplicate_by_mmsi(self, vessels: List[Dict]) -> List[Dict]:
        """
        Remove duplicate vessels based on MMSI, keeping the most recent.
        
        Args:
            vessels: List of vessel dictionaries
            
        Returns:
            List of unique vessels
        """
        mmsi_dict = {}
        
        for vessel in vessels:
            mmsi = vessel.get('mmsi')
            if not mmsi or mmsi == 'unknown':
                continue
            
            # Keep the most recent vessel for each MMSI
            if mmsi not in mmsi_dict:
                mmsi_dict[mmsi] = vessel
            else:
                # Compare timestamps if available
                try:
                    current_time = datetime.fromisoformat(vessel['timestamp'].replace('Z', '+00:00'))
                    existing_time = datetime.fromisoformat(mmsi_dict[mmsi]['timestamp'].replace('Z', '+00:00'))
                    
                    if current_time > existing_time:
                        mmsi_dict[mmsi] = vessel
                except:
                    # If timestamp comparison fails, keep the existing vessel
                    pass
        
        return list(mmsi_dict.values())
    
    def save_barentswatch_data(self, vessels: List[Dict]) -> str:
        """Save BarentsWatch data with official Norwegian government tag."""
        if not vessels:
            return ""
        
        # Create today's directory
        today = datetime.now().strftime('%Y-%m-%d')
        today_dir = self.data_dir / today
        today_dir.mkdir(exist_ok=True)
        
        # Save with timestamp and official tag
        timestamp = datetime.now().strftime('%H%M%S')
        filename = f"barentswatch_official_{timestamp}.json"
        file_path = today_dir / filename
        
        # Add metadata
        save_data = {
            'metadata': {
                'source': 'BarentsWatch Official Norwegian API',
                'authority': 'Norwegian Coastal Administration',
                'collection_time': datetime.now().isoformat(),
                'api_version': 'v1',
                'total_vessels': len(vessels),
                'regions_covered': list(set(v.get('region', 'unknown') for v in vessels))
            },
            'vessels': vessels
        }
        
        # Save data
        with open(file_path, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        # Also save as latest official
        latest_file = today_dir / "latest_barentswatch_official.json"
        with open(latest_file, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        logger.info(f"Saved {len(vessels)} official Norwegian vessels to {file_path}")
        return str(file_path)
    
    def get_coverage_summary(self) -> Dict:
        """Get summary of Norwegian Arctic coverage areas."""
        return {
            'total_regions': len(self.norwegian_arctic_regions),
            'high_priority_regions': len([r for r in self.norwegian_arctic_regions.values() if r['priority'] == 'high']),
            'regions': {name: {'bbox': info['bbox'], 'priority': info['priority'], 'description': info['description']} 
                       for name, info in self.norwegian_arctic_regions.items()}
        }

# Test function
def test_barentswatch_collection():
    """Test BarentsWatch AIS collection."""
    print("🇳🇴 Testing BarentsWatch Official Norwegian Arctic AIS Collection")
    print("=" * 70)
    
    collector = BarentsWatchCollector()
    
    # Show coverage areas
    coverage = collector.get_coverage_summary()
    print(f"\n📍 Norwegian Arctic Coverage Areas:")
    for region, info in coverage['regions'].items():
        print(f"   • {region}: {info['description']} (Priority: {info['priority']})")
    
    # Test authentication
    print(f"\n🔑 Testing authentication...")
    if collector.auth.test_connection():
        print("   ✅ Authentication successful")
        
        # Test high-priority data collection
        print(f"\n🌊 Collecting from high-priority areas...")
        vessels = collector.collect_priority_areas()
        
        if vessels:
            print(f"   ✅ Collected {len(vessels)} official Norwegian vessels")
            
            # Show sample vessels
            print(f"\n🚢 Sample official Norwegian vessels:")
            for vessel in vessels[:5]:
                print(f"   • {vessel['name']} (MMSI: {vessel['mmsi']})")
                print(f"     Position: {vessel['latitude']:.3f}°N, {vessel['longitude']:.3f}°E")
                print(f"     Region: {vessel['region']} | Speed: {vessel['speed']:.1f} knots")
                print(f"     Authority: {vessel['authority']}")
            
            # Save official data
            saved_file = collector.save_barentswatch_data(vessels)
            print(f"\n💾 Official Norwegian data saved to: {saved_file}")
            
        else:
            print("   ⚠️ No vessels collected (may be normal for some regions)")
    
    else:
        print("   ❌ Authentication failed")
        print("\n💡 Setup instructions:")
        print("1. Visit: https://developer.barentswatch.no/")
        print("2. Register application with Client ID: henrikformoe@gmail.com:ArcticShadowTracker")
        print("3. Set environment variable: export BARENTSWATCH_CLIENT_SECRET='your_secret'")

if __name__ == "__main__":
    test_barentswatch_collection()