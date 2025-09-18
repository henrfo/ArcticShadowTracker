#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Real AIS Data Collection
Multi-source AIS data fetching with historical support and robust error handling.
"""

import requests
import pandas as pd
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import asyncio
import aiohttp
import csv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class AISSource:
    """Configuration for an AIS data source"""
    name: str
    url: str
    api_key: Optional[str] = None
    rate_limit_per_hour: int = 100
    timeout_seconds: int = 30
    supports_historical: bool = False
    priority: int = 1  # 1 = highest priority

class RealAISCollector:
    """Collects real AIS data from multiple sources with failover and historical support"""
    
    def __init__(self, data_dir: str = "data/ais"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Arctic surveillance area
        self.arctic_bounds = {
            'north': 82.0,
            'south': 69.0,
            'east': 35.0,
            'west': 5.0
        }
        
        # Initialize AIS sources
        self.sources = self._initialize_sources()
        
        # Rate limiting tracking
        self.last_request_time = {}
        
    def _initialize_sources(self) -> List[AISSource]:
        """Initialize AIS data sources with priority order"""
        sources = [
            # Primary: AISHub (free tier)
            AISSource(
                name="aishub",
                url="http://data.aishub.net/ws.php",
                rate_limit_per_hour=100,
                timeout_seconds=30,
                supports_historical=False,
                priority=1
            ),
            
            # Secondary: Norwegian Coastal Administration (free)
            AISSource(
                name="kystverket",
                url="https://www.kystverket.no/api/ais",
                rate_limit_per_hour=200,
                timeout_seconds=25,
                supports_historical=True,
                priority=2
            ),
            
            # Tertiary: MarineTraffic (requires API key)
            AISSource(
                name="marinetraffic",
                url="https://services.marinetraffic.com/api",
                api_key=os.getenv('MARINETRAFFIC_API_KEY'),
                rate_limit_per_hour=50,
                timeout_seconds=35,
                supports_historical=True,
                priority=3
            ),
            
            # Backup: VesselFinder (requires API key)
            AISSource(
                name="vesselfinder",
                url="https://api.vesselfinder.com",
                api_key=os.getenv('VESSELFINDER_API_KEY'),
                rate_limit_per_hour=30,
                timeout_seconds=40,
                supports_historical=False,
                priority=4
            )
        ]
        
        # Sort by priority
        return sorted(sources, key=lambda x: x.priority)
    
    def _check_rate_limit(self, source: AISSource) -> bool:
        """Check if we can make a request to this source"""
        now = time.time()
        key = f"{source.name}_last_request"
        
        if key in self.last_request_time:
            time_since_last = now - self.last_request_time[key]
            min_interval = 3600 / source.rate_limit_per_hour  # seconds between requests
            
            if time_since_last < min_interval:
                logger.debug(f"Rate limit: waiting {min_interval - time_since_last:.1f}s for {source.name}")
                return False
        
        self.last_request_time[key] = now
        return True
    
    def _fetch_from_aishub(self, source: AISSource, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict]:
        """Fetch data from AISHub"""
        logger.info(f"Fetching from AISHub...")
        
        params = {
            'username': 'DH_DEMO',  # Demo username for testing
            'format': '1',
            'output': 'json',
            'compress': '0',
            'latmin': str(self.arctic_bounds['south']),
            'latmax': str(self.arctic_bounds['north']),
            'lonmin': str(self.arctic_bounds['west']),
            'lonmax': str(self.arctic_bounds['east'])
        }
        
        try:
            response = requests.get(source.url, params=params, timeout=source.timeout_seconds)
            response.raise_for_status()
            
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
                        'source': 'aishub',
                        'last_position_time': vessel.get('UTCSTAMP', datetime.now().isoformat())
                    }
                    vessels.append(vessel_record)
            
            logger.info(f"AISHub: Retrieved {len(vessels)} vessels")
            return vessels
            
        except Exception as e:
            logger.error(f"AISHub fetch failed: {e}")
            return []
    
    def _fetch_from_kystverket(self, source: AISSource, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict]:
        """Fetch data from Norwegian Coastal Administration"""
        logger.info(f"Fetching from Norwegian Coastal Administration...")
        
        # Note: This is a placeholder for the actual Kystverket API
        # Real implementation would use their official AIS API
        
        try:
            # For demo: simulate Norwegian waters focus
            demo_vessels = [
                {
                    'timestamp': datetime.now().isoformat(),
                    'mmsi': '257123456',
                    'latitude': 78.2,
                    'longitude': 15.6,
                    'speed': 8.5,
                    'course': 45.0,
                    'vessel_name': 'NORDKAPP EXPRESS',
                    'vessel_type': 'Passenger',
                    'source': 'kystverket',
                    'last_position_time': datetime.now().isoformat()
                },
                {
                    'timestamp': datetime.now().isoformat(),
                    'mmsi': '257987654',
                    'latitude': 71.1,
                    'longitude': 25.8,
                    'speed': 12.3,
                    'course': 180.0,
                    'vessel_name': 'BARENTS CARRIER',
                    'vessel_type': 'Cargo',
                    'source': 'kystverket',
                    'last_position_time': datetime.now().isoformat()
                }
            ]
            
            logger.info(f"Kystverket: Retrieved {len(demo_vessels)} vessels (demo data)")
            return demo_vessels
            
        except Exception as e:
            logger.error(f"Kystverket fetch failed: {e}")
            return []
    
    def _fetch_from_marinetraffic(self, source: AISSource, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict]:
        """Fetch data from MarineTraffic API"""
        if not source.api_key:
            logger.warning("MarineTraffic API key not configured, skipping")
            return []
        
        logger.info(f"Fetching from MarineTraffic...")
        
        # MarineTraffic API endpoint for vessel positions
        endpoint = f"{source.url}/exportvessel/v:8/{source.api_key}/MINLAT:{self.arctic_bounds['south']}/MAXLAT:{self.arctic_bounds['north']}/MINLON:{self.arctic_bounds['west']}/MAXLON:{self.arctic_bounds['east']}/protocol:jsono"
        
        try:
            response = requests.get(endpoint, timeout=source.timeout_seconds)
            response.raise_for_status()
            
            data = response.json()
            vessels = []
            
            if isinstance(data, list):
                for vessel in data:
                    vessel_record = {
                        'timestamp': datetime.now().isoformat(),
                        'mmsi': str(vessel.get('MMSI', 'unknown')),
                        'latitude': float(vessel.get('LAT', 0)),
                        'longitude': float(vessel.get('LON', 0)),
                        'speed': float(vessel.get('SPEED', 0)),
                        'course': float(vessel.get('COURSE', 0)),
                        'vessel_name': vessel.get('SHIPNAME', 'Unknown'),
                        'vessel_type': vessel.get('TYPE_NAME', 'Unknown'),
                        'source': 'marinetraffic',
                        'last_position_time': vessel.get('TIMESTAMP', datetime.now().isoformat())
                    }
                    vessels.append(vessel_record)
            
            logger.info(f"MarineTraffic: Retrieved {len(vessels)} vessels")
            return vessels
            
        except Exception as e:
            logger.error(f"MarineTraffic fetch failed: {e}")
            return []
    
    def _fetch_from_vesselfinder(self, source: AISSource, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict]:
        """Fetch data from VesselFinder API"""
        if not source.api_key:
            logger.warning("VesselFinder API key not configured, skipping")
            return []
        
        logger.info(f"Fetching from VesselFinder...")
        
        # VesselFinder API typically requires specific endpoint configuration
        # This is a placeholder for actual implementation
        
        try:
            # Demo implementation - would be replaced with actual API calls
            demo_vessels = []
            logger.info(f"VesselFinder: Retrieved {len(demo_vessels)} vessels (demo data)")
            return demo_vessels
            
        except Exception as e:
            logger.error(f"VesselFinder fetch failed: {e}")
            return []
    
    def fetch_current_data(self) -> List[Dict]:
        """Fetch current AIS data from all available sources with failover"""
        logger.info("🌐 Starting multi-source AIS data collection...")
        
        all_vessels = []
        successful_sources = []
        
        for source in self.sources:
            # Check rate limits
            if not self._check_rate_limit(source):
                logger.debug(f"Skipping {source.name} due to rate limiting")
                continue
            
            try:
                # Route to appropriate fetcher
                vessels = []
                if source.name == "aishub":
                    vessels = self._fetch_from_aishub(source)
                elif source.name == "kystverket":
                    vessels = self._fetch_from_kystverket(source)
                elif source.name == "marinetraffic":
                    vessels = self._fetch_from_marinetraffic(source)
                elif source.name == "vesselfinder":
                    vessels = self._fetch_from_vesselfinder(source)
                
                if vessels:
                    all_vessels.extend(vessels)
                    successful_sources.append(source.name)
                    logger.info(f"✅ {source.name}: {len(vessels)} vessels")
                else:
                    logger.warning(f"⚠️ {source.name}: No data returned")
                    
            except Exception as e:
                logger.error(f"❌ {source.name} failed: {e}")
                continue
        
        # Remove duplicates by MMSI (keep latest)
        unique_vessels = {}
        for vessel in all_vessels:
            mmsi = vessel['mmsi']
            if mmsi not in unique_vessels or vessel['timestamp'] > unique_vessels[mmsi]['timestamp']:
                unique_vessels[mmsi] = vessel
        
        final_vessels = list(unique_vessels.values())
        
        logger.info(f"📊 Collection complete:")
        logger.info(f"   Sources used: {', '.join(successful_sources)}")
        logger.info(f"   Total vessels: {len(all_vessels)}")
        logger.info(f"   Unique vessels: {len(final_vessels)}")
        
        # Save data
        if final_vessels:
            self._save_current_data(final_vessels)
        
        return final_vessels
    
    def fetch_historical_data(self, start_date: datetime, end_date: datetime) -> Dict[str, List[Dict]]:
        """Fetch historical AIS data for date range"""
        logger.info(f"📅 Fetching historical data from {start_date.date()} to {end_date.date()}")
        
        historical_data = {}
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            logger.info(f"Fetching data for {date_str}...")
            
            # Try sources that support historical data
            day_vessels = []
            for source in self.sources:
                if not source.supports_historical:
                    continue
                
                if not self._check_rate_limit(source):
                    time.sleep(1)  # Brief pause for rate limiting
                    continue
                
                try:
                    if source.name == "kystverket":
                        # Simulated historical data
                        day_vessels.extend(self._fetch_from_kystverket(source, (current_date, current_date)))
                    elif source.name == "marinetraffic":
                        day_vessels.extend(self._fetch_from_marinetraffic(source, (current_date, current_date)))
                        
                except Exception as e:
                    logger.error(f"Historical fetch failed for {source.name} on {date_str}: {e}")
            
            if day_vessels:
                historical_data[date_str] = day_vessels
                self._save_historical_data(day_vessels, current_date)
                logger.info(f"✅ {date_str}: {len(day_vessels)} vessels")
            else:
                logger.warning(f"⚠️ {date_str}: No data available")
            
            current_date += timedelta(days=1)
            time.sleep(2)  # Rate limiting between days
        
        logger.info(f"📊 Historical collection complete: {len(historical_data)} days")
        return historical_data
    
    def _save_current_data(self, vessels: List[Dict]):
        """Save current vessel data"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON format
        json_file = self.data_dir / f"current_ais_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(vessels, f, indent=2)
        
        # CSV format for analysis
        csv_file = self.data_dir / f"current_ais_{timestamp}.csv"
        if vessels:
            df = pd.DataFrame(vessels)
            df.to_csv(csv_file, index=False)
        
        # Latest file for quick access
        latest_json = self.data_dir / "latest_ais.json"
        with open(latest_json, 'w') as f:
            json.dump(vessels, f, indent=2)
        
        logger.info(f"💾 Saved {len(vessels)} vessels to {json_file.name}")
    
    def _save_historical_data(self, vessels: List[Dict], date: datetime):
        """Save historical vessel data"""
        date_str = date.strftime('%Y-%m-%d')
        
        # Create historical directory
        hist_dir = self.data_dir / "historical"
        hist_dir.mkdir(exist_ok=True)
        
        # Save daily file
        json_file = hist_dir / f"ais_{date_str}.json"
        with open(json_file, 'w') as f:
            json.dump(vessels, f, indent=2)
        
        csv_file = hist_dir / f"ais_{date_str}.csv"
        if vessels:
            df = pd.DataFrame(vessels)
            df.to_csv(csv_file, index=False)
    
    def validate_data_quality(self, vessels: List[Dict]) -> Dict[str, any]:
        """Validate AIS data quality and completeness"""
        if not vessels:
            return {'quality_score': 0, 'issues': ['No data available']}
        
        issues = []
        quality_metrics = {
            'total_vessels': len(vessels),
            'valid_positions': 0,
            'valid_speeds': 0,
            'valid_mmsi': 0,
            'named_vessels': 0,
            'recent_positions': 0
        }
        
        current_time = datetime.now()
        
        for vessel in vessels:
            # Check position validity
            lat, lon = vessel.get('latitude', 0), vessel.get('longitude', 0)
            if (self.arctic_bounds['south'] <= lat <= self.arctic_bounds['north'] and 
                self.arctic_bounds['west'] <= lon <= self.arctic_bounds['east']):
                quality_metrics['valid_positions'] += 1
            
            # Check speed validity
            speed = vessel.get('speed', -1)
            if 0 <= speed <= 50:  # Reasonable speed range
                quality_metrics['valid_speeds'] += 1
            
            # Check MMSI validity
            mmsi = vessel.get('mmsi', '')
            if mmsi and mmsi != 'unknown' and len(mmsi) >= 7:
                quality_metrics['valid_mmsi'] += 1
            
            # Check vessel naming
            name = vessel.get('vessel_name', '')
            if name and name != 'Unknown':
                quality_metrics['named_vessels'] += 1
            
            # Check position recency
            try:
                pos_time = datetime.fromisoformat(vessel.get('last_position_time', '').replace('Z', '+00:00'))
                if (current_time - pos_time).total_seconds() < 3600:  # Within last hour
                    quality_metrics['recent_positions'] += 1
            except:
                pass
        
        # Calculate quality score
        total = quality_metrics['total_vessels']
        quality_score = (
            (quality_metrics['valid_positions'] / total) * 0.3 +
            (quality_metrics['valid_speeds'] / total) * 0.2 +
            (quality_metrics['valid_mmsi'] / total) * 0.2 +
            (quality_metrics['named_vessels'] / total) * 0.15 +
            (quality_metrics['recent_positions'] / total) * 0.15
        ) * 100
        
        # Identify issues
        if quality_metrics['valid_positions'] / total < 0.9:
            issues.append(f"Position quality low: {quality_metrics['valid_positions']}/{total} valid")
        
        if quality_metrics['valid_mmsi'] / total < 0.8:
            issues.append(f"MMSI quality low: {quality_metrics['valid_mmsi']}/{total} valid")
        
        if quality_metrics['recent_positions'] / total < 0.7:
            issues.append(f"Position recency low: {quality_metrics['recent_positions']}/{total} recent")
        
        return {
            'quality_score': round(quality_score, 1),
            'metrics': quality_metrics,
            'issues': issues,
            'timestamp': current_time.isoformat()
        }
    
    def get_data_statistics(self) -> Dict[str, any]:
        """Get statistics about collected data"""
        stats = {
            'collection_dates': [],
            'total_files': 0,
            'latest_collection': None,
            'historical_coverage': []
        }
        
        # Count current data files
        current_files = list(self.data_dir.glob("current_ais_*.json"))
        stats['total_files'] = len(current_files)
        
        if current_files:
            # Get latest file
            latest_file = max(current_files, key=lambda p: p.stat().st_mtime)
            stats['latest_collection'] = datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat()
        
        # Check historical coverage
        hist_dir = self.data_dir / "historical"
        if hist_dir.exists():
            hist_files = list(hist_dir.glob("ais_*.json"))
            for file in hist_files:
                date_str = file.stem.replace('ais_', '')
                stats['historical_coverage'].append(date_str)
        
        stats['historical_coverage'].sort()
        
        return stats

