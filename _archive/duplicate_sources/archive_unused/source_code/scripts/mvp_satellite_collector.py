#!/usr/bin/env python3
"""
MVP Copernicus Satellite Image Collector
Simple script that fetches actual satellite images from Copernicus and saves to timestamped files.
No databases, no fancy processing - just prove we can get real data.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from utils.real_sentinel_collector import RealSentinelCollector

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """MVP data collection - prove we can get real Arctic satellite imagery."""
    print("🛰️ MVP Copernicus Satellite Image Collector")
    print("=" * 50)
    
    # Create output directory
    output_dir = Path('data/mvp_pipeline/satellite')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize collector
    collector = RealSentinelCollector(data_dir=str(output_dir))
    
    # Generate timestamp for this run
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Collection log
    collection_log = {
        'timestamp': datetime.now().isoformat(),
        'source': 'copernicus_sentinel1',
        'status': 'started',
        'products_found': 0,
        'products_downloaded': 0,
        'search_days_back': 3,
        'errors': []
    }
    
    try:
        # Check credentials
        if not collector.credentials.get('dataspace_username') and not collector.credentials.get('scihub_username'):
            error_msg = "No Copernicus credentials found"
            logger.error(error_msg)
            collection_log['status'] = 'failed'
            collection_log['errors'].append(error_msg)
            
            # Save failure log
            log_file = output_dir / f"satellite_failed_{timestamp}.json"
            with open(log_file, 'w') as f:
                json.dump(collection_log, f, indent=2)
            
            print(f"❌ No credentials found - see {log_file}")
            print("\n💡 Setup instructions:")
            print("1. Register FREE at: https://dataspace.copernicus.eu/")
            print("2. Set environment variables:")
            print("   export COPERNICUS_DATASPACE_USERNAME='your_username'")
            print("   export COPERNICUS_DATASPACE_PASSWORD='your_password'")
            return
        
        logger.info("✅ Credentials found")
        
        # Search for recent Sentinel-1 products (last 3 days)
        logger.info("Searching for recent Sentinel-1 Arctic imagery...")
        print("🔄 Searching for Sentinel-1 Arctic imagery (last 3 days)...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        
        products = collector.search_sentinel1_products(start_date, end_date, max_results=5)
        
        collection_log['products_found'] = len(products)
        
        if products:
            print(f"✅ Found {len(products)} Sentinel-1 products")
            
            # Show available products
            print(f"\n📡 Available products:")
            for i, product in enumerate(products):
                print(f"   {i+1}. {product.title}")
                print(f"      Date: {product.date.strftime('%Y-%m-%d %H:%M')}")
                print(f"      Platform: {product.platform}, Size: {product.size}")
                print(f"      Orbit: {product.orbit_direction}")
            
            # Try to download the most recent product
            print(f"\n⬇️ Attempting to download most recent product...")
            latest_product = products[0]
            
            try:
                downloaded_file = collector.download_product(latest_product, extract=False)
                
                if downloaded_file:
                    collection_log['status'] = 'success'
                    collection_log['products_downloaded'] = 1
                    collection_log['downloaded_product'] = {
                        'title': latest_product.title,
                        'date': latest_product.date.isoformat(),
                        'size': latest_product.size,
                        'local_path': str(downloaded_file)
                    }
                    
                    print(f"✅ SUCCESS: Downloaded satellite image")
                    print(f"📁 File: {downloaded_file}")
                    print(f"📊 Product: {latest_product.title}")
                    print(f"📅 Date: {latest_product.date.strftime('%Y-%m-%d %H:%M')}")
                    
                    # Create metadata file
                    metadata_file = output_dir / f"satellite_metadata_{timestamp}.json"
                    metadata = {
                        'collection_time': datetime.now().isoformat(),
                        'source': 'Copernicus Sentinel-1',
                        'product': {
                            'id': latest_product.id,
                            'title': latest_product.title,
                            'date': latest_product.date.isoformat(),
                            'size': latest_product.size,
                            'platform': latest_product.platform,
                            'orbit_direction': latest_product.orbit_direction,
                            'product_type': latest_product.product_type
                        },
                        'local_file': str(downloaded_file),
                        'arctic_bounds': collector.arctic_bounds
                    }
                    
                    with open(metadata_file, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    
                    # Save latest copy
                    latest_metadata = output_dir / "latest_satellite_metadata.json"
                    with open(latest_metadata, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    
                    print(f"📋 Metadata: {metadata_file}")
                    
                else:
                    collection_log['status'] = 'download_failed'
                    collection_log['errors'].append("Download failed for latest product")
                    print("❌ Download failed for latest product")
            
            except Exception as download_error:
                error_msg = f"Download error: {str(download_error)}"
                collection_log['status'] = 'download_error'
                collection_log['errors'].append(error_msg)
                print(f"❌ Download error: {download_error}")
        
        else:
            collection_log['status'] = 'no_products'
            collection_log['errors'].append("No Sentinel-1 products found in Arctic region")
            
            logger.warning("No Sentinel-1 products found in Arctic region")
            print("⚠️ No Sentinel-1 products found in Arctic region for the last 3 days")
            print("This could be normal depending on satellite coverage patterns")
        
    except Exception as e:
        error_msg = f"Collection failed: {str(e)}"
        logger.error(error_msg)
        collection_log['status'] = 'error'
        collection_log['errors'].append(error_msg)
        print(f"❌ Collection failed: {e}")
    
    # Save collection log
    log_file = output_dir / f"collection_log_{timestamp}.json"
    with open(log_file, 'w') as f:
        json.dump(collection_log, f, indent=2)
    
    print(f"\n📋 Collection log: {log_file}")
    print(f"🔍 Status: {collection_log['status']}")
    
    # Show download statistics if available
    try:
        stats = collector.get_download_statistics()
        if stats['total_products'] > 0:
            print(f"\n📊 Download Statistics:")
            print(f"   Total products downloaded: {stats['total_products']}")
            print(f"   Total size: {stats['total_size_gb']:.2f} GB")
    except:
        pass

if __name__ == "__main__":
    main()