#!/usr/bin/env python3
"""
Enhanced Arctic AIS Collector - Dual Source Integration
Combines free aisstream.io data with official BarentsWatch Norwegian Arctic data
for comprehensive Arctic maritime surveillance.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import concurrent.futures

from .free_ais_collector import FreeArcticAISCollector
from .barentswatch_collector import BarentsWatchCollector

logger = logging.getLogger(__name__)

class EnhancedArcticAISCollector:
    """
    Enhanced Arctic AIS collector combining multiple official and free sources.
    Provides comprehensive Arctic maritime surveillance with intelligent source prioritization.
    """
    
    def __init__(self):
        """Initialize enhanced dual-source AIS collector."""
        # Initialize data collectors
        self.free_collector = FreeArcticAISCollector()
        self.barentswatch_collector = BarentsWatchCollector()
        
        # Source priority configuration
        self.source_priority = {
            'norwegian_arctic': {
                'regions': ['svalbard', 'barents_sea_west', 'barents_sea_central'],
                'primary_source': 'barentswatch',
                'backup_source': 'aisstream',
                'description': 'Norwegian Arctic waters - BarentsWatch has jurisdiction'
            },
            'international_arctic': {
                'regions': ['kola_waters', 'franz_josef', 'greenland_sea'],
                'primary_source': 'aisstream',
                'backup_source': 'barentswatch',
                'description': 'International Arctic waters - free sources preferred'
            }
        }
        
        # Geographic boundaries for source selection
        self.geographic_priorities = {
            'svalbard_zone': {
                'bbox': [5.0, 74.0, 40.0, 82.0],
                'preferred_source': 'barentswatch',
                'reason': 'Norwegian territorial waters'
            },
            'barents_norwegian': {
                'bbox': [15.0, 70.0, 45.0, 80.0],
                'preferred_source': 'barentswatch',
                'reason': 'Norwegian EEZ'
            },
            'kola_peninsula': {
                'bbox': [28.0, 66.0, 42.0, 70.0],
                'preferred_source': 'aisstream',
                'reason': 'Russian waters - free sources preferred'
            },
            'international_arctic': {
                'bbox': [-180.0, 70.0, 180.0, 90.0],
                'preferred_source': 'aisstream',
                'reason': 'International waters'
            }
        }
        
        # Data storage
        self.data_dir = Path('data/operational/daily')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Enhanced Arctic AIS collector initialized with dual-source capability")
    
    def collect_comprehensive_arctic_data(self, duration_minutes: int = 3) -> Dict[str, List[Dict]]:
        """
        Collect comprehensive Arctic AIS data from all available sources.
        
        Args:
            duration_minutes: Duration for streaming data collection
            
        Returns:
            Dictionary with separate and combined vessel data
        """
        logger.info("🌊 Collecting COMPREHENSIVE Arctic AIS data from all sources")
        
        start_time = datetime.now()
        
        # Results structure
        results = {
            'barentswatch_data': [],
            'aisstream_data': [],
            'combined_data': [],
            'collection_metadata': {
                'start_time': start_time.isoformat(),
                'duration_minutes': duration_minutes
            }
        }
        
        # Collect from both sources in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit collection tasks
            barentswatch_future = executor.submit(self._collect_barentswatch_safe)
            aisstream_future = executor.submit(self._collect_aisstream_safe, duration_minutes)
            
            # Wait for both to complete
            try:
                # Collect BarentsWatch official data
                barentswatch_vessels = barentswatch_future.result(timeout=120)
                results['barentswatch_data'] = barentswatch_vessels
                logger.info(f"BarentsWatch official: {len(barentswatch_vessels)} vessels")
                
            except Exception as e:
                logger.error(f"BarentsWatch collection failed: {e}")
                results['barentswatch_data'] = []
            
            try:
                # Collect aisstream.io data
                aisstream_vessels = aisstream_future.result(timeout=120)
                results['aisstream_data'] = aisstream_vessels
                logger.info(f"aisstream.io: {len(aisstream_vessels)} vessels")
                
            except Exception as e:
                logger.error(f"aisstream.io collection failed: {e}")
                results['aisstream_data'] = []
        
        # Intelligent merging based on geographic zones
        combined_vessels = self._intelligent_merge_sources(
            results['barentswatch_data'], 
            results['aisstream_data']
        )
        
        results['combined_data'] = combined_vessels
        results['collection_metadata'].update({
            'end_time': datetime.now().isoformat(),
            'barentswatch_count': len(results['barentswatch_data']),
            'aisstream_count': len(results['aisstream_data']),
            'combined_count': len(combined_vessels),
            'deduplication_stats': self._get_deduplication_stats(results)
        })
        
        logger.info(f"Enhanced AIS collection complete:")
        logger.info(f"  BarentsWatch (official): {len(results['barentswatch_data'])}")
        logger.info(f"  aisstream.io (free): {len(results['aisstream_data'])}")
        logger.info(f"  Combined unique: {len(combined_vessels)}")
        
        return results
    
    def collect_optimized_arctic_data(self, priority: str = 'balanced') -> List[Dict]:
        """
        Collect Arctic data with optimized source selection.
        
        Args:
            priority: 'official' (prefer BarentsWatch), 'free' (prefer aisstream), 'balanced'
            
        Returns:
            Optimized list of vessels from best available sources
        """
        logger.info(f"Collecting optimized Arctic data (priority: {priority})")
        
        if priority == 'official':
            # Prefer official BarentsWatch data
            vessels = self._collect_barentswatch_safe()
            if not vessels:
                logger.info("No BarentsWatch data, falling back to aisstream.io")
                vessels = self._collect_aisstream_safe(duration_minutes=2)
            
        elif priority == 'free':
            # Prefer free aisstream.io data
            vessels = self._collect_aisstream_safe(duration_minutes=2)
            if not vessels:
                logger.info("No aisstream.io data, falling back to BarentsWatch")
                vessels = self._collect_barentswatch_safe()
        
        else:  # balanced
            # Use comprehensive collection with intelligent merging
            all_data = self.collect_comprehensive_arctic_data(duration_minutes=2)
            vessels = all_data['combined_data']
        
        logger.info(f"Optimized collection: {len(vessels)} vessels")
        return vessels
    
    def _collect_barentswatch_safe(self) -> List[Dict]:
        """Safely collect BarentsWatch data with error handling."""
        try:
            return self.barentswatch_collector.collect_priority_areas()
        except Exception as e:
            logger.error(f"BarentsWatch safe collection failed: {e}")
            return []
    
    def _collect_aisstream_safe(self, duration_minutes: int) -> List[Dict]:
        """Safely collect aisstream.io data with error handling."""
        try:
            return self.free_collector.collect_all_free_sources(duration_minutes=duration_minutes)
        except Exception as e:
            logger.error(f"aisstream.io safe collection failed: {e}")
            return []
    
    def _intelligent_merge_sources(self, barentswatch_vessels: List[Dict], aisstream_vessels: List[Dict]) -> List[Dict]:
        """
        Intelligently merge vessels from multiple sources based on geographic zones and priorities.
        
        Args:
            barentswatch_vessels: Official Norwegian vessels
            aisstream_vessels: Free aisstream.io vessels
            
        Returns:
            Merged list with optimal source selection and deduplication
        """
        logger.info("Performing intelligent source merging...")
        
        # Step 1: Categorize vessels by geographic zone
        categorized = {
            'svalbard_barentswatch': [],
            'svalbard_aisstream': [],
            'barents_barentswatch': [],
            'barents_aisstream': [],
            'kola_aisstream': [],
            'international_aisstream': [],
            'other_barentswatch': [],
            'other_aisstream': []
        }
        
        # Categorize BarentsWatch vessels
        for vessel in barentswatch_vessels:
            zone = self._get_vessel_zone(vessel['latitude'], vessel['longitude'])
            if zone == 'svalbard_zone':
                categorized['svalbard_barentswatch'].append(vessel)
            elif zone == 'barents_norwegian':
                categorized['barents_barentswatch'].append(vessel)
            else:
                categorized['other_barentswatch'].append(vessel)
        
        # Categorize aisstream vessels
        for vessel in aisstream_vessels:
            zone = self._get_vessel_zone(vessel['latitude'], vessel['longitude'])
            if zone == 'svalbard_zone':
                categorized['svalbard_aisstream'].append(vessel)
            elif zone == 'barents_norwegian':
                categorized['barents_aisstream'].append(vessel)
            elif zone == 'kola_peninsula':
                categorized['kola_aisstream'].append(vessel)
            else:
                categorized['international_aisstream'].append(vessel)
        
        # Step 2: Apply intelligent prioritization
        merged_vessels = []
        
        # Svalbard: Prefer BarentsWatch (Norwegian waters)
        svalbard_vessels = self._merge_by_priority(
            primary=categorized['svalbard_barentswatch'],
            secondary=categorized['svalbard_aisstream'],
            zone='Svalbard'
        )
        merged_vessels.extend(svalbard_vessels)
        
        # Barents Sea (Norwegian sector): Prefer BarentsWatch
        barents_vessels = self._merge_by_priority(
            primary=categorized['barents_barentswatch'],
            secondary=categorized['barents_aisstream'],
            zone='Barents Sea Norwegian'
        )
        merged_vessels.extend(barents_vessels)
        
        # Kola Peninsula: Prefer aisstream (Russian waters)
        merged_vessels.extend(categorized['kola_aisstream'])
        
        # International: Prefer aisstream
        merged_vessels.extend(categorized['international_aisstream'])
        
        # Other areas: Include both with deduplication
        other_vessels = self._merge_by_priority(
            primary=categorized['other_barentswatch'],
            secondary=categorized['other_aisstream'],
            zone='Other Arctic'
        )
        merged_vessels.extend(other_vessels)
        
        # Step 3: Final deduplication by MMSI
        final_vessels = self._deduplicate_by_mmsi_advanced(merged_vessels)
        
        logger.info(f"Intelligent merge complete:")
        logger.info(f"  Svalbard (BarentsWatch priority): {len(svalbard_vessels)}")
        logger.info(f"  Barents Sea (BarentsWatch priority): {len(barents_vessels)}")
        logger.info(f"  Kola Peninsula (aisstream): {len(categorized['kola_aisstream'])}")
        logger.info(f"  International (aisstream): {len(categorized['international_aisstream'])}")
        logger.info(f"  Final unique vessels: {len(final_vessels)}")
        
        return final_vessels
    
    def _get_vessel_zone(self, latitude: float, longitude: float) -> Optional[str]:
        """Determine which geographic zone a vessel is in."""
        for zone_name, zone_info in self.geographic_priorities.items():
            bbox = zone_info['bbox']
            if bbox[0] <= longitude <= bbox[2] and bbox[1] <= latitude <= bbox[3]:
                return zone_name
        return None
    
    def _merge_by_priority(self, primary: List[Dict], secondary: List[Dict], zone: str) -> List[Dict]:
        """
        Merge vessels from primary and secondary sources with MMSI-based deduplication.
        Primary source takes precedence for duplicate MMSIs.
        """
        logger.debug(f"Merging {zone}: {len(primary)} primary + {len(secondary)} secondary")
        
        # Create MMSI index from primary source
        mmsi_index = {}
        result = []
        
        # Add all primary vessels
        for vessel in primary:
            mmsi = vessel.get('mmsi')
            if mmsi and mmsi != 'unknown':
                mmsi_index[mmsi] = True
            result.append(vessel)
        
        # Add secondary vessels only if MMSI not in primary
        for vessel in secondary:
            mmsi = vessel.get('mmsi')
            if not mmsi or mmsi == 'unknown' or mmsi not in mmsi_index:
                result.append(vessel)
                if mmsi and mmsi != 'unknown':
                    mmsi_index[mmsi] = True
        
        logger.debug(f"Merged {zone}: {len(result)} vessels (removed {len(primary) + len(secondary) - len(result)} duplicates)")
        return result
    
    def _deduplicate_by_mmsi_advanced(self, vessels: List[Dict]) -> List[Dict]:
        """
        Advanced MMSI deduplication with source priority handling.
        BarentsWatch (official) data takes precedence over free sources.
        """
        mmsi_dict = {}
        
        for vessel in vessels:
            mmsi = vessel.get('mmsi')
            if not mmsi or mmsi == 'unknown':
                # Keep vessels without MMSI (might be dark vessels)
                mmsi_dict[f"no_mmsi_{len(mmsi_dict)}"] = vessel
                continue
            
            if mmsi not in mmsi_dict:
                mmsi_dict[mmsi] = vessel
            else:
                # Determine which vessel to keep based on source priority
                existing = mmsi_dict[mmsi]
                current = vessel
                
                # BarentsWatch official data has highest priority
                if current.get('source') == 'barentswatch_official' and existing.get('source') != 'barentswatch_official':
                    mmsi_dict[mmsi] = current
                elif existing.get('source') == 'barentswatch_official' and current.get('source') != 'barentswatch_official':
                    # Keep existing BarentsWatch vessel
                    pass
                else:
                    # Both from same source type, keep more recent
                    try:
                        current_time = datetime.fromisoformat(current['timestamp'].replace('Z', '+00:00'))
                        existing_time = datetime.fromisoformat(existing['timestamp'].replace('Z', '+00:00'))
                        
                        if current_time > existing_time:
                            mmsi_dict[mmsi] = current
                    except:
                        # If timestamp comparison fails, keep existing
                        pass
        
        return list(mmsi_dict.values())
    
    def _get_deduplication_stats(self, results: Dict) -> Dict:
        """Calculate deduplication statistics."""
        total_original = len(results['barentswatch_data']) + len(results['aisstream_data'])
        total_combined = len(results['combined_data'])
        
        return {
            'original_total': total_original,
            'combined_total': total_combined,
            'duplicates_removed': max(0, total_original - total_combined),
            'deduplication_rate': max(0, total_original - total_combined) / max(1, total_original)
        }
    
    def save_enhanced_data(self, results: Dict[str, List[Dict]]) -> Dict[str, str]:
        """Save enhanced dual-source AIS data."""
        if not any(results.values()):
            return {}
        
        # Create today's directory
        today = datetime.now().strftime('%Y-%m-%d')
        today_dir = self.data_dir / today
        today_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%H%M%S')
        saved_files = {}
        
        # Save combined data (main output)
        if results['combined_data']:
            combined_file = f"enhanced_ais_data_{timestamp}.json"
            combined_path = today_dir / combined_file
            
            save_data = {
                'metadata': {
                    'collection_type': 'enhanced_dual_source',
                    'sources': ['BarentsWatch Official', 'aisstream.io Free'],
                    'collection_time': datetime.now().isoformat(),
                    'total_vessels': len(results['combined_data']),
                    'source_statistics': results['collection_metadata']
                },
                'vessels': results['combined_data']
            }
            
            with open(combined_path, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            # Also save as latest
            latest_combined = today_dir / "latest_enhanced_ais.json"
            with open(latest_combined, 'w') as f:
                json.dump(save_data, f, indent=2)
            
            saved_files['combined'] = str(combined_path)
        
        # Save source-specific data for analysis
        if results['barentswatch_data']:
            self.barentswatch_collector.save_barentswatch_data(results['barentswatch_data'])
            saved_files['barentswatch'] = 'saved via BarentsWatch collector'
        
        if results['aisstream_data']:
            ais_file = self.free_collector.save_free_data(results['aisstream_data'])
            saved_files['aisstream'] = ais_file
        
        logger.info(f"Enhanced AIS data saved to {len(saved_files)} files")
        return saved_files
    
    def get_source_capabilities(self) -> Dict:
        """Get information about data source capabilities."""
        return {
            'barentswatch': {
                'type': 'official_norwegian_government',
                'coverage': 'Norwegian Arctic waters (Svalbard, Barents Sea)',
                'data_quality': 'official',
                'authentication': 'OAuth2 required',
                'rate_limits': 'Government API limits apply',
                'priority_regions': ['svalbard', 'barents_sea_west']
            },
            'aisstream': {
                'type': 'free_global_ais',
                'coverage': 'Global AIS including Arctic',
                'data_quality': 'community_sourced',
                'authentication': 'Free API key required',
                'rate_limits': 'Free tier limits',
                'priority_regions': ['kola_peninsula', 'international_arctic']
            },
            'intelligent_merging': {
                'method': 'geographic_zone_priority',
                'deduplication': 'advanced_mmsi_based',
                'priority_logic': 'official_sources_preferred_in_norwegian_waters'
            }
        }

# Test function
def test_enhanced_ais_collection():
    """Test enhanced dual-source AIS collection."""
    print("🌊 Testing Enhanced Arctic AIS Collection (Dual Source)")
    print("=" * 70)
    
    collector = EnhancedArcticAISCollector()
    
    # Show source capabilities
    capabilities = collector.get_source_capabilities()
    print("📊 Data Source Capabilities:")
    for source, info in capabilities.items():
        if source != 'intelligent_merging':
            print(f"   {source.upper()}:")
            print(f"     • Type: {info['type']}")
            print(f"     • Coverage: {info['coverage']}")
            print(f"     • Quality: {info['data_quality']}")
    
    print(f"\n🧠 Intelligent Merging:")
    merging = capabilities['intelligent_merging']
    print(f"   • Method: {merging['method']}")
    print(f"   • Deduplication: {merging['deduplication']}")
    print(f"   • Priority Logic: {merging['priority_logic']}")
    
    # Test comprehensive collection
    print(f"\n🎯 Testing comprehensive dual-source collection...")
    results = collector.collect_comprehensive_arctic_data(duration_minutes=1)
    
    print(f"\n📊 Collection Results:")
    metadata = results['collection_metadata']
    print(f"   BarentsWatch Official: {metadata['barentswatch_count']} vessels")
    print(f"   aisstream.io Free: {metadata['aisstream_count']} vessels")
    print(f"   Combined Unique: {metadata['combined_count']} vessels")
    
    if metadata.get('deduplication_stats'):
        dedup = metadata['deduplication_stats']
        print(f"   Duplicates Removed: {dedup['duplicates_removed']}")
        print(f"   Deduplication Rate: {dedup['deduplication_rate']:.1%}")
    
    # Show sample vessels from combined data
    if results['combined_data']:
        print(f"\n🚢 Sample Enhanced Arctic Vessels:")
        for vessel in results['combined_data'][:5]:
            print(f"   • {vessel['name']} (MMSI: {vessel['mmsi']})")
            print(f"     Position: {vessel['latitude']:.3f}°N, {vessel['longitude']:.3f}°E")
            print(f"     Source: {vessel['source']} | Authority: {vessel.get('authority', 'N/A')}")
        
        # Save enhanced data
        saved_files = collector.save_enhanced_data(results)
        print(f"\n💾 Enhanced data saved:")
        for data_type, file_path in saved_files.items():
            print(f"   {data_type}: {file_path}")
    
    else:
        print(f"\n⚠️ No vessels collected from any source")
        print("Check API configurations and network connectivity")

if __name__ == "__main__":
    test_enhanced_ais_collection()