#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Simplified Vessel Detection
Unified vessel detection system (replacing basic/advanced split).
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from geopy.distance import geodesic
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class VesselDetector:
    """
    Simplified unified vessel detection system.
    Replaces both basic and advanced detection classes.
    """
    
    def __init__(self, 
                 matching_threshold_meters: float = 1000,
                 enable_ml_filtering: bool = True,
                 confidence_threshold: float = 0.6):
        """
        Initialize vessel detector with simple configuration.
        
        Args:
            matching_threshold_meters: Distance threshold for SAR-AIS matching
            enable_ml_filtering: Use ML for false positive filtering
            confidence_threshold: Minimum confidence for detections
        """
        self.matching_threshold = matching_threshold_meters
        self.enable_ml_filtering = enable_ml_filtering
        self.confidence_threshold = confidence_threshold
        
        logger.info(f"VesselDetector initialized: threshold={matching_threshold_meters}m, ML={enable_ml_filtering}")
    
    def detect_vessels_in_sar(self, sar_image_path: str, roi_bounds: Optional[tuple] = None) -> List[Dict]:
        """
        Detect vessels in SAR imagery (simplified).
        
        Args:
            sar_image_path: Path to SAR image file
            roi_bounds: Optional region of interest (south, west, north, east)
            
        Returns:
            List of vessel detections with positions and confidence
        """
        try:
            logger.info(f"Processing SAR image: {sar_image_path}")
            
            # For placeholder files, simulate realistic detections
            if sar_image_path.endswith('.placeholder'):
                return self._simulate_sar_detections(sar_image_path, roi_bounds)
            
            # For real SAR files, would implement actual detection here
            # Using CFAR detection algorithms, speckle filtering, etc.
            logger.warning("Real SAR processing not implemented yet")
            return []
            
        except Exception as e:
            logger.error(f"SAR detection failed: {e}")
            return []
    
    def find_dark_vessels(self, sar_detections: List[Dict], ais_data: List[Dict], 
                         time_tolerance_minutes: int = 30) -> List[Dict]:
        """
        Find dark vessels by correlating SAR detections with AIS data.
        
        Args:
            sar_detections: List of SAR vessel detections
            ais_data: List of AIS vessel positions
            time_tolerance_minutes: Time window for correlation
            
        Returns:
            List of dark vessel detections (SAR detections without matching AIS)
        """
        if not sar_detections:
            logger.info("No SAR detections to correlate")
            return []
            
        if not ais_data:
            logger.warning("No AIS data - all SAR detections considered dark vessels")
            return sar_detections
        
        logger.info(f"Correlating {len(sar_detections)} SAR detections with {len(ais_data)} AIS positions")
        
        dark_vessels = []
        
        for sar_detection in sar_detections:
            if not self._has_matching_ais(sar_detection, ais_data, time_tolerance_minutes):
                # This is a dark vessel - add additional metadata
                dark_vessel = sar_detection.copy()
                dark_vessel.update({
                    'dark_vessel': True,
                    'risk_score': self._calculate_simple_risk_score(dark_vessel),
                    'analysis_timestamp': datetime.now().isoformat()
                })
                dark_vessels.append(dark_vessel)
        
        logger.info(f"Found {len(dark_vessels)} dark vessels")
        return dark_vessels
    
    def _simulate_sar_detections(self, sar_file: str, roi_bounds: tuple) -> List[Dict]:
        """Simulate SAR detections for testing with placeholder files"""
        import json
        import random
        import os
        
        try:
            # Load metadata from placeholder file
            with open(sar_file, 'r') as f:
                metadata = json.load(f)
            
            center_lat, center_lon = metadata.get('center_location', (78.0, 15.0))
            
            # Generate realistic detections around the area
            detections = []
            num_detections = random.randint(2, 6)
            
            for i in range(num_detections):
                detection = {
                    'detection_id': f"SAR_{os.path.basename(sar_file).split('.')[0]}_{i+1}",
                    'lat': center_lat + random.uniform(-0.3, 0.3),
                    'lon': center_lon + random.uniform(-0.5, 0.5),
                    'confidence': random.uniform(0.65, 0.95),
                    'detection_time': datetime.now().isoformat(),
                    'source_file': os.path.basename(sar_file),
                    'vessel_length_estimate': random.uniform(40, 150)
                }
                detections.append(detection)
            
            return detections
            
        except Exception as e:
            logger.error(f"Error simulating SAR detections: {e}")
            return []
    
    def _has_matching_ais(self, sar_detection: Dict, ais_data: List[Dict], 
                         time_tolerance_minutes: int) -> bool:
        """Check if SAR detection has a matching AIS signal"""
        sar_lat = sar_detection['lat']
        sar_lon = sar_detection['lon']
        sar_time = datetime.fromisoformat(sar_detection['detection_time'].replace('Z', ''))
        
        for ais_vessel in ais_data:
            try:
                ais_lat = float(ais_vessel['lat'])
                ais_lon = float(ais_vessel['lon'])
                ais_time = datetime.fromisoformat(ais_vessel['timestamp'].replace('Z', ''))
                
                # Check time difference
                time_diff = abs((sar_time - ais_time).total_seconds() / 60)  # minutes
                if time_diff > time_tolerance_minutes:
                    continue
                
                # Check spatial distance
                distance_m = geodesic((sar_lat, sar_lon), (ais_lat, ais_lon)).meters
                if distance_m <= self.matching_threshold:
                    return True  # Found matching AIS signal
                    
            except (ValueError, KeyError, TypeError):
                continue  # Skip malformed AIS records
        
        return False  # No matching AIS signal found
    
    def _calculate_simple_risk_score(self, vessel_data: Dict) -> float:
        """
        Simple additive risk scoring (replacing complex weighted system).
        
        Args:
            vessel_data: Vessel detection data
            
        Returns:
            Risk score between 0.0 and 1.0
        """
        risk = 0.0
        
        # Base risk for being a dark vessel
        risk += 0.4
        
        # Higher risk for high confidence detections
        confidence = vessel_data.get('confidence', 0.5)
        if confidence > 0.8:
            risk += 0.2
        
        # Size-based risk (larger vessels more concerning)
        vessel_length = vessel_data.get('vessel_length_estimate', 50)
        if vessel_length > 100:  # Large vessel
            risk += 0.2
        elif vessel_length > 200:  # Very large vessel
            risk += 0.3
        
        # Location-based risk (would be enhanced with cable proximity)
        # This would be calculated by CableMonitor
        
        return min(risk, 1.0)  # Cap at 1.0