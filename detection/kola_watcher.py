"""
Kola Peninsula area monitoring module for ArcticShadowTracker.

This module implements specialized monitoring for the strategically important
Kola Peninsula region, focusing on naval activities and sensitive areas.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from geopy.distance import geodesic
from shapely.geometry import Point, Polygon, box
import logging
from typing import List, Dict, Tuple, Optional


class KolaWatcher:
    """
    Specialized monitoring system for Kola Peninsula and surrounding waters.
    
    Monitors:
    - Naval base approaches
    - Restricted military areas
    - Strategic shipping lanes
    - Submarine activity zones
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize monitoring zones
        self.naval_bases = self._define_naval_bases()
        self.restricted_zones = self._define_restricted_zones()
        self.strategic_areas = self._define_strategic_areas()
        self.shipping_lanes = self._define_shipping_lanes()
        
        # Activity patterns
        self.activity_baseline = {}
        self.anomaly_threshold = 2.0  # Standard deviations above normal
        
    def _define_naval_bases(self) -> List[Dict]:
        """
        Define known naval facilities in the Kola Peninsula region.
        
        Returns:
            List[Dict]: Naval base information
        """
        bases = [
            {
                'name': 'Severomorsk Naval Base',
                'id': 'SEVEROMORSK',
                'coordinates': (69.07, 33.42),
                'type': 'northern_fleet_hq',
                'significance': 'critical',
                'monitoring_radius_km': 50,
                'vessel_types': ['surface_combatant', 'submarine', 'support'],
                'typical_activity_level': 'high'
            },
            {
                'name': 'Gadzhiyevo Submarine Base',
                'id': 'GADZHIYEVO',
                'coordinates': (69.25, 33.32),
                'type': 'submarine_base',
                'significance': 'critical',
                'monitoring_radius_km': 30,
                'vessel_types': ['submarine', 'support'],
                'typical_activity_level': 'medium'
            },
            {
                'name': 'Polyarny Naval Base',
                'id': 'POLYARNY',
                'coordinates': (69.20, 33.45),
                'type': 'naval_base',
                'significance': 'high',
                'monitoring_radius_km': 25,
                'vessel_types': ['surface_combatant', 'support'],
                'typical_activity_level': 'medium'
            },
            {
                'name': 'Olenya Bay',
                'id': 'OLENYA',
                'coordinates': (69.08, 33.28),
                'type': 'submarine_facility',
                'significance': 'high',
                'monitoring_radius_km': 20,
                'vessel_types': ['submarine'],
                'typical_activity_level': 'low'
            },
            {
                'name': 'Murmansk Commercial Port',
                'id': 'MURMANSK',
                'coordinates': (68.97, 33.05),
                'type': 'commercial_port',
                'significance': 'medium',
                'monitoring_radius_km': 15,
                'vessel_types': ['commercial', 'support'],
                'typical_activity_level': 'high'
            }
        ]
        
        return bases
    
    def _define_restricted_zones(self) -> List[Dict]:
        """
        Define restricted military areas and exclusion zones.
        
        Returns:
            List[Dict]: Restricted zone definitions
        """
        zones = [
            {
                'name': 'Kola Bay Military Zone',
                'id': 'KOLA_MIL',
                'polygon': [
                    (69.0, 33.0), (69.3, 33.0), (69.3, 33.7), (69.0, 33.7)
                ],
                'restriction_type': 'military_operations',
                'alert_level': 'high',
                'permitted_vessels': ['military', 'authorized_civilian']
            },
            {
                'name': 'Submarine Exercise Area Alpha',
                'id': 'SUB_ALPHA',
                'polygon': [
                    (69.5, 32.5), (70.0, 32.5), (70.0, 34.0), (69.5, 34.0)
                ],
                'restriction_type': 'submarine_operations',
                'alert_level': 'critical',
                'permitted_vessels': ['military']
            },
            {
                'name': 'Northern Fleet Training Area',
                'id': 'NFTA',
                'polygon': [
                    (68.5, 32.0), (70.5, 32.0), (70.5, 35.0), (68.5, 35.0)
                ],
                'restriction_type': 'naval_exercises',
                'alert_level': 'medium',
                'permitted_vessels': ['military', 'support']
            },
            {
                'name': 'Sensitive Infrastructure Zone',
                'id': 'INFRA_SENS',
                'polygon': [
                    (69.0, 33.2), (69.2, 33.2), (69.2, 33.5), (69.0, 33.5)
                ],
                'restriction_type': 'infrastructure_protection',
                'alert_level': 'high',
                'permitted_vessels': ['authorized_only']
            }
        ]
        
        return zones
    
    def _define_strategic_areas(self) -> List[Dict]:
        """
        Define areas of strategic interest for monitoring.
        
        Returns:
            List[Dict]: Strategic area definitions
        """
        areas = [
            {
                'name': 'Barents Sea Approach',
                'id': 'BARENTS_APP',
                'center': (70.0, 35.0),
                'radius_km': 100,
                'significance': 'high',
                'monitoring_focus': ['foreign_military', 'intelligence_gathering']
            },
            {
                'name': 'GIUK Gap Northern Approach',
                'id': 'GIUK_NORTH',
                'center': (72.0, 30.0),
                'radius_km': 150,
                'significance': 'critical',
                'monitoring_focus': ['submarine_transit', 'naval_movements']
            },
            {
                'name': 'Svalbard Transit Route',
                'id': 'SVALBARD_TRANSIT',
                'center': (75.0, 25.0),
                'radius_km': 200,
                'significance': 'medium',
                'monitoring_focus': ['civilian_vessels', 'research_vessels']
            },
            {
                'name': 'Franz Josef Land Approach',
                'id': 'FJL_APP',
                'center': (80.0, 45.0),
                'radius_km': 100,
                'significance': 'medium',
                'monitoring_focus': ['arctic_operations', 'sovereignty_assertion']
            }
        ]
        
        return areas
    
    def _define_shipping_lanes(self) -> List[Dict]:
        """
        Define major shipping lanes for monitoring commercial traffic.
        
        Returns:
            List[Dict]: Shipping lane definitions
        """
        lanes = [
            {
                'name': 'Northern Sea Route - Western Section',
                'id': 'NSR_WEST',
                'waypoints': [
                    (68.97, 33.05),  # Murmansk
                    (70.0, 40.0),    # Barents Sea
                    (72.0, 55.0),    # Kara Gate
                    (74.0, 70.0)     # Kara Sea
                ],
                'width_km': 20,
                'traffic_type': 'commercial',
                'seasonal': True,
                'peak_months': [6, 7, 8, 9, 10]  # June to October
            },
            {
                'name': 'Murmansk Approach Channel',
                'id': 'MURMANSK_APP',
                'waypoints': [
                    (68.5, 32.0),    # Open sea
                    (68.8, 32.5),    # Approach
                    (68.97, 33.05)   # Murmansk
                ],
                'width_km': 10,
                'traffic_type': 'mixed',
                'seasonal': False
            },
            {
                'name': 'Kirkenes-Murmansk Route',
                'id': 'KIRKENES_MUR',
                'waypoints': [
                    (69.73, 30.05),  # Kirkenes
                    (69.5, 31.5),    # Mid-route
                    (68.97, 33.05)   # Murmansk
                ],
                'width_km': 15,
                'traffic_type': 'commercial',
                'seasonal': False
            }
        ]
        
        return lanes
    
    def analyze_vessel_activity(self, vessels: List[Dict]) -> Dict:
        """
        Analyze vessel activity in the Kola Peninsula region.
        
        Args:
            vessels (List[Dict]): List of vessel positions and data
            
        Returns:
            Dict: Analysis results with alerts and assessments
        """
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'total_vessels_monitored': len(vessels),
            'naval_base_activity': {},
            'restricted_zone_violations': [],
            'strategic_area_activity': {},
            'shipping_lane_activity': {},
            'anomalies': [],
            'threat_assessment': {}
        }
        
        # Analyze activity around naval bases
        for base in self.naval_bases:
            base_vessels = self._get_vessels_near_point(
                vessels, base['coordinates'], base['monitoring_radius_km']
            )
            
            analysis['naval_base_activity'][base['id']] = {
                'base_name': base['name'],
                'vessel_count': len(base_vessels),
                'vessel_types': self._classify_vessels_by_type(base_vessels),
                'activity_level': self._assess_activity_level(base_vessels, base),
                'vessels': base_vessels
            }
        
        # Check for restricted zone violations
        for zone in self.restricted_zones:
            zone_violations = self._check_zone_violations(vessels, zone)
            analysis['restricted_zone_violations'].extend(zone_violations)
        
        # Analyze strategic areas
        for area in self.strategic_areas:
            area_vessels = self._get_vessels_near_point(
                vessels, area['center'], area['radius_km']
            )
            
            analysis['strategic_area_activity'][area['id']] = {
                'area_name': area['name'],
                'vessel_count': len(area_vessels),
                'significance_level': area['significance'],
                'monitoring_focus': area['monitoring_focus'],
                'notable_vessels': self._identify_notable_vessels(area_vessels, area),
                'vessels': area_vessels
            }
        
        # Analyze shipping lanes
        for lane in self.shipping_lanes:
            lane_traffic = self._analyze_shipping_lane(vessels, lane)
            analysis['shipping_lane_activity'][lane['id']] = lane_traffic
        
        # Detect anomalies
        analysis['anomalies'] = self._detect_activity_anomalies(analysis)
        
        # Generate threat assessment
        analysis['threat_assessment'] = self._generate_threat_assessment(analysis)
        
        return analysis
    
    def _get_vessels_near_point(self, vessels: List[Dict], point: Tuple[float, float], 
                               radius_km: float) -> List[Dict]:
        """Get vessels within specified radius of a point."""
        nearby_vessels = []
        
        for vessel in vessels:
            vessel_pos = (vessel['latitude'], vessel['longitude'])
            distance = geodesic(point, vessel_pos).kilometers
            
            if distance <= radius_km:
                vessel_copy = vessel.copy()
                vessel_copy['distance_from_point_km'] = distance
                nearby_vessels.append(vessel_copy)
        
        return nearby_vessels
    
    def _classify_vessels_by_type(self, vessels: List[Dict]) -> Dict[str, int]:
        """Classify vessels by type and count them."""
        type_counts = {}
        
        for vessel in vessels:
            vessel_type = self._determine_vessel_type(vessel)
            type_counts[vessel_type] = type_counts.get(vessel_type, 0) + 1
        
        return type_counts
    
    def _determine_vessel_type(self, vessel: Dict) -> str:
        """
        Determine vessel type based on available data.
        
        Args:
            vessel (Dict): Vessel data
            
        Returns:
            str: Vessel type classification
        """
        # Use AIS data if available
        if 'ship_type' in vessel:
            ship_type = vessel['ship_type']
            if ship_type in range(30, 38):  # Fishing vessels
                return 'fishing'
            elif ship_type in range(70, 80):  # Cargo
                return 'cargo'
            elif ship_type in range(80, 90):  # Tanker
                return 'tanker'
            elif ship_type in range(35, 40):  # Military
                return 'military'
        
        # Use size estimates
        if 'estimated_length' in vessel:
            length = vessel['estimated_length']
            if length > 200:
                return 'large_commercial'
            elif length > 100:
                return 'medium_commercial'
            elif length > 50:
                return 'small_commercial'
            else:
                return 'small_vessel'
        
        # Use behavioral patterns
        if 'vessel_history' in vessel:
            history = vessel['vessel_history']
            if history.get('ais_gaps_count', 0) > 5:
                return 'suspicious'
            elif history.get('avg_speed', 0) > 20:
                return 'fast_vessel'
        
        return 'unknown'
    
    def _assess_activity_level(self, vessels: List[Dict], base: Dict) -> str:
        """Assess activity level around a naval base."""
        vessel_count = len(vessels)
        typical_level = base['typical_activity_level']
        
        # Define thresholds based on typical activity
        if typical_level == 'high':
            thresholds = {'low': 10, 'medium': 20, 'high': 35, 'very_high': 50}
        elif typical_level == 'medium':
            thresholds = {'low': 5, 'medium': 12, 'high': 25, 'very_high': 40}
        else:  # low
            thresholds = {'low': 2, 'medium': 6, 'high': 15, 'very_high': 25}
        
        # Classify current activity
        if vessel_count >= thresholds['very_high']:
            return 'very_high'
        elif vessel_count >= thresholds['high']:
            return 'high'
        elif vessel_count >= thresholds['medium']:
            return 'medium'
        else:
            return 'low'
    
    def _check_zone_violations(self, vessels: List[Dict], zone: Dict) -> List[Dict]:
        """Check for violations of restricted zones."""
        violations = []
        zone_polygon = Polygon(zone['polygon'])
        
        for vessel in vessels:
            vessel_point = Point(vessel['longitude'], vessel['latitude'])
            
            if zone_polygon.contains(vessel_point):
                vessel_type = self._determine_vessel_type(vessel)
                
                # Check if vessel type is permitted
                if vessel_type not in zone.get('permitted_vessels', []):
                    violation = {
                        'vessel_id': vessel.get('vessel_id', 'unknown'),
                        'zone_name': zone['name'],
                        'zone_id': zone['id'],
                        'restriction_type': zone['restriction_type'],
                        'alert_level': zone['alert_level'],
                        'vessel_type': vessel_type,
                        'position': {'lat': vessel['latitude'], 'lon': vessel['longitude']},
                        'timestamp': vessel.get('timestamp', datetime.now().isoformat()),
                        'violation_severity': self._calculate_violation_severity(vessel, zone)
                    }
                    violations.append(violation)
        
        return violations
    
    def _calculate_violation_severity(self, vessel: Dict, zone: Dict) -> str:
        """Calculate severity of a zone violation."""
        base_severity = zone['alert_level']
        vessel_type = self._determine_vessel_type(vessel)
        
        # Upgrade severity for foreign military vessels
        if vessel_type == 'military' and vessel.get('nationality') != 'RU':
            if base_severity == 'medium':
                return 'high'
            elif base_severity == 'high':
                return 'critical'
        
        # Upgrade for suspicious vessels
        if vessel_type == 'suspicious':
            if base_severity == 'medium':
                return 'high'
        
        return base_severity
    
    def _identify_notable_vessels(self, vessels: List[Dict], area: Dict) -> List[Dict]:
        """Identify vessels of particular interest in strategic areas."""
        notable_vessels = []
        focus_areas = area['monitoring_focus']
        
        for vessel in vessels:
            vessel_type = self._determine_vessel_type(vessel)
            is_notable = False
            notable_reasons = []
            
            # Check against monitoring focus
            if 'foreign_military' in focus_areas and vessel_type == 'military':
                if vessel.get('nationality') != 'RU':
                    is_notable = True
                    notable_reasons.append('foreign_military_vessel')
            
            if 'intelligence_gathering' in focus_areas:
                if vessel.get('vessel_history', {}).get('loitering_incidents', 0) > 2:
                    is_notable = True
                    notable_reasons.append('potential_intelligence_gathering')
            
            if 'submarine_transit' in focus_areas and vessel_type == 'unknown':
                # Submarines might appear as unknown contacts
                if vessel.get('ais_data') is None:  # No AIS = possibly submarine
                    is_notable = True
                    notable_reasons.append('possible_submarine')
            
            # Size-based criteria
            if vessel.get('estimated_length', 0) > 150:
                is_notable = True
                notable_reasons.append('large_vessel')
            
            if is_notable:
                notable_vessel = vessel.copy()
                notable_vessel['notable_reasons'] = notable_reasons
                notable_vessels.append(notable_vessel)
        
        return notable_vessels
    
    def _analyze_shipping_lane(self, vessels: List[Dict], lane: Dict) -> Dict:
        """Analyze traffic in a shipping lane."""
        # Create lane geometry
        from shapely.geometry import LineString
        
        lane_line = LineString(lane['waypoints'])
        lane_buffer = lane_line.buffer(lane['width_km'] / 111.0)  # Convert km to degrees
        
        # Find vessels in lane
        lane_vessels = []
        for vessel in vessels:
            vessel_point = Point(vessel['longitude'], vessel['latitude'])
            if lane_buffer.contains(vessel_point):
                lane_vessels.append(vessel)
        
        # Analyze traffic
        traffic_analysis = {
            'lane_name': lane['name'],
            'vessel_count': len(lane_vessels),
            'traffic_types': self._classify_vessels_by_type(lane_vessels),
            'seasonal_expected': lane.get('seasonal', False),
            'vessels': lane_vessels
        }
        
        # Check if traffic is appropriate for season (if seasonal)
        if lane.get('seasonal', False):
            current_month = datetime.now().month
            peak_months = lane.get('peak_months', [])
            
            if current_month in peak_months:
                traffic_analysis['seasonal_status'] = 'peak_season'
            else:
                traffic_analysis['seasonal_status'] = 'off_season'
                if len(lane_vessels) > 0:
                    traffic_analysis['off_season_alert'] = True
        
        return traffic_analysis
    
    def _detect_activity_anomalies(self, analysis: Dict) -> List[Dict]:
        """Detect anomalous activity patterns."""
        anomalies = []
        
        # Check for unusual naval base activity
        for base_id, base_data in analysis['naval_base_activity'].items():
            if base_data['activity_level'] == 'very_high':
                anomalies.append({
                    'type': 'high_naval_activity',
                    'location': base_data['base_name'],
                    'details': f"Very high activity at {base_data['base_name']}: {base_data['vessel_count']} vessels",
                    'severity': 'medium'
                })
        
        # Check for multiple zone violations
        if len(analysis['restricted_zone_violations']) > 3:
            anomalies.append({
                'type': 'multiple_zone_violations',
                'details': f"{len(analysis['restricted_zone_violations'])} restricted zone violations detected",
                'severity': 'high'
            })
        
        # Check for foreign military activity
        for area_id, area_data in analysis['strategic_area_activity'].items():
            foreign_military = [v for v in area_data['notable_vessels'] 
                              if 'foreign_military_vessel' in v.get('notable_reasons', [])]
            if len(foreign_military) > 0:
                anomalies.append({
                    'type': 'foreign_military_presence',
                    'location': area_data['area_name'],
                    'details': f"{len(foreign_military)} foreign military vessels in strategic area",
                    'severity': 'high'
                })
        
        return anomalies
    
    def _generate_threat_assessment(self, analysis: Dict) -> Dict:
        """Generate overall threat assessment for the region."""
        threat_factors = []
        threat_score = 0
        
        # Zone violations
        violation_count = len(analysis['restricted_zone_violations'])
        if violation_count > 0:
            threat_factors.append(f"{violation_count} restricted zone violations")
            threat_score += violation_count * 2
        
        # Foreign military presence
        foreign_military_count = 0
        for area_data in analysis['strategic_area_activity'].values():
            foreign_military_count += len([v for v in area_data['notable_vessels'] 
                                         if 'foreign_military_vessel' in v.get('notable_reasons', [])])
        
        if foreign_military_count > 0:
            threat_factors.append(f"{foreign_military_count} foreign military vessels")
            threat_score += foreign_military_count * 3
        
        # High activity levels
        high_activity_bases = [base_data['base_name'] 
                              for base_data in analysis['naval_base_activity'].values()
                              if base_data['activity_level'] in ['high', 'very_high']]
        
        if len(high_activity_bases) > 2:
            threat_factors.append(f"High activity at {len(high_activity_bases)} naval bases")
            threat_score += len(high_activity_bases)
        
        # Anomalies
        anomaly_count = len(analysis['anomalies'])
        if anomaly_count > 0:
            threat_factors.append(f"{anomaly_count} activity anomalies")
            threat_score += anomaly_count
        
        # Calculate threat level
        if threat_score >= 15:
            threat_level = 'CRITICAL'
        elif threat_score >= 10:
            threat_level = 'HIGH'
        elif threat_score >= 5:
            threat_level = 'MEDIUM'
        else:
            threat_level = 'LOW'
        
        return {
            'threat_level': threat_level,
            'threat_score': threat_score,
            'threat_factors': threat_factors,
            'recommendations': self._generate_recommendations(threat_level, analysis)
        }
    
    def _generate_recommendations(self, threat_level: str, analysis: Dict) -> List[str]:
        """Generate security recommendations based on threat assessment."""
        recommendations = []
        
        if threat_level in ['HIGH', 'CRITICAL']:
            recommendations.append("Increase monitoring frequency in all zones")
            recommendations.append("Alert maritime patrol units")
            recommendations.append("Coordinate with naval intelligence")
        
        if analysis['restricted_zone_violations']:
            recommendations.append("Investigate restricted zone violations immediately")
            recommendations.append("Consider diplomatic notifications if foreign vessels involved")
        
        foreign_activity = any(
            len([v for v in area_data['notable_vessels'] 
                if 'foreign_military_vessel' in v.get('notable_reasons', [])]) > 0
            for area_data in analysis['strategic_area_activity'].values()
        )
        
        if foreign_activity:
            recommendations.append("Track foreign military vessel movements")
            recommendations.append("Prepare situation reports for command")
        
        if not recommendations:
            recommendations.append("Maintain standard monitoring procedures")
        
        recommendations.append("Continue regular surveillance of all strategic areas")
        
        return recommendations
    
    def generate_kola_report(self, vessels: List[Dict]) -> Dict:
        """
        Generate comprehensive Kola Peninsula monitoring report.
        
        Args:
            vessels (List[Dict]): Current vessel positions
            
        Returns:
            Dict: Complete monitoring report
        """
        analysis = self.analyze_vessel_activity(vessels)
        
        report = {
            'report_type': 'kola_peninsula_monitoring',
            'timestamp': datetime.now().isoformat(),
            'region': 'Kola Peninsula and Barents Sea',
            'analysis': analysis,
            'executive_summary': {
                'total_vessels': analysis['total_vessels_monitored'],
                'threat_level': analysis['threat_assessment']['threat_level'],
                'zone_violations': len(analysis['restricted_zone_violations']),
                'foreign_military_detected': len([
                    v for area in analysis['strategic_area_activity'].values()
                    for v in area['notable_vessels']
                    if 'foreign_military_vessel' in v.get('notable_reasons', [])
                ]),
                'anomalies_detected': len(analysis['anomalies'])
            },
            'priority_alerts': self._extract_priority_alerts(analysis),
            'monitoring_status': 'active',
            'next_update': (datetime.now() + timedelta(hours=6)).isoformat()
        }
        
        return report
    
    def _extract_priority_alerts(self, analysis: Dict) -> List[Dict]:
        """Extract high-priority alerts for immediate attention."""
        priority_alerts = []
        
        # Critical zone violations
        critical_violations = [v for v in analysis['restricted_zone_violations']
                             if v['alert_level'] == 'critical']
        for violation in critical_violations:
            priority_alerts.append({
                'type': 'critical_zone_violation',
                'priority': 'immediate',
                'message': f"Critical violation in {violation['zone_name']} by {violation['vessel_type']} vessel",
                'vessel_id': violation['vessel_id']
            })
        
        # Foreign military in sensitive areas
        for area_id, area_data in analysis['strategic_area_activity'].items():
            foreign_military = [v for v in area_data['notable_vessels'] 
                              if 'foreign_military_vessel' in v.get('notable_reasons', [])]
            if foreign_military and area_data['significance_level'] == 'critical':
                priority_alerts.append({
                    'type': 'foreign_military_critical_area',
                    'priority': 'high',
                    'message': f"Foreign military vessel detected in critical area: {area_data['area_name']}",
                    'vessel_count': len(foreign_military)
                })
        
        # High anomaly count
        if len(analysis['anomalies']) >= 3:
            priority_alerts.append({
                'type': 'multiple_anomalies',
                'priority': 'medium',
                'message': f"Multiple anomalies detected: {len(analysis['anomalies'])} incidents",
                'anomaly_types': [a['type'] for a in analysis['anomalies']]
            })
        
        return priority_alerts


