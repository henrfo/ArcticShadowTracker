#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Real Sentinel-1 SAR Data Collection
Integrates with Copernicus Data Space Ecosystem and Sentinel Hub for real SAR imagery.
"""

import requests
import json
import zipfile
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import time
import hashlib
from urllib.parse import urljoin
from io import BytesIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SentinelProduct:
    """Represents a Sentinel-1 product from search results"""
    id: str
    title: str
    size: str
    date: datetime
    footprint: str
    download_url: str
    orbit_direction: str
    product_type: str
    platform: str

class RealSentinelCollector:
    """Collects real Sentinel-1 SAR data from Copernicus services"""
    
    def __init__(self, data_dir: str = "data/satellite", credentials_file: str = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Arctic surveillance area
        self.arctic_bounds = {
            'north': 82.0,
            'south': 69.0,
            'east': 35.0,
            'west': 5.0
        }
        
        # Copernicus API endpoints
        self.api_endpoints = {
            'dataspace_search': 'https://catalogue.dataspace.copernicus.eu/odata/v1/Products',
            'dataspace_download': 'https://zipper.dataspace.copernicus.eu/odata/v1/Products',
            'dataspace_auth': 'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
            'scihub_search': 'https://scihub.copernicus.eu/dhus/search',
            'scihub_download': 'https://scihub.copernicus.eu/dhus/odata/v1/Products'
        }
        
        # Authentication
        self.credentials = self._load_credentials(credentials_file)
        self.access_token = None
        self.token_expiry = None
        
        # Download tracking
        self.download_log = self.data_dir / "download_log.json"
        
    def _load_credentials(self, credentials_file: Optional[str]) -> Dict[str, str]:
        """Load API credentials from file or environment"""
        credentials = {}
        
        # Try environment variables first
        credentials['dataspace_username'] = os.getenv('COPERNICUS_DATASPACE_USERNAME')
        credentials['dataspace_password'] = os.getenv('COPERNICUS_DATASPACE_PASSWORD')
        credentials['scihub_username'] = os.getenv('COPERNICUS_SCIHUB_USERNAME')
        credentials['scihub_password'] = os.getenv('COPERNICUS_SCIHUB_PASSWORD')
        
        # Try credentials file if provided
        if credentials_file and Path(credentials_file).exists():
            try:
                with open(credentials_file, 'r') as f:
                    file_creds = json.load(f)
                    credentials.update(file_creds)
            except Exception as e:
                logger.warning(f"Could not load credentials file: {e}")
        
        # Filter out None values
        return {k: v for k, v in credentials.items() if v is not None}
    
    def _authenticate_dataspace(self) -> bool:
        """Authenticate with Copernicus Data Space Ecosystem"""
        if not self.credentials.get('dataspace_username') or not self.credentials.get('dataspace_password'):
            logger.warning("Copernicus Data Space credentials not available")
            return False
        
        # Check if token is still valid
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return True
        
        try:
            auth_data = {
                'grant_type': 'password',
                'username': self.credentials['dataspace_username'],
                'password': self.credentials['dataspace_password'],
                'client_id': 'cdse-public'
            }
            
            response = requests.post(
                self.api_endpoints['dataspace_auth'],
                data=auth_data,
                timeout=30
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)  # 5 min buffer
            
            logger.info("Successfully authenticated with Copernicus Data Space")
            return True
            
        except Exception as e:
            logger.error(f"Data Space authentication failed: {e}")
            return False
    
    def _get_footprint_wkt(self) -> str:
        """Generate WKT polygon for Arctic surveillance area"""
        return f"POLYGON(({self.arctic_bounds['west']} {self.arctic_bounds['south']},{self.arctic_bounds['east']} {self.arctic_bounds['south']},{self.arctic_bounds['east']} {self.arctic_bounds['north']},{self.arctic_bounds['west']} {self.arctic_bounds['north']},{self.arctic_bounds['west']} {self.arctic_bounds['south']}))"
    
    def search_sentinel1_products(self, start_date: datetime, end_date: datetime, 
                                 max_results: int = 50) -> List[SentinelProduct]:
        """Search for Sentinel-1 products in Arctic region"""
        logger.info(f"Searching for Sentinel-1 products from {start_date.date()} to {end_date.date()}")
        
        products = []
        
        # Try Copernicus Data Space first
        products.extend(self._search_dataspace(start_date, end_date, max_results))
        
        # Fallback to SciHub if needed
        if len(products) < max_results // 2:
            products.extend(self._search_scihub(start_date, end_date, max_results - len(products)))
        
        # Sort by date (newest first)
        products.sort(key=lambda p: p.date, reverse=True)
        
        logger.info(f"Found {len(products)} Sentinel-1 products")
        return products[:max_results]
    
    def _search_dataspace(self, start_date: datetime, end_date: datetime, max_results: int) -> List[SentinelProduct]:
        """Search Copernicus Data Space Ecosystem"""
        if not self._authenticate_dataspace():
            return []
        
        try:
            # Build OData query
            date_filter = f"ContentDate/Start ge {start_date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z and ContentDate/Start le {end_date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z"
            collection_filter = "Collection/Name eq 'SENTINEL-1'"
            footprint_filter = f"OData.CSC.Intersects(area=geography'SRID=4326;{self._get_footprint_wkt()}')"
            
            query_params = {
                '$filter': f"{collection_filter} and {date_filter} and {footprint_filter}",
                '$orderby': 'ContentDate/Start desc',
                '$top': max_results,
                '$expand': 'Attributes'
            }
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                self.api_endpoints['dataspace_search'],
                params=query_params,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            products = []
            
            for item in data.get('value', []):
                try:
                    product = SentinelProduct(
                        id=item['Id'],
                        title=item['Name'],
                        size=item.get('ContentLength', 'Unknown'),
                        date=datetime.fromisoformat(item['ContentDate']['Start'].replace('Z', '+00:00')),
                        footprint=item.get('Footprint', ''),
                        download_url=f"{self.api_endpoints['dataspace_download']}({item['Id']})/$value",
                        orbit_direction=self._extract_attribute(item, 'orbitdirection'),
                        product_type=self._extract_attribute(item, 'producttype'),
                        platform=self._extract_attribute(item, 'platformname')
                    )
                    products.append(product)
                except Exception as e:
                    logger.warning(f"Failed to parse product item: {e}")
                    continue
            
            logger.info(f"Data Space: Found {len(products)} products")
            return products
            
        except Exception as e:
            logger.error(f"Data Space search failed: {e}")
            return []
    
    def _search_scihub(self, start_date: datetime, end_date: datetime, max_results: int) -> List[SentinelProduct]:
        """Search Copernicus SciHub (backup)"""
        if not self.credentials.get('scihub_username') or not self.credentials.get('scihub_password'):
            logger.warning("SciHub credentials not available")
            return []
        
        try:
            # Build OpenSearch query
            footprint = self._get_footprint_wkt()
            query_params = {
                'q': f'platformname:Sentinel-1 AND footprint:"Intersects({footprint})" AND beginPosition:[{start_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")} TO {end_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}]',
                'rows': max_results,
                'start': 0,
                'orderby': 'beginposition desc',
                'format': 'json'
            }
            
            auth = (self.credentials['scihub_username'], self.credentials['scihub_password'])
            
            response = requests.get(
                self.api_endpoints['scihub_search'],
                params=query_params,
                auth=auth,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            products = []
            
            entries = data.get('feed', {}).get('entry', [])
            if isinstance(entries, dict):  # Single result
                entries = [entries]
            
            for entry in entries:
                try:
                    product_id = entry['id']
                    title = entry['title']
                    
                    # Extract attributes
                    attributes = {}
                    for attr in entry.get('str', []):
                        if isinstance(attr, dict):
                            attributes[attr.get('name', '')] = attr.get('content', '')
                    
                    product = SentinelProduct(
                        id=product_id,
                        title=title,
                        size=attributes.get('size', 'Unknown'),
                        date=datetime.fromisoformat(attributes.get('beginposition', '').replace('Z', '+00:00')),
                        footprint=attributes.get('footprint', ''),
                        download_url=f"{self.api_endpoints['scihub_download']}('{product_id}')/$value",
                        orbit_direction=attributes.get('orbitdirection', 'Unknown'),
                        product_type=attributes.get('producttype', 'Unknown'),
                        platform=attributes.get('platformname', 'Unknown')
                    )
                    products.append(product)
                    
                except Exception as e:
                    logger.warning(f"Failed to parse SciHub entry: {e}")
                    continue
            
            logger.info(f"SciHub: Found {len(products)} products")
            return products
            
        except Exception as e:
            logger.error(f"SciHub search failed: {e}")
            return []
    
    def _extract_attribute(self, item: Dict, attr_name: str) -> str:
        """Extract attribute from Data Space API response"""
        try:
            attributes = item.get('Attributes', [])
            for attr in attributes:
                if attr.get('Name', '').lower() == attr_name.lower():
                    return attr.get('Value', 'Unknown')
            return 'Unknown'
        except:
            return 'Unknown'
    
    def download_product(self, product: SentinelProduct, extract: bool = False) -> Optional[Path]:
        """Download a Sentinel-1 product"""
        logger.info(f"Downloading {product.title}...")
        
        # Check if already downloaded
        local_path = self.data_dir / f"{product.title}.zip"
        if local_path.exists():
            logger.info(f"Product already exists: {local_path.name}")
            return local_path
        
        try:
            # Prepare authentication headers
            headers = {}
            auth = None
            
            if self.access_token and 'dataspace' in product.download_url:
                headers['Authorization'] = f'Bearer {self.access_token}'
            elif 'scihub' in product.download_url:
                auth = (self.credentials.get('scihub_username'), self.credentials.get('scihub_password'))
            
            # Start download with streaming
            response = requests.get(
                product.download_url,
                headers=headers,
                auth=auth,
                stream=True,
                timeout=300
            )
            response.raise_for_status()
            
            # Download with progress tracking
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress every 100MB
                        if downloaded % (100 * 1024 * 1024) == 0 and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            logger.info(f"Download progress: {progress:.1f}%")
            
            logger.info(f"Download complete: {local_path.name} ({downloaded / (1024*1024):.1f} MB)")
            
            # Log download
            self._log_download(product, local_path)
            
            # Extract if requested
            if extract:
                extract_path = self._extract_product(local_path)
                return extract_path
            
            return local_path
            
        except Exception as e:
            logger.error(f"Download failed for {product.title}: {e}")
            if local_path.exists():
                local_path.unlink()  # Remove partial download
            return None
    
    def _extract_product(self, zip_path: Path) -> Optional[Path]:
        """Extract Sentinel-1 product ZIP file"""
        extract_dir = zip_path.parent / zip_path.stem
        
        if extract_dir.exists():
            logger.info(f"Product already extracted: {extract_dir.name}")
            return extract_dir
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            logger.info(f"Extracted to: {extract_dir.name}")
            return extract_dir
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return None
    
    def _log_download(self, product: SentinelProduct, local_path: Path):
        """Log download to tracking file"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'product_id': product.id,
            'title': product.title,
            'date': product.date.isoformat(),
            'local_path': str(local_path),
            'size_mb': local_path.stat().st_size / (1024 * 1024) if local_path.exists() else 0
        }
        
        # Load existing log
        log_data = []
        if self.download_log.exists():
            try:
                with open(self.download_log, 'r') as f:
                    log_data = json.load(f)
            except:
                pass
        
        # Add new entry
        log_data.append(log_entry)
        
        # Save updated log
        with open(self.download_log, 'w') as f:
            json.dump(log_data, f, indent=2)
    
    def fetch_latest_data(self, days_back: int = 3, max_products: int = 10) -> List[Path]:
        """Fetch latest Sentinel-1 data for Arctic region"""
        logger.info(f"Fetching latest Sentinel-1 data ({days_back} days back, max {max_products} products)")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Search for products
        products = self.search_sentinel1_products(start_date, end_date, max_products)
        
        if not products:
            logger.warning("No Sentinel-1 products found for the specified period")
            return []
        
        # Download products
        downloaded_files = []
        for i, product in enumerate(products[:max_products]):
            logger.info(f"Processing product {i+1}/{len(products[:max_products])}")
            
            local_path = self.download_product(product, extract=False)
            if local_path:
                downloaded_files.append(local_path)
            
            # Rate limiting between downloads
            if i < len(products) - 1:
                time.sleep(2)
        
        logger.info(f"Downloaded {len(downloaded_files)} Sentinel-1 products")
        return downloaded_files
    
    def fetch_historical_data(self, start_date: datetime, end_date: datetime, 
                             max_products: int = 100) -> List[Path]:
        """Fetch historical Sentinel-1 data for date range"""
        logger.info(f"Fetching historical Sentinel-1 data from {start_date.date()} to {end_date.date()}")
        
        # Search for products
        products = self.search_sentinel1_products(start_date, end_date, max_products)
        
        if not products:
            logger.warning("No historical Sentinel-1 products found")
            return []
        
        # Download products in batches to avoid overwhelming the servers
        downloaded_files = []
        batch_size = 5
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(products) + batch_size - 1) // batch_size}")
            
            for product in batch:
                local_path = self.download_product(product, extract=False)
                if local_path:
                    downloaded_files.append(local_path)
                
                time.sleep(1)  # Rate limiting
            
            # Longer pause between batches
            if i + batch_size < len(products):
                logger.info("Pausing between batches...")
                time.sleep(10)
        
        logger.info(f"Downloaded {len(downloaded_files)} historical Sentinel-1 products")
        return downloaded_files
    
    def get_download_statistics(self) -> Dict[str, any]:
        """Get statistics about downloaded products"""
        stats = {
            'total_products': 0,
            'total_size_gb': 0,
            'date_range': None,
            'platforms': {},
            'orbit_directions': {},
            'recent_downloads': []
        }
        
        if not self.download_log.exists():
            return stats
        
        try:
            with open(self.download_log, 'r') as f:
                log_data = json.load(f)
            
            if not log_data:
                return stats
            
            stats['total_products'] = len(log_data)
            stats['total_size_gb'] = sum(entry.get('size_mb', 0) for entry in log_data) / 1024
            
            # Date range
            dates = [datetime.fromisoformat(entry['date']) for entry in log_data if 'date' in entry]
            if dates:
                stats['date_range'] = {
                    'start': min(dates).isoformat(),
                    'end': max(dates).isoformat()
                }
            
            # Recent downloads (last 5)
            stats['recent_downloads'] = [
                {
                    'title': entry['title'],
                    'date': entry['date'],
                    'size_mb': entry.get('size_mb', 0)
                }
                for entry in sorted(log_data, key=lambda x: x['timestamp'], reverse=True)[:5]
            ]
            
        except Exception as e:
            logger.error(f"Failed to load download statistics: {e}")
        
        return stats

