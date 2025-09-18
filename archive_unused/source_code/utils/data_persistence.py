#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Data Persistence Module
Simple and practical data saving for operational surveillance.
"""

import os
import json
import pandas as pd
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class DataPersistence:
    """
    Simple data persistence for Arctic surveillance operations.
    Saves AIS data, SAR detections, and threat assessments with timestamps.
    """
    
    def __init__(self, base_data_dir: str = None):
        """
        Initialize data persistence manager.
        
        Args:
            base_data_dir: Base directory for data storage (defaults to project/data)
        """
        if base_data_dir is None:
            self.base_dir = Path(__file__).parent.parent / 'data' / 'operational'
        else:
            self.base_dir = Path(base_data_dir)
        
        # Create directory structure
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / 'daily').mkdir(exist_ok=True)
        (self.base_dir / 'historical').mkdir(exist_ok=True)
        (self.base_dir / 'latest').mkdir(exist_ok=True)
        
        logger.info(f"DataPersistence initialized: {self.base_dir}")
    
    def _validate_data_quality(self, data: List[Dict], data_type: str) -> Tuple[List[Dict], Dict]:
        """
        Validate and clean input data, return cleaned data and quality report.
        
        Args:
            data: Raw data list
            data_type: Type of data ('ais', 'sar', 'threats')
            
        Returns:
            Tuple of (cleaned_data, quality_report)
        """
        if not data:
            return [], {'status': 'EMPTY', 'records_processed': 0, 'records_valid': 0}
        
        cleaned_data = []
        errors = []
        
        required_fields = {
            'ais': ['mmsi', 'latitude', 'longitude', 'timestamp'],
            'sar': ['lat', 'lon', 'detection_time'],
            'threats': ['vessel_id', 'threat_level', 'latitude', 'longitude']
        }
        
        required = required_fields.get(data_type, [])
        
        for i, record in enumerate(data):
            try:
                # Check required fields
                missing_fields = [field for field in required if field not in record or record[field] is None]
                if missing_fields:
                    errors.append(f"Record {i}: missing fields {missing_fields}")
                    continue
                
                # Validate coordinates for all types
                lat_field = 'latitude' if 'latitude' in record else 'lat'
                lon_field = 'longitude' if 'longitude' in record else 'lon'
                
                if lat_field in record and lon_field in record:
                    lat, lon = float(record[lat_field]), float(record[lon_field])
                    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                        errors.append(f"Record {i}: invalid coordinates ({lat}, {lon})")
                        continue
                
                # Add validation timestamp
                record['validation_timestamp'] = datetime.now().isoformat()
                cleaned_data.append(record)
                
            except (ValueError, TypeError) as e:
                errors.append(f"Record {i}: validation error - {e}")
                continue
        
        quality_report = {
            'status': 'PROCESSED',
            'records_processed': len(data),
            'records_valid': len(cleaned_data),
            'records_rejected': len(data) - len(cleaned_data),
            'error_rate': (len(data) - len(cleaned_data)) / len(data) if data else 0,
            'errors': errors[:10]  # Keep first 10 errors for debugging
        }
        
        if errors:
            logger.warning(f"{data_type} validation: {len(errors)} errors found")
        
        return cleaned_data, quality_report
    
    def _save_json_compressed(self, data: Any, filepath: Path, compress_threshold: int = 1000) -> str:
        """
        Save JSON data with optional compression for large datasets.
        
        Args:
            data: Data to save
            filepath: File path to save to
            compress_threshold: Number of records above which to compress
            
        Returns:
            Path to saved file
        """
        data_size = len(data) if isinstance(data, list) else 1
        
        if data_size > compress_threshold:
            # Save compressed for large datasets
            compressed_path = filepath.with_suffix('.json.gz')
            with gzip.open(compressed_path, 'wt', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {data_size} records (compressed) to {compressed_path.name}")
            return str(compressed_path)
        else:
            # Save uncompressed for small datasets
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {data_size} records to {filepath.name}")
            return str(filepath)
    
    def save_daily_data(self, 
                       ais_data: List[Dict] = None,
                       sar_detections: List[Dict] = None, 
                       threats: List[Dict] = None,
                       mission_summary: Dict = None,
                       date_str: str = None) -> Dict[str, str]:
        """
        Save daily operational data with timestamped folder structure.
        
        Args:
            ais_data: List of AIS vessel records
            sar_detections: List of SAR detection records
            threats: List of threat assessment records
            mission_summary: Mission summary statistics
            date_str: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with saved file paths
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        timestamp = datetime.now().strftime('%H%M%S')
        
        # Create daily directory
        daily_dir = self.base_dir / 'daily' / date_str
        daily_dir.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        quality_reports = {}
        
        # Validate and save AIS data
        if ais_data:
            ais_data, ais_quality = self._validate_data_quality(ais_data, 'ais')
            quality_reports['ais'] = ais_quality
            # Save JSON first (more memory efficient for raw data)
            ais_json = daily_dir / f'ais_data_{timestamp}.json'
            with open(ais_json, 'w') as f:
                json.dump(ais_data, f, indent=2)
            
            # Only create DataFrame if CSV is needed for analysis
            try:
                ais_df = pd.DataFrame(ais_data)
                ais_file = daily_dir / f'ais_data_{timestamp}.csv'
                ais_df.to_csv(ais_file, index=False)
                saved_files['ais'] = str(ais_file)
            except Exception as e:
                logger.warning(f"CSV creation failed for AIS data: {e}")
                saved_files['ais'] = str(ais_json)
            
            logger.info(f"Saved {len(ais_data)} AIS records to {ais_json.name}")
        
        # Save SAR detections
        if sar_detections:
            sar_file = daily_dir / f'sar_detections_{timestamp}.csv'
            sar_df = pd.DataFrame(sar_detections)
            sar_df.to_csv(sar_file, index=False)
            saved_files['sar'] = str(sar_file)
            
            sar_json = daily_dir / f'sar_detections_{timestamp}.json'
            with open(sar_json, 'w') as f:
                json.dump(sar_detections, f, indent=2)
            
            logger.info(f"Saved {len(sar_detections)} SAR detections to {sar_file.name}")
        
        # Save threats
        if threats:
            threats_file = daily_dir / f'threats_{timestamp}.csv'
            threats_df = pd.DataFrame(threats)
            threats_df.to_csv(threats_file, index=False)
            saved_files['threats'] = str(threats_file)
            
            threats_json = daily_dir / f'threats_{timestamp}.json'
            with open(threats_json, 'w') as f:
                json.dump(threats, f, indent=2)
            
            logger.info(f"Saved {len(threats)} threats to {threats_file.name}")
        
        # Save mission summary
        if mission_summary:
            summary_file = daily_dir / f'mission_summary_{timestamp}.json'
            
            # Add metadata
            enhanced_summary = {
                'timestamp': datetime.now().isoformat(),
                'date': date_str,
                'data_counts': {
                    'ais_vessels': len(ais_data) if ais_data else 0,
                    'sar_detections': len(sar_detections) if sar_detections else 0,
                    'threats_detected': len(threats) if threats else 0
                },
                'mission_data': mission_summary
            }
            
            with open(summary_file, 'w') as f:
                json.dump(enhanced_summary, f, indent=2)
            
            saved_files['summary'] = str(summary_file)
            logger.info(f"Saved mission summary to {summary_file.name}")
        
        # Update latest data symlinks/copies
        self._update_latest_data(ais_data, sar_detections, threats, mission_summary)
        
        return saved_files
    
    def load_daily_data(self, date_str: str = None) -> Dict[str, Any]:
        """
        Load data for a specific date.
        
        Args:
            date_str: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with loaded data
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        daily_dir = self.base_dir / 'daily' / date_str
        
        if not daily_dir.exists():
            logger.warning(f"No data found for date: {date_str}")
            return {}
        
        data = {}
        
        # Load latest files for the day
        ais_files = sorted(daily_dir.glob('ais_data_*.json'))
        if ais_files:
            with open(ais_files[-1], 'r') as f:
                data['ais_data'] = json.load(f)
        
        sar_files = sorted(daily_dir.glob('sar_detections_*.json'))
        if sar_files:
            with open(sar_files[-1], 'r') as f:
                data['sar_detections'] = json.load(f)
        
        threat_files = sorted(daily_dir.glob('threats_*.json'))
        if threat_files:
            with open(threat_files[-1], 'r') as f:
                data['threats'] = json.load(f)
        
        summary_files = sorted(daily_dir.glob('mission_summary_*.json'))
        if summary_files:
            with open(summary_files[-1], 'r') as f:
                data['mission_summary'] = json.load(f)
        
        logger.info(f"Loaded data for {date_str}: {list(data.keys())}")
        return data
    
    def get_historical_summary(self, days_back: int = 7) -> pd.DataFrame:
        """
        Get historical summary for the last N days.
        
        Args:
            days_back: Number of days to include in summary
            
        Returns:
            DataFrame with daily statistics
        """
        summary_data = []
        
        for i in range(days_back):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            daily_data = self.load_daily_data(date_str)
            if daily_data and 'mission_summary' in daily_data:
                summary = daily_data['mission_summary']
                
                row = {
                    'date': date_str,
                    'ais_vessels': summary.get('data_counts', {}).get('ais_vessels', 0),
                    'sar_detections': summary.get('data_counts', {}).get('sar_detections', 0),
                    'threats_detected': summary.get('data_counts', {}).get('threats_detected', 0),
                    'critical_threats': summary.get('mission_data', {}).get('summary', {}).get('critical_threats', 0),
                    'high_threats': summary.get('mission_data', {}).get('summary', {}).get('high_threats', 0),
                    'dark_vessels': summary.get('mission_data', {}).get('summary', {}).get('dark_vessels', 0)
                }
                summary_data.append(row)
        
        if not summary_data:
            logger.warning("No historical data found")
            return pd.DataFrame()
        
        df = pd.DataFrame(summary_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        logger.info(f"Generated historical summary: {len(df)} days")
        return df
    
    def _update_latest_data(self, ais_data, sar_detections, threats, mission_summary):
        """Update latest data files for quick access"""
        latest_dir = self.base_dir / 'latest'
        
        try:
            if ais_data:
                with open(latest_dir / 'ais_latest.json', 'w') as f:
                    json.dump(ais_data, f, indent=2)
            
            if sar_detections:
                with open(latest_dir / 'sar_latest.json', 'w') as f:
                    json.dump(sar_detections, f, indent=2)
            
            if threats:
                with open(latest_dir / 'threats_latest.json', 'w') as f:
                    json.dump(threats, f, indent=2)
            
            if mission_summary:
                with open(latest_dir / 'summary_latest.json', 'w') as f:
                    json.dump(mission_summary, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to update latest data: {e}")
    
    def create_cumulative_dataset(self, data_type: str = 'threats', days_back: int = 30) -> pd.DataFrame:
        """
        Create cumulative dataset from historical data.
        
        Args:
            data_type: Type of data ('ais', 'sar', 'threats')
            days_back: Number of days to include
            
        Returns:
            Combined DataFrame from multiple days
        """
        all_data = []
        
        for i in range(days_back):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            
            daily_data = self.load_daily_data(date_str)
            if daily_data and data_type in daily_data:
                for record in daily_data[data_type]:
                    record['collection_date'] = date_str
                    all_data.append(record)
        
        if not all_data:
            logger.warning(f"No cumulative {data_type} data found")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        logger.info(f"Created cumulative {data_type} dataset: {len(df)} records over {days_back} days")
        
        return df
    
    def generate_daily_summary_report(self, date_str: str = None) -> Dict:
        """
        Generate a comprehensive daily summary report.
        
        Args:
            date_str: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with comprehensive daily statistics
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        daily_data = self.load_daily_data(date_str)
        
        if not daily_data:
            return {
                'date': date_str,
                'status': 'NO_DATA',
                'message': f'No surveillance data available for {date_str}'
            }
        
        # Calculate statistics
        ais_data = daily_data.get('ais_data', [])
        sar_detections = daily_data.get('sar_detections', [])
        threats = daily_data.get('threats', [])
        
        # Vessel type breakdown
        vessel_types = {}
        for vessel in ais_data:
            vtype = vessel.get('type', 'Unknown')
            vessel_types[vtype] = vessel_types.get(vtype, 0) + 1
        
        # Threat level breakdown
        threat_levels = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        for threat in threats:
            level = threat.get('threat_level', 'LOW')
            threat_levels[level] = threat_levels.get(level, 0) + 1
        
        # Geographic distribution (simple binning)
        lat_bins = {'Arctic_North': 0, 'Arctic_Central': 0, 'Arctic_South': 0}
        for vessel in ais_data:
            lat = vessel.get('latitude', 0)
            if lat > 80:
                lat_bins['Arctic_North'] += 1
            elif lat > 75:
                lat_bins['Arctic_Central'] += 1
            else:
                lat_bins['Arctic_South'] += 1
        
        report = {
            'date': date_str,
            'status': 'SUCCESS',
            'timestamp': datetime.now().isoformat(),
            'vessel_statistics': {
                'total_ais_vessels': len(ais_data),
                'total_sar_detections': len(sar_detections),
                'vessel_types': vessel_types,
                'geographic_distribution': lat_bins
            },
            'threat_analysis': {
                'total_threats': len(threats),
                'threat_levels': threat_levels,
                'max_threat_level': max(threat_levels.keys()) if any(threat_levels.values()) else 'NONE'
            },
            'surveillance_quality': {
                'ais_coverage': 'Good' if len(ais_data) > 5 else 'Limited',
                'sar_coverage': 'Good' if len(sar_detections) > 3 else 'Limited',
                'data_completeness': len([d for d in [ais_data, sar_detections, threats] if d]) / 3
            }
        }
        
        logger.info(f"Generated daily summary for {date_str}")
        return report