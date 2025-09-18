#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Simplified Cable Monitoring
Unified cable monitoring system (replacing basic/advanced split).
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from geopy.distance import geodesic
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class CableMonitor:
    """
    Simplified unified cable monitoring system.
    Replaces both basic and advanced cable monitor classes.
    """
    
    def __init__(self, proximity_threshold_km: float = 5.0):
        """
        Initialize cable monitor.
        
        Args:
            proximity_threshold_km: Alert distance from cables in kilometers
        """
        self.proximity_threshold = proximity_threshold_km
        self.cables = self._load_arctic_cables()
        
        logger.info(f"CableMonitor initialized: {len(self.cables)} cables, {proximity_threshold_km}km threshold")
    
    def _load_arctic_cables(self) -> List[Dict]:
        """Load Arctic submarine cable data"""
        cables = [
            {
                'name': 'Svalbard Underwater Cable System (SUCS)',
                'id': 'SUCS',
                'route': [
                    (78.22, 15.63),  # Longyearbyen
                    (77.50, 16.00),  # Mid-point
                    (71.17, 25.78)   # Hammerfest, Norway
                ],
                'type': 'power_fiber',
                'critical': True
            },
            {
                'name': 'Longyearbyen-Barentsburg Cable',
                'id': 'LYB-BAR',
                'route': [
                    (78.22, 15.63),  # Longyearbyen
                    (78.065, 14.233) # Barentsburg
                ],
                'type': 'fiber',
                'critical': False
            },
            {
                'name': 'Arctic Connect (Planned)',
                'id': 'ARCTIC-CONNECT',
                'route': [
                    (71.17, 25.78),  # Hammerfest
                    (74.0, 30.0),    # Bear Island area
                    (78.22, 15.63),  # Svalbard
                    (81.0, 20.0),    # North of Svalbard
                ],
                'type': 'fiber',
                'critical': True,
                'status': 'planned'
            },
            {
                'name': 'Murmansk-Svalbard Research Link',
                'id': 'MSR-LINK',
                'route': [
                    (68.97, 33.08),  # Murmansk
                    (74.5, 35.0),    # Mid Barents Sea
                    (78.22, 15.63)   # Longyearbyen
                ],
                'type': 'research',
                'critical': False
            }
        ]
        
        return cables
    
    def check_vessel_cable_proximity(self, vessels: List[Dict]) -> List[Dict]:
        """
        Check vessels for proximity to submarine cables (simplified).
        
        Args:
            vessels: List of vessel positions
            
        Returns:
            List of vessels with cable proximity information added
        """
        if not vessels:
            return []
        
        logger.info(f"Checking {len(vessels)} vessels for cable proximity")
        
        vessels_with_cable_info = []
        
        for vessel in vessels:
            try:
                vessel_lat = vessel['latitude']
                vessel_lon = vessel['longitude']
                
                # Initialize cable proximity fields
                vessel_info = vessel.copy()
                vessel_info.update({
                    'near_cable': False,
                    'closest_cable': None,
                    'distance_to_cable_km': float('inf'),
                    'cable_alerts': []
                })
                
                # Check proximity to each cable
                for cable in self.cables:
                    min_distance_km = self._calculate_distance_to_cable(
                        vessel_lat, vessel_lon, cable
                    )
                    
                    # Update closest cable info
                    if min_distance_km < vessel_info['distance_to_cable_km']:
                        vessel_info['distance_to_cable_km'] = min_distance_km
                        vessel_info['closest_cable'] = cable['name']
                    
                    # Check if within alert threshold
                    if min_distance_km <= self.proximity_threshold:
                        vessel_info['near_cable'] = True
                        
                        alert_level = self._get_alert_level(min_distance_km, cable)
                        alert = {
                            'cable_name': cable['name'],
                            'cable_id': cable['id'],
                            'distance_km': min_distance_km,
                            'alert_level': alert_level,
                            'timestamp': datetime.now().isoformat()
                        }
                        vessel_info['cable_alerts'].append(alert)
                
                vessels_with_cable_info.append(vessel_info)
                
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Skipping malformed vessel data: {e}")
                continue
        
        near_cable_count = sum(1 for v in vessels_with_cable_info if v['near_cable'])
        logger.info(f"Found {near_cable_count} vessels near cables")
        
        return vessels_with_cable_info
    
    def _calculate_distance_to_cable(self, lat: float, lon: float, cable: Dict) -> float:
        """
        Calculate minimum distance from point to cable route using geodesic calculation.
        
        Args:
            lat: Vessel latitude
            lon: Vessel longitude
            cable: Cable information with route
            
        Returns:
            Minimum distance to cable in kilometers
        """
        min_distance_km = float('inf')
        
        # Calculate distance to each cable segment
        route = cable['route']
        for i in range(len(route) - 1):
            seg_start = route[i]
            seg_end = route[i + 1]
            
            # Distance to segment endpoints using geodesic calculation
            dist_start = geodesic((lat, lon), seg_start).kilometers
            dist_end = geodesic((lat, lon), seg_end).kilometers
            
            # Simple approximation: use minimum distance to endpoints
            # In production, would calculate true point-to-line distance
            segment_min_dist = min(dist_start, dist_end)
            min_distance_km = min(min_distance_km, segment_min_dist)
        
        return min_distance_km
    
    def _get_alert_level(self, distance_km: float, cable: Dict) -> str:
        """
        Get alert level based on distance and cable criticality.
        
        Args:
            distance_km: Distance to cable in km
            cable: Cable information
            
        Returns:
            Alert level string
        """
        is_critical = cable.get('critical', False)
        
        if distance_km < 1.0:  # Very close
            return 'CRITICAL' if is_critical else 'HIGH'
        elif distance_km < 2.0:  # Close
            return 'HIGH' if is_critical else 'MEDIUM'
        else:  # Within monitoring zone
            return 'MEDIUM' if is_critical else 'LOW'
    
    def generate_cable_threat_report(self, vessels_with_cable_info: List[Dict]) -> Dict:
        """
        Generate simple cable threat report.
        
        Args:
            vessels_with_cable_info: Vessels with cable proximity data
            
        Returns:
            Threat report dictionary
        """
        near_cable_vessels = [v for v in vessels_with_cable_info if v['near_cable']]
        
        if not near_cable_vessels:
            return {
                'timestamp': datetime.now().isoformat(),
                'threat_level': 'LOW',
                'vessels_near_cables': 0,
                'summary': 'No vessels detected near submarine cables'
            }
        
        # Count by alert level
        critical_alerts = []
        high_alerts = []
        medium_alerts = []
        
        for vessel in near_cable_vessels:
            for alert in vessel.get('cable_alerts', []):
                if alert['alert_level'] == 'CRITICAL':
                    critical_alerts.append(alert)
                elif alert['alert_level'] == 'HIGH':
                    high_alerts.append(alert)
                else:
                    medium_alerts.append(alert)
        
        # Determine overall threat level
        if critical_alerts:
            threat_level = 'CRITICAL'
        elif high_alerts:
            threat_level = 'HIGH'
        else:
            threat_level = 'MEDIUM'
        
        return {
            'timestamp': datetime.now().isoformat(),
            'threat_level': threat_level,
            'vessels_near_cables': len(near_cable_vessels),
            'alert_counts': {
                'critical': len(critical_alerts),
                'high': len(high_alerts),
                'medium': len(medium_alerts)
            },
            'summary': f"{len(near_cable_vessels)} vessels detected near cables ({threat_level} threat level)"
        }