def main():
    """Command line interface for Sentinel-1 data collection"""
    collector = RealSentinelCollector()
    
    print("🛰️ Arctic Sentinel-1 SAR Data Collector")
    print("=" * 45)
    print("1. Fetch latest data (last 3 days)")
    print("2. Fetch historical data (last 7 days)")
    print("3. Fetch historical data (last 30 days)")
    print("4. Search products only (no download)")
    print("5. Show download statistics")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    if choice == "1":
        files = collector.fetch_latest_data(days_back=3, max_products=5)
        print(f"\n✅ Downloaded {len(files)} latest Sentinel-1 products")
        for file in files:
            print(f"   - {file.name}")
    
    elif choice == "2":
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        files = collector.fetch_historical_data(start_date, end_date, max_products=20)
        print(f"\n✅ Downloaded {len(files)} historical Sentinel-1 products")
    
    elif choice == "3":
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        files = collector.fetch_historical_data(start_date, end_date, max_products=50)
        print(f"\n✅ Downloaded {len(files)} historical Sentinel-1 products")
    
    elif choice == "4":
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        products = collector.search_sentinel1_products(start_date, end_date, max_results=20)
        
        print(f"\n🔍 Found {len(products)} Sentinel-1 products:")
        for i, product in enumerate(products[:10]):
            print(f"   {i+1}. {product.title}")
            print(f"      Date: {product.date.strftime('%Y-%m-%d %H:%M')}")
            print(f"      Platform: {product.platform}, Orbit: {product.orbit_direction}")
            print(f"      Size: {product.size}")
            print()
    
    elif choice == "5":
        stats = collector.get_download_statistics()
        print(f"\n📊 Download Statistics:")
        print(f"   Total products: {stats['total_products']}")
        print(f"   Total size: {stats['total_size_gb']:.2f} GB")
        
        if stats['date_range']:
            start_date = datetime.fromisoformat(stats['date_range']['start'])
            end_date = datetime.fromisoformat(stats['date_range']['end'])
            print(f"   Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        if stats['recent_downloads']:
            print(f"\n   Recent downloads:")
            for download in stats['recent_downloads']:
                date = datetime.fromisoformat(download['date'])
                print(f"     - {download['title']} ({date.strftime('%Y-%m-%d')}, {download['size_mb']:.1f} MB)")
    
    else:
        print("❌ Invalid option")
    
    print("\n📝 Note: Requires Copernicus account credentials")
    print("Set environment variables:")
    print("  COPERNICUS_DATASPACE_USERNAME")
    print("  COPERNICUS_DATASPACE_PASSWORD")

if __name__ == "__main__":
    main()