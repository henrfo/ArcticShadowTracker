"""
Cable monitoring module for ArcticShadowTracker.

This module implements specialized monitoring for submarine cable infrastructure,
detecting vessels that may pose a threat to critical undersea cables.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from geopy.distance import geodesic
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import transform
import logging
from typing import List, Dict, Tuple, Optional


class CableMonitor:
    """
    Monitor vessels near submarine cables and detect potential threats.
    """
    
    def __init__(self, proximity_threshold_km=5, loitering_threshold_hours=2):
        """
        Initialize cable monitoring system.
        
        Args:
            proximity_threshold_km (float): Alert distance from cables
            loitering_threshold_hours (float): Time threshold for loitering detection
        """
        self.proximity_threshold = proximity_threshold_km
        self.loitering_threshold = loitering_threshold_hours
        self.logger = logging.getLogger(__name__)
        
        # Initialize cable database
        self.cables = self._load_cable_data()
        self.protection_zones = self._create_protection_zones()
        
    def _load_cable_data(self) -> List[Dict]:
        """
        Load submarine cable data for Arctic region.
        
        Returns:
            List[Dict]: Cable information including routes and specifications
        """
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
                'capacity': '200MW + 40Gbps',
                'owner': 'Store Norske',
                'year_installed': 2004,
                'depth_range': (50, 2600),
                'critical_sections': [
                    {'start': (78.22, 15.63), 'end': (78.0, 15.8), 'reason': 'landing_site'},
                    {'start': (71.17, 25.78), 'end': (71.5, 25.5), 'reason': 'landing_site'}
                ]
            },
            {
                'name': 'Longyearbyen-Barentsburg Cable',
                'id': 'LYB-BAR',
                'route': [
                    (78.22, 15.63),  # Longyearbyen
                    (78.065, 14.233) # Barentsburg
                ],
                'type': 'fiber',
                'capacity': '10Gbps',
                'owner': 'Telenor Svalbard',
                'year_installed': 2015,
                'depth_range': (10, 100),
                'critical_sections': [
                    {'start': (78.22, 15.63), 'end': (78.20, 15.60), 'reason': 'shallow_water'},
                    {'start': (78.065, 14.233), 'end': (78.07, 14.25), 'reason': 'shallow_water'}
                ]
            },
            {
                'name': 'Arctic Connect (Planned)',
                'id': 'ARCTIC-CONNECT',
                'route': [
                    (71.17, 25.78),  # Hammerfest
                    (74.0, 30.0),    # Bear Island area
                    (78.22, 15.63),  # Svalbard
                    (81.0, 20.0),    # North of Svalbard
                    (85.0, 0.0)      # North Pole route
                ],
                'type': 'fiber',
                'capacity': '400Gbps',
                'owner': 'Planned - Consortium',
                'year_installed': 2026,  # Planned
                'depth_range': (100, 4000),
                'status': 'planned'
            },
            {
                'name': 'Murmansk-Svalbard Research Link',
                'id': 'MURMANSK-SVB',
                'route': [
                    (68.97, 33.05),  # Murmansk
                    (72.0, 35.0),    # Barents Sea
                    (76.0, 25.0),    # Central Barents
                    (78.22, 15.63)   # Longyearbyen
                ],
                'type': 'research_fiber',
                'capacity': '100Gbps',
                'owner': 'Arctic Research Consortium',
                'year_installed': 2020,
                'depth_range': (200, 3000),
                'sensitivity': 'high'  # Research traffic
            }
        ]
        
        return cables
    
    def _create_protection_zones(self) -> Dict[str, Polygon]:
        """
        Create protection zones around cables.
        
        Returns:
            Dict[str, Polygon]: Protection zones for each cable
        """
        protection_zones = {}
        
        for cable in self.cables:
            cable_line = LineString(cable['route'])
            
            # Create buffer around cable (in degrees, approximate)
            # 1 km ≈ 0.009 degrees at Arctic latitudes
            buffer_degrees = self.proximity_threshold / 111.0
            
            protection_zone = cable_line.buffer(buffer_degrees)
            protection_zones[cable['id']] = protection_zone
        
        return protection_zones
    
    def check_vessel_cable_proximity(self, vessels: List[Dict]) -> List[Dict]:
        """
        Check if vessels are near submarine cables.
        
        Args:
            vessels (List[Dict]): List of vessel positions
            
        Returns:
            List[Dict]: Vessels with cable proximity information
        """
        vessels_with_cable_info = []
        
        for vessel in vessels:
            vessel_point = Point(vessel['longitude'], vessel['latitude'])
            vessel_cable_info = vessel.copy()
            
            # Initialize cable proximity fields
            vessel_cable_info['near_cable'] = False
            vessel_cable_info['closest_cable'] = None
            vessel_cable_info['distance_to_cable_km'] = float('inf')
            vessel_cable_info['cable_alerts'] = []
            
            # Check proximity to each cable
            for cable in self.cables:
                cable_line = LineString(cable['route'])
                
                # Calculate minimum distance to cable
                distance_degrees = vessel_point.distance(cable_line)
                distance_km = distance_degrees * 111.0  # Approximate conversion
                
                if distance_km < vessel_cable_info['distance_to_cable_km']:
                    vessel_cable_info['distance_to_cable_km'] = distance_km
                    vessel_cable_info['closest_cable'] = cable['name']
                
                # Check if within alert threshold
                if distance_km <= self.proximity_threshold:
                    vessel_cable_info['near_cable'] = True
                    
                    alert = {
                        'cable_name': cable['name'],
                        'cable_id': cable['id'],
                        'distance_km': distance_km,
                        'cable_type': cable['type'],
                        'alert_level': self._calculate_alert_level(distance_km, cable),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    vessel_cable_info['cable_alerts'].append(alert)
            
            vessels_with_cable_info.append(vessel_cable_info)
        
        return vessels_with_cable_info
    
    def _calculate_alert_level(self, distance_km: float, cable: Dict) -> str:
        """
        Calculate alert level based on distance and cable importance.
        
        Args:
            distance_km (float): Distance to cable
            cable (Dict): Cable information
            
        Returns:
            str: Alert level (LOW, MEDIUM, HIGH, CRITICAL)
        """
        # Base alert level on distance
        if distance_km <= 1:
            base_level = 'CRITICAL'
        elif distance_km <= 2:
            base_level = 'HIGH'
        elif distance_km <= 3:
            base_level = 'MEDIUM'
        else:
            base_level = 'LOW'
        
        # Upgrade alert for sensitive cables
        if cable.get('sensitivity') == 'high':
            if base_level == 'LOW':
                base_level = 'MEDIUM'
            elif base_level == 'MEDIUM':
                base_level = 'HIGH'
        
        # Upgrade alert for power cables
        if 'power' in cable.get('type', ''):
            if base_level == 'LOW':
                base_level = 'MEDIUM'
        
        return base_level
    
    def detect_loitering_near_cables(self, vessel_tracks: Dict[str, List[Dict]]) -> List[Dict]:
        """
        Detect vessels loitering near submarine cables.
        
        Args:
            vessel_tracks (Dict): Vessel movement histories
            
        Returns:
            List[Dict]: Loitering incidents near cables
        """
        loitering_incidents = []
        
        for vessel_id, track in vessel_tracks.items():
            if len(track) < 2:
                continue
            
            # Group consecutive positions near cables
            cable_sessions = self._identify_cable_sessions(track)
            
            for session in cable_sessions:
                duration_hours = self._calculate_session_duration(session)
                
                if duration_hours >= self.loitering_threshold:
                    # Calculate average position during loitering
                    avg_lat = np.mean([pos['latitude'] for pos in session])
                    avg_lon = np.mean([pos['longitude'] for pos in session])
                    
                    # Find which cable they were near
                    closest_cable = self._find_closest_cable(avg_lat, avg_lon)
                    
                    incident = {
                        'vessel_id': vessel_id,
                        'incident_type': 'loitering_near_cable',
                        'start_time': session[0]['timestamp'],
                        'end_time': session[-1]['timestamp'],
                        'duration_hours': duration_hours,
                        'average_position': {'lat': avg_lat, 'lon': avg_lon},
                        'cable_name': closest_cable['name'],
                        'cable_id': closest_cable['id'],
                        'positions_count': len(session),
                        'max_distance_from_cable': max([
                            self._distance_to_cable(pos['latitude'], pos['longitude'], closest_cable)
                            for pos in session
                        ]),
                        'min_distance_from_cable': min([
                            self._distance_to_cable(pos['latitude'], pos['longitude'], closest_cable)
                            for pos in session
                        ]),
                        'risk_score': self._calculate_loitering_risk(session, closest_cable)
                    }
                    
                    loitering_incidents.append(incident)
        
        return loitering_incidents
    
    def _identify_cable_sessions(self, track: List[Dict]) -> List[List[Dict]]:
        """
        Identify continuous sessions where vessel was near cables.
        
        Args:
            track (List[Dict]): Vessel position track
            
        Returns:
            List[List[Dict]]: Sessions of positions near cables
        """
        sessions = []
        current_session = []
        
        for position in track:
            # Check if position is near any cable
            near_cable = False
            for cable in self.cables:
                distance = self._distance_to_cable(
                    position['latitude'], position['longitude'], cable
                )
                if distance <= self.proximity_threshold:
                    near_cable = True
                    break
            
            if near_cable:
                current_session.append(position)
            else:
                # End current session if it exists
                if current_session:
                    sessions.append(current_session)
                    current_session = []
        
        # Don't forget the last session
        if current_session:
            sessions.append(current_session)
        
        return sessions
    
    def _calculate_session_duration(self, session: List[Dict]) -> float:
        """Calculate duration of a session in hours."""
        if len(session) < 2:
            return 0
        
        start_time = datetime.fromisoformat(session[0]['timestamp'])
        end_time = datetime.fromisoformat(session[-1]['timestamp'])
        
        return (end_time - start_time).total_seconds() / 3600
    
    def _distance_to_cable(self, lat: float, lon: float, cable: Dict) -> float:
        """
        Calculate distance from point to cable route.
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            cable (Dict): Cable information
            
        Returns:
            float: Distance in kilometers
        """
        vessel_point = Point(lon, lat)
        cable_line = LineString(cable['route'])
        
        # Distance in degrees, convert to km
        distance_degrees = vessel_point.distance(cable_line)
        return distance_degrees * 111.0
    
    def _find_closest_cable(self, lat: float, lon: float) -> Dict:
        """Find the closest cable to given coordinates."""
        closest_cable = None
        min_distance = float('inf')
        
        for cable in self.cables:
            distance = self._distance_to_cable(lat, lon, cable)
            if distance < min_distance:
                min_distance = distance
                closest_cable = cable
        
        return closest_cable
    
    def _calculate_loitering_risk(self, session: List[Dict], cable: Dict) -> float:
        """
        Calculate risk score for loitering incident.
        
        Args:
            session (List[Dict]): Loitering session positions
            cable (Dict): Cable being monitored
            
        Returns:
            float: Risk score (0-10)
        """
        risk_factors = []
        
        # Duration factor
        duration = self._calculate_session_duration(session)
        if duration > 12:  # Over 12 hours
            risk_factors.append(4)
        elif duration > 6:  # Over 6 hours
            risk_factors.append(3)
        elif duration > 2:  # Over 2 hours
            risk_factors.append(2)
        else:
            risk_factors.append(1)
        
        # Proximity factor
        min_distance = min([
            self._distance_to_cable(pos['latitude'], pos['longitude'], cable)
            for pos in session
        ])
        
        if min_distance < 0.5:  # Very close
            risk_factors.append(4)
        elif min_distance < 1:  # Close
            risk_factors.append(3)
        elif min_distance < 2:  # Moderately close
            risk_factors.append(2)
        else:
            risk_factors.append(1)
        
        # Cable importance factor
        if cable.get('type') == 'power_fiber':  # Power + data
            risk_factors.append(3)
        elif cable.get('sensitivity') == 'high':
            risk_factors.append(2)
        else:
            risk_factors.append(1)
        
        # Time of activity (night operations more suspicious)
        night_positions = sum(1 for pos in session 
                            if self._is_night_time(pos['timestamp']))
        night_ratio = night_positions / len(session)
        
        if night_ratio > 0.8:  # Mostly at night
            risk_factors.append(2)
        elif night_ratio > 0.5:  # Half at night
            risk_factors.append(1)
        else:
            risk_factors.append(0)
        
        # Calculate final risk score
        risk_score = sum(risk_factors)
        return min(10, risk_score)
    
    def _is_night_time(self, timestamp: str) -> bool:
        """Check if timestamp is during night hours (rough approximation)."""
        dt = datetime.fromisoformat(timestamp)
        hour = dt.hour
        # Arctic has complex daylight patterns, but this is a simple approximation
        return hour < 6 or hour > 22
    
    def generate_cable_threat_report(self, vessels: List[Dict], 
                                   loitering_incidents: List[Dict]) -> Dict:
        """
        Generate comprehensive cable threat assessment report.
        
        Args:
            vessels (List[Dict]): Current vessel positions with cable info
            loitering_incidents (List[Dict]): Historical loitering incidents
            
        Returns:
            Dict: Cable threat report
        """
        # Current threats
        current_threats = [v for v in vessels if v.get('near_cable', False)]
        high_risk_vessels = [v for v in current_threats 
                           if any(alert.get('alert_level') in ['HIGH', 'CRITICAL'] 
                                 for alert in v.get('cable_alerts', []))]
        
        # Recent loitering (last 7 days)
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_loitering = [
            incident for incident in loitering_incidents
            if datetime.fromisoformat(incident['start_time']) > recent_cutoff
        ]
        
        # Cable-specific analysis
        cable_analysis = {}
        for cable in self.cables:
            cable_vessels = [v for v in current_threats 
                           if any(alert.get('cable_id') == cable['id'] 
                                 for alert in v.get('cable_alerts', []))]
            
            cable_loitering = [incident for incident in recent_loitering
                             if incident.get('cable_id') == cable['id']]
            
            cable_analysis[cable['id']] = {
                'cable_name': cable['name'],
                'current_vessels_nearby': len(cable_vessels),
                'high_risk_vessels': len([v for v in cable_vessels 
                                        if any(a.get('alert_level') in ['HIGH', 'CRITICAL']
                                              for a in v.get('cable_alerts', []))]),
                'recent_loitering_incidents': len(cable_loitering),
                'total_loitering_hours': sum(incident['duration_hours'] 
                                           for incident in cable_loitering),
                'threat_level': self._assess_cable_threat_level(cable_vessels, cable_loitering)
            }
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'summary': {
                'total_vessels_monitored': len(vessels),
                'vessels_near_cables': len(current_threats),
                'high_risk_vessels': len(high_risk_vessels),
                'recent_loitering_incidents': len(recent_loitering),
                'cables_monitored': len(self.cables)
            },
            'current_threats': current_threats,
            'high_risk_vessels': high_risk_vessels,
            'recent_loitering': recent_loitering,
            'cable_analysis': cable_analysis,
            'recommendations': self._generate_recommendations(cable_analysis)
        }
        
        return report
    
    def _assess_cable_threat_level(self, nearby_vessels: List[Dict], 
                                  loitering_incidents: List[Dict]) -> str:
        """Assess overall threat level for a specific cable."""
        threat_score = 0
        
        # Current vessel threats
        threat_score += len(nearby_vessels)
        
        # High-risk vessel multiplier
        high_risk_count = len([v for v in nearby_vessels 
                             if any(a.get('alert_level') in ['HIGH', 'CRITICAL']
                                   for a in v.get('cable_alerts', []))])
        threat_score += high_risk_count * 2
        
        # Recent loitering
        threat_score += len(loitering_incidents)
        
        # Long loitering incidents
        long_loitering = [i for i in loitering_incidents if i['duration_hours'] > 6]
        threat_score += len(long_loitering) * 2
        
        # Classify threat level
        if threat_score >= 8:
            return 'CRITICAL'
        elif threat_score >= 5:
            return 'HIGH'
        elif threat_score >= 2:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _generate_recommendations(self, cable_analysis: Dict) -> List[str]:
        """Generate security recommendations based on analysis."""
        recommendations = []
        
        # Check for high-threat cables
        high_threat_cables = [cable_id for cable_id, analysis in cable_analysis.items()
                            if analysis['threat_level'] in ['HIGH', 'CRITICAL']]
        
        if high_threat_cables:
            recommendations.append(
                f"Increase monitoring for cables: {', '.join([cable_analysis[c]['cable_name'] for c in high_threat_cables])}"
            )
        
        # Check for repeated loitering
        frequent_loitering = [cable_id for cable_id, analysis in cable_analysis.items()
                            if analysis['recent_loitering_incidents'] >= 3]
        
        if frequent_loitering:
            recommendations.append(
                f"Investigate repeated loitering near: {', '.join([cable_analysis[c]['cable_name'] for c in frequent_loitering])}"
            )
        
        # Check for multiple vessels
        crowded_areas = [cable_id for cable_id, analysis in cable_analysis.items()
                        if analysis['current_vessels_nearby'] >= 5]
        
        if crowded_areas:
            recommendations.append(
                f"High vessel density detected near: {', '.join([cable_analysis[c]['cable_name'] for c in crowded_areas])}"
            )
        
        # General recommendations
        if not recommendations:
            recommendations.append("Current cable infrastructure threat level is acceptable")
        
        recommendations.append("Continue regular monitoring of all cable routes")
        recommendations.append("Maintain coordination with maritime authorities")
        
        return recommendations


class CableDatabase:
    """
    Manage submarine cable database with real-world data.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def load_from_telegeography(self) -> List[Dict]:
        """
        Load cable data from TeleGeography database (simulated).
        In practice, this would fetch from their API or dataset.
        """
        # This would normally fetch from TeleGeography's Submarine Cable Map
        # https://www.submarinecablemap.com/
        pass
    
    def update_cable_status(self, cable_id: str, status: str, timestamp: str):
        """Update operational status of a cable."""
        pass
    
    def get_cables_in_region(self, bounds: Tuple[float, float, float, float]) -> List[Dict]:
        """Get all cables within geographic bounds."""
        pass


if __name__ == "__main__":
    # Example usage
    monitor = CableMonitor()
    
    # Example vessels near Svalbard cable
    test_vessels = [
        {
            'vessel_id': 'DARK_001',
            'latitude': 78.20,
            'longitude': 15.65,
            'timestamp': '2024-11-15T10:30:00'
        },
        {
            'vessel_id': 'AIS_123',
            'latitude': 77.80,
            'longitude': 16.20,
            'timestamp': '2024-11-15T10:30:00'
        }
    ]
    
    # Check cable proximity
    vessels_with_cable_info = monitor.check_vessel_cable_proximity(test_vessels)
    
    # Generate threat report
    report = monitor.generate_cable_threat_report(vessels_with_cable_info, [])
    
    print(f"Cable monitoring report: {report['summary']}")