if __name__ == "__main__":
    # Example usage
    watcher = KolaWatcher()
    
    # Example vessels in Kola Peninsula region
    test_vessels = [
        {
            'vessel_id': 'FOREIGN_NAVY_001',
            'latitude': 69.15,
            'longitude': 33.35,
            'nationality': 'US',
            'ship_type': 35,  # Military vessel
            'estimated_length': 180,
            'timestamp': '2024-11-15T10:30:00'
        },
        {
            'vessel_id': 'DARK_VESSEL_002',
            'latitude': 69.25,
            'longitude': 33.32,
            'estimated_length': 120,
            'timestamp': '2024-11-15T10:30:00'
        },
        {
            'vessel_id': 'COMMERCIAL_003',
            'latitude': 68.97,
            'longitude': 33.05,
            'ship_type': 70,  # Cargo
            'estimated_length': 200,
            'timestamp': '2024-11-15T10:30:00'
        }
    ]
    
    # Generate monitoring report
    report = watcher.generate_kola_report(test_vessels)
    
    print(f"Kola Peninsula Report Summary:")
    print(f"Threat Level: {report['executive_summary']['threat_level']}")
    print(f"Zone Violations: {report['executive_summary']['zone_violations']}")
    print(f"Foreign Military: {report['executive_summary']['foreign_military_detected']}")
    print(f"Priority Alerts: {len(report['priority_alerts'])}")