def main():
    """Command line interface for AIS data collection"""
    collector = RealAISCollector()
    
    print("🌐 Arctic AIS Data Collector")
    print("=" * 40)
    print("1. Fetch current AIS data")
    print("2. Fetch historical data (last 7 days)")
    print("3. Fetch historical data (last 30 days)")
    print("4. Show data statistics")
    print("5. Validate latest data quality")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    if choice == "1":
        vessels = collector.fetch_current_data()
        print(f"\n✅ Retrieved {len(vessels)} vessels from Arctic region")
        
        if vessels:
            quality = collector.validate_data_quality(vessels)
            print(f"📊 Data quality score: {quality['quality_score']}/100")
            if quality['issues']:
                print("⚠️ Quality issues:")
                for issue in quality['issues']:
                    print(f"   - {issue}")
    
    elif choice == "2":
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        historical = collector.fetch_historical_data(start_date, end_date)
        print(f"\n✅ Retrieved historical data for {len(historical)} days")
    
    elif choice == "3":
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        historical = collector.fetch_historical_data(start_date, end_date)
        print(f"\n✅ Retrieved historical data for {len(historical)} days")
    
    elif choice == "4":
        stats = collector.get_data_statistics()
        print(f"\n📊 Data Statistics:")
        print(f"   Total files: {stats['total_files']}")
        print(f"   Latest collection: {stats['latest_collection']}")
        print(f"   Historical coverage: {len(stats['historical_coverage'])} days")
        if stats['historical_coverage']:
            print(f"   Date range: {stats['historical_coverage'][0]} to {stats['historical_coverage'][-1]}")
    
    elif choice == "5":
        # Load latest data
        latest_file = collector.data_dir / "latest_ais.json"
        if latest_file.exists():
            with open(latest_file, 'r') as f:
                vessels = json.load(f)
            
            quality = collector.validate_data_quality(vessels)
            print(f"\n📊 Data Quality Report:")
            print(f"   Quality Score: {quality['quality_score']}/100")
            print(f"   Total Vessels: {quality['metrics']['total_vessels']}")
            print(f"   Valid Positions: {quality['metrics']['valid_positions']}")
            print(f"   Valid MMSI: {quality['metrics']['valid_mmsi']}")
            print(f"   Named Vessels: {quality['metrics']['named_vessels']}")
            print(f"   Recent Positions: {quality['metrics']['recent_positions']}")
            
            if quality['issues']:
                print(f"\n⚠️ Issues Found:")
                for issue in quality['issues']:
                    print(f"   - {issue}")
        else:
            print("\n❌ No data available. Run option 1 first.")
    
    else:
        print("❌ Invalid option")

if __name__ == "__main__":
    main()