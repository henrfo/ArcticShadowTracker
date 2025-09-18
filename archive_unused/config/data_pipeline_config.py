#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Data Pipeline Configuration
Central configuration for data processing, storage, and quality settings.
"""

from datetime import timedelta
from typing import Dict, Any

class DataPipelineConfig:
    """Configuration settings for the data pipeline"""
    
    # Data Quality Settings
    DATA_VALIDATION = {
        'enable_validation': True,
        'coordinate_bounds': {
            'lat_min': 65.0, 'lat_max': 85.0,  # Arctic bounds
            'lon_min': -30.0, 'lon_max': 50.0
        },
        'required_fields': {
            'ais': ['mmsi', 'latitude', 'longitude', 'timestamp'],
            'sar': ['lat', 'lon', 'detection_time'],
            'threats': ['vessel_id', 'threat_level', 'latitude', 'longitude']
        }
    }
    
    # Storage Settings
    STORAGE = {
        'compression_threshold': 1000,  # Records above which to compress
        'keep_daily_files_days': 90,    # Keep daily files for 90 days
        'cumulative_dataset_days': 30,  # Rolling 30-day cumulative datasets
        'max_file_size_mb': 100,        # Max file size before splitting
        'backup_enabled': True
    }
    
    # Performance Settings
    PERFORMANCE = {
        'batch_size': 500,              # Process data in batches
        'memory_limit_mb': 512,         # Memory limit for processing
        'parallel_processing': True,    # Enable parallel processing where possible
        'cache_duration_hours': 6,      # Cache data for 6 hours
        'request_timeout_seconds': 10   # Network request timeout
    }
    
    # Data Collection Settings
    COLLECTION = {
        'ais_update_interval_minutes': 30,
        'sar_update_interval_hours': 6,
        'max_vessels_per_request': 50,
        'retry_attempts': 3,
        'retry_delay_seconds': 5
    }
    
    # Alert Thresholds
    ALERTS = {
        'data_quality_error_rate': 0.1,    # Alert if >10% data errors
        'processing_time_threshold_seconds': 300,  # Alert if processing takes >5 minutes
        'missing_data_threshold_hours': 12, # Alert if no data for 12 hours
        'disk_space_threshold_gb': 1.0      # Alert if <1GB disk space
    }
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get complete configuration as dictionary"""
        return {
            'data_validation': cls.DATA_VALIDATION,
            'storage': cls.STORAGE,
            'performance': cls.PERFORMANCE,
            'collection': cls.COLLECTION,
            'alerts': cls.ALERTS
        }
    
    @classmethod
    def is_valid_coordinate(cls, lat: float, lon: float) -> bool:
        """Check if coordinates are within valid Arctic bounds"""
        bounds = cls.DATA_VALIDATION['coordinate_bounds']
        return (bounds['lat_min'] <= lat <= bounds['lat_max'] and 
                bounds['lon_min'] <= lon <= bounds['lon_max'])
    
    @classmethod
    def should_compress(cls, record_count: int) -> bool:
        """Check if data should be compressed based on size"""
        return record_count >= cls.STORAGE['compression_threshold']
    
    @classmethod
    def get_retention_cutoff(cls) -> 'datetime':
        """Get cutoff date for file retention"""
        from datetime import datetime
        return datetime.now() - timedelta(days=cls.STORAGE['keep_daily_files_days'])