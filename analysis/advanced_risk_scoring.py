"""
Risk scoring module for ArcticShadowTracker.

This module implements comprehensive risk assessment algorithms to score
vessel threats based on multiple factors including behavior, location,
vessel characteristics, and intelligence indicators.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from geopy.distance import geodesic
from typing import List, Dict, Tuple, Optional, Any
import logging


class RiskScorer:
    """
    Comprehensive risk scoring system for maritime threats.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Risk weight configurations
        self.risk_weights = {
            'vessel_characteristics': 0.20,
            'behavioral_patterns': 0.25,
            'location_context': 0.20,
            'temporal_factors': 0.15,
            'intelligence_indicators': 0.20
        }
        
        # Critical infrastructure definitions
        self.critical_infrastructure = self._load_critical_infrastructure()
        
        # Threat assessment matrices
        self.threat_matrices = self._initialize_threat_matrices()
        
    def _load_critical_infrastructure(self) -> List[Dict]:
        """Load critical infrastructure locations and definitions."""
        return [
            {
                'type': 'submarine_cable',
                'name': 'Svalbard Cable System',
                'coordinates': [(78.22, 15.63), (71.17, 25.78)],
                'criticality': 'high',
                'protection_radius_km': 5,
                'risk_multiplier': 2.0
            },
            {
                'type': 'naval_base',
                'name': 'Severomorsk',
                'coordinates': [(69.07, 33.42)],
                'criticality': 'critical',
                'protection_radius_km': 50,
                'risk_multiplier': 3.0
            },
            {
                'type': 'oil_platform',
                'name': 'Goliat Platform',
                'coordinates': [(71.25, 22.25)],
                'criticality': 'medium',
                'protection_radius_km': 10,
                'risk_multiplier': 1.5
            },
            {
                'type': 'research_station',
                'name': 'Ny-Ålesund',
                'coordinates': [(78.92, 11.93)],
                'criticality': 'medium',
                'protection_radius_km': 15,
                'risk_multiplier': 1.3
            }
        ]
    
    def _initialize_threat_matrices(self) -> Dict:
        """Initialize threat assessment matrices."""
        return {
            'vessel_size_threat': {
                # Length in meters -> base threat score
                (0, 20): 1,      # Small boats
                (20, 50): 2,     # Medium vessels
                (50, 100): 3,    # Large vessels
                (100, 200): 4,   # Very large vessels
                (200, float('inf')): 5  # Massive vessels
            },
            'vessel_type_threat': {
                'fishing': 2,
                'cargo': 2,
                'tanker': 3,
                'passenger': 2,
                'military': 5,
                'research': 2,
                'unknown': 4,
                'submarine': 6
            },
            'nationality_risk': {
                'NO': 1,    # Norway - lowest risk
                'IS': 1,    # Iceland
                'DK': 1,    # Denmark
                'SE': 1,    # Sweden
                'FI': 1,    # Finland
                'GB': 1.2,  # UK
                'US': 1.2,  # USA
                'CA': 1.2,  # Canada
                'DE': 1.3,  # Germany
                'FR': 1.3,  # France
                'NL': 1.3,  # Netherlands
                'RU': 2.5,  # Russia - higher risk in Arctic
                'CN': 2.0,  # China
                'KP': 3.0,  # North Korea - highest risk
                'IR': 2.8,  # Iran
                'UNKNOWN': 2.0  # Unknown nationality
            },
            'behavior_risk_scores': {
                'normal_fishing': 1,
                'normal_transit': 1,
                'normal_patrol': 2,
                'surveillance_pattern': 5,
                'evasive_maneuvers': 6,
                'rendezvous_pattern': 5,
                'loitering': 4,
                'ais_manipulation': 6
            }
        }
    
    def calculate_comprehensive_risk_score(self, vessel_data: Dict) -> Dict:
        """
        Calculate comprehensive risk score for a vessel.
        
        Args:
            vessel_data (Dict): Complete vessel information
            
        Returns:
            Dict: Detailed risk assessment
        """
        risk_assessment = {
            'vessel_id': vessel_data.get('vessel_id', 'unknown'),
            'timestamp': datetime.now().isoformat(),
            'overall_risk_score': 0,
            'risk_level': 'LOW',
            'component_scores': {},
            'risk_factors': [],
            'mitigating_factors': [],
            'recommendations': []
        }
        
        # Calculate component scores
        vessel_score = self._score_vessel_characteristics(vessel_data)
        behavioral_score = self._score_behavioral_patterns(vessel_data)
        location_score = self._score_location_context(vessel_data)
        temporal_score = self._score_temporal_factors(vessel_data)
        intelligence_score = self._score_intelligence_indicators(vessel_data)
        
        # Store component scores
        risk_assessment['component_scores'] = {
            'vessel_characteristics': vessel_score,
            'behavioral_patterns': behavioral_score,
            'location_context': location_score,
            'temporal_factors': temporal_score,
            'intelligence_indicators': intelligence_score
        }
        
        # Calculate weighted overall score
        overall_score = (
            vessel_score['score'] * self.risk_weights['vessel_characteristics'] +
            behavioral_score['score'] * self.risk_weights['behavioral_patterns'] +
            location_score['score'] * self.risk_weights['location_context'] +
            temporal_score['score'] * self.risk_weights['temporal_factors'] +
            intelligence_score['score'] * self.risk_weights['intelligence_indicators']
        )
        
        risk_assessment['overall_risk_score'] = overall_score
        
        # Determine risk level
        risk_assessment['risk_level'] = self._determine_risk_level(overall_score)
        
        # Collect risk factors
        all_components = [vessel_score, behavioral_score, location_score, 
                         temporal_score, intelligence_score]
        for component in all_components:
            risk_assessment['risk_factors'].extend(component.get('risk_factors', []))
            risk_assessment['mitigating_factors'].extend(component.get('mitigating_factors', []))
        
        # Generate recommendations
        risk_assessment['recommendations'] = self._generate_risk_recommendations(
            risk_assessment['risk_level'], risk_assessment['component_scores']
        )
        
        return risk_assessment
    
    def _score_vessel_characteristics(self, vessel_data: Dict) -> Dict:
        """Score based on vessel physical and identification characteristics."""
        score = 0
        risk_factors = []
        mitigating_factors = []
        
        # Vessel size scoring
        vessel_length = vessel_data.get('estimated_length', vessel_data.get('length', 0))
        for (min_len, max_len), threat_score in self.threat_matrices['vessel_size_threat'].items():
            if min_len <= vessel_length < max_len:
                score += threat_score
                if threat_score >= 4:
                    risk_factors.append(f"Large vessel ({vessel_length}m)")
                break
        
        # Vessel type scoring
        vessel_type = vessel_data.get('vessel_type', 'unknown')
        if vessel_type in self.threat_matrices['vessel_type_threat']:
            type_score = self.threat_matrices['vessel_type_threat'][vessel_type]
            score += type_score
            if type_score >= 4:
                risk_factors.append(f"High-risk vessel type: {vessel_type}")
            elif type_score <= 2:
                mitigating_factors.append(f"Low-risk vessel type: {vessel_type}")
        
        # Nationality/flag scoring
        nationality = vessel_data.get('nationality', vessel_data.get('flag', 'UNKNOWN'))
        nationality_multiplier = self.threat_matrices['nationality_risk'].get(nationality, 2.0)
        score *= nationality_multiplier
        
        if nationality_multiplier >= 2.0:
            risk_factors.append(f"High-risk nationality: {nationality}")
        elif nationality_multiplier <= 1.2:
            mitigating_factors.append(f"Allied/friendly nationality: {nationality}")
        
        # AIS presence
        has_ais = vessel_data.get('ais_data') is not None
        if not has_ais:
            score += 2
            risk_factors.append("No AIS signal (dark vessel)")
        else:
            mitigating_factors.append("AIS signal present")
        
        # Ship identification
        has_imo = vessel_data.get('imo_number') is not None
        has_mmsi = vessel_data.get('mmsi') is not None
        
        if not has_imo and not has_mmsi:
            score += 1
            risk_factors.append("No international identification numbers")
        
        # Age and condition indicators
        if 'year_built' in vessel_data:
            age = datetime.now().year - vessel_data['year_built']
            if age > 30:
                score += 0.5
                risk_factors.append(f"Old vessel ({age} years)")
        
        return {
            'score': min(10, score),  # Cap at 10
            'risk_factors': risk_factors,
            'mitigating_factors': mitigating_factors,
            'details': {
                'size_score': vessel_length,
                'type_score': vessel_type,
                'nationality_multiplier': nationality_multiplier,
                'has_ais': has_ais
            }
        }
    
    def _score_behavioral_patterns(self, vessel_data: Dict) -> Dict:
        """Score based on vessel behavioral patterns."""
        score = 0
        risk_factors = []
        mitigating_factors = []
        
        # Get behavior classification
        behavior_analysis = vessel_data.get('behavior_analysis', {})
        
        # Primary behavior pattern
        behavior_pattern = behavior_analysis.get('pattern_classification', {}).get('pattern', 'unknown')
        if behavior_pattern in self.threat_matrices['behavior_risk_scores']:
            pattern_score = self.threat_matrices['behavior_risk_scores'][behavior_pattern]
            score += pattern_score
            
            if pattern_score >= 5:
                risk_factors.append(f"Suspicious behavior pattern: {behavior_pattern}")
            elif pattern_score <= 2:
                mitigating_factors.append(f"Normal behavior pattern: {behavior_pattern}")
        
        # Behavior confidence
        behavior_confidence = behavior_analysis.get('pattern_classification', {}).get('confidence', 1.0)
        if behavior_confidence < 0.5:
            score += 1
            risk_factors.append("Uncertain behavior classification")
        
        # Anomalies
        anomalies = behavior_analysis.get('anomalies', [])
        high_severity_anomalies = len([a for a in anomalies if a.get('severity') == 'high'])
        medium_severity_anomalies = len([a for a in anomalies if a.get('severity') == 'medium'])
        
        score += high_severity_anomalies * 1.5
        score += medium_severity_anomalies * 0.5
        
        if high_severity_anomalies > 0:
            risk_factors.append(f"{high_severity_anomalies} high-severity behavioral anomalies")
        
        # Movement characteristics
        movement_features = behavior_analysis.get('movement_features', {})
        
        # Excessive speed changes
        speed_variance = movement_features.get('speed_variance', 0)
        if speed_variance > 100:
            score += 1
            risk_factors.append("Highly variable speed patterns")
        
        # Frequent course changes
        turning_frequency = movement_features.get('turning_frequency', 0)
        if turning_frequency > 0.5:
            score += 1
            risk_factors.append("Frequent course changes")
        
        # Extended stationary periods
        stationary_periods = movement_features.get('stationary_periods', 0)
        if stationary_periods > 0.4:
            score += 1
            risk_factors.append("Extended stationary periods (loitering)")
        
        # Track history consistency
        vessel_history = vessel_data.get('vessel_history', {})
        ais_gaps = vessel_history.get('ais_gaps_count', 0)
        if ais_gaps > 5:
            score += 2
            risk_factors.append(f"Multiple AIS gaps ({ais_gaps} incidents)")
        
        return {
            'score': min(10, score),
            'risk_factors': risk_factors,
            'mitigating_factors': mitigating_factors,
            'details': {
                'behavior_pattern': behavior_pattern,
                'anomaly_count': len(anomalies),
                'ais_gaps': ais_gaps
            }
        }
    
    def _score_location_context(self, vessel_data: Dict) -> Dict:
        """Score based on vessel location and proximity to sensitive areas."""
        score = 0
        risk_factors = []
        mitigating_factors = []
        
        vessel_lat = vessel_data.get('latitude', 0)
        vessel_lon = vessel_data.get('longitude', 0)
        vessel_pos = (vessel_lat, vessel_lon)
        
        # Check proximity to critical infrastructure
        closest_infrastructure = None
        min_distance = float('inf')
        
        for infrastructure in self.critical_infrastructure:
            if infrastructure['type'] == 'submarine_cable':
                # For cables, calculate distance to line
                from shapely.geometry import Point, LineString
                vessel_point = Point(vessel_lon, vessel_lat)
                cable_line = LineString([(lon, lat) for lat, lon in infrastructure['coordinates']])
                distance_degrees = vessel_point.distance(cable_line)
                distance_km = distance_degrees * 111.0  # Approximate conversion
            else:
                # For point infrastructure, calculate distance to point
                infra_pos = infrastructure['coordinates'][0]
                distance_km = geodesic(vessel_pos, infra_pos).kilometers
            
            if distance_km < min_distance:
                min_distance = distance_km
                closest_infrastructure = infrastructure
        
        # Score based on proximity to closest infrastructure
        if closest_infrastructure and min_distance <= closest_infrastructure['protection_radius_km']:
            proximity_score = (
                (closest_infrastructure['protection_radius_km'] - min_distance) / 
                closest_infrastructure['protection_radius_km'] * 5 * 
                closest_infrastructure['risk_multiplier']
            )
            score += proximity_score
            
            risk_factors.append(
                f"Within {min_distance:.1f}km of {closest_infrastructure['name']} "
                f"({closest_infrastructure['type']})"
            )
        
        # Check for restricted zones
        restricted_zones = vessel_data.get('restricted_zone_violations', [])
        for violation in restricted_zones:
            if violation.get('alert_level') == 'critical':
                score += 3
                risk_factors.append(f"Critical zone violation: {violation['zone_name']}")
            elif violation.get('alert_level') == 'high':
                score += 2
                risk_factors.append(f"High-level zone violation: {violation['zone_name']}")
            else:
                score += 1
                risk_factors.append(f"Zone violation: {violation['zone_name']}")
        
        # Geographic context
        # Arctic waters (higher baseline risk due to strategic importance)
        if vessel_lat > 70:
            score += 0.5
            risk_factors.append("Operating in High Arctic waters")
        elif vessel_lat > 66.5:
            score += 0.3
            risk_factors.append("Operating in Arctic Circle")
        
        # Distance from nearest port
        distance_to_port = vessel_data.get('distance_to_port', 0)
        if distance_to_port > 200:  # Very far from any port
            score += 1
            risk_factors.append(f"Far from nearest port ({distance_to_port:.0f}km)")
        elif distance_to_port < 50:  # Close to port
            mitigating_factors.append("Close to commercial port")
        
        # International waters vs territorial waters
        if vessel_data.get('in_territorial_waters') == False:
            score += 0.5
            risk_factors.append("Operating in international waters")
        else:
            mitigating_factors.append("Operating in territorial waters")
        
        return {
            'score': min(10, score),
            'risk_factors': risk_factors,
            'mitigating_factors': mitigating_factors,
            'details': {
                'closest_infrastructure': closest_infrastructure['name'] if closest_infrastructure else None,
                'infrastructure_distance_km': min_distance,
                'zone_violations': len(restricted_zones),
                'arctic_level': 'high' if vessel_lat > 70 else 'standard' if vessel_lat > 66.5 else 'none'
            }
        }
    
    def _score_temporal_factors(self, vessel_data: Dict) -> Dict:
        """Score based on temporal context and timing patterns."""
        score = 0
        risk_factors = []
        mitigating_factors = []
        
        current_time = datetime.now()
        detection_time = vessel_data.get('detection_time', current_time.isoformat())
        detection_dt = datetime.fromisoformat(detection_time)
        
        # Time of day analysis
        hour = detection_dt.hour
        if 2 <= hour <= 5:  # Early morning hours
            score += 1
            risk_factors.append("Activity during suspicious hours (2-5 AM)")
        elif 22 <= hour or hour <= 2:  # Late night
            score += 0.5
            risk_factors.append("Night-time activity")
        
        # Day of week
        weekday = detection_dt.weekday()
        if weekday >= 5:  # Weekend
            score += 0.3
            risk_factors.append("Weekend activity")
        
        # Seasonal considerations
        month = detection_dt.month
        if month in [11, 12, 1, 2]:  # Winter months in Arctic
            score += 0.5
            risk_factors.append("Winter Arctic operations")
        elif month in [6, 7, 8]:  # Summer navigation season
            mitigating_factors.append("Normal navigation season")
        
        # Activity patterns
        behavior_analysis = vessel_data.get('behavior_analysis', {})
        temporal_features = behavior_analysis.get('temporal_features', {})
        
        # Night activity ratio
        night_ratio = temporal_features.get('night_activity_ratio', 0)
        if night_ratio > 0.7:
            score += 1.5
            risk_factors.append("Predominantly night-time operations")
        elif night_ratio < 0.3:
            mitigating_factors.append("Predominantly daytime operations")
        
        # Weekend activity ratio
        weekend_ratio = temporal_features.get('weekend_activity_ratio', 0)
        if weekend_ratio > 0.8:
            score += 1
            risk_factors.append("Predominantly weekend operations")
        
        # Recent events correlation
        # Check for correlation with military exercises, diplomatic tensions, etc.
        # This would integrate with external intelligence feeds
        geopolitical_tension = self._assess_geopolitical_context(detection_dt)
        score += geopolitical_tension['score']
        risk_factors.extend(geopolitical_tension['factors'])
        
        return {
            'score': min(10, score),
            'risk_factors': risk_factors,
            'mitigating_factors': mitigating_factors,
            'details': {
                'hour_of_day': hour,
                'day_of_week': weekday,
                'month': month,
                'night_activity_ratio': night_ratio,
                'geopolitical_context': geopolitical_tension
            }
        }
    
    def _score_intelligence_indicators(self, vessel_data: Dict) -> Dict:
        """Score based on intelligence indicators and threat databases."""
        score = 0
        risk_factors = []
        mitigating_factors = []
        
        # Vessel identification checks
        vessel_id = vessel_data.get('vessel_id')
        imo_number = vessel_data.get('imo_number')
        mmsi = vessel_data.get('mmsi')
        
        # Check against known threat databases (simulated)
        threat_db_hits = self._check_threat_databases(vessel_id, imo_number, mmsi)
        
        if threat_db_hits['sanctions_list']:
            score += 5
            risk_factors.append("Vessel on sanctions list")
        
        if threat_db_hits['watch_list']:
            score += 3
            risk_factors.append("Vessel on intelligence watch list")
        
        if threat_db_hits['previous_violations']:
            score += 2
            risk_factors.append("Previous maritime violations recorded")
        
        # Owner/operator analysis
        vessel_owner = vessel_data.get('owner', '')
        if vessel_owner:
            owner_risk = self._assess_owner_risk(vessel_owner)
            score += owner_risk['score']
            risk_factors.extend(owner_risk['factors'])
        
        # Communication patterns
        vessel_history = vessel_data.get('vessel_history', {})
        
        # AIS manipulation indicators
        if vessel_history.get('ais_manipulation_suspected', False):
            score += 3
            risk_factors.append("Suspected AIS manipulation")
        
        # Unusual communication gaps
        comm_gaps = vessel_history.get('ais_gaps_count', 0)
        if comm_gaps > 10:
            score += 2
            risk_factors.append("Frequent communication blackouts")
        
        # Pattern analysis
        suspicious_meetings = vessel_history.get('suspicious_meetings', 0)
        if suspicious_meetings > 0:
            score += suspicious_meetings * 0.5
            risk_factors.append(f"Suspicious vessel encounters ({suspicious_meetings})")
        
        # Technology indicators
        if vessel_data.get('jamming_detected', False):
            score += 4
            risk_factors.append("Electronic jamming detected")
        
        if vessel_data.get('spoofing_detected', False):
            score += 3
            risk_factors.append("GPS/AIS spoofing detected")
        
        return {
            'score': min(10, score),
            'risk_factors': risk_factors,
            'mitigating_factors': mitigating_factors,
            'details': {
                'threat_db_hits': threat_db_hits,
                'communication_anomalies': comm_gaps,
                'owner_assessment': vessel_owner
            }
        }
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level based on overall score."""
        if score >= 8:
            return 'CRITICAL'
        elif score >= 6:
            return 'HIGH'
        elif score >= 4:
            return 'MEDIUM'
        elif score >= 2:
            return 'LOW'
        else:
            return 'MINIMAL'
    
    def _assess_geopolitical_context(self, timestamp: datetime) -> Dict:
        """Assess geopolitical context that might affect risk."""
        # This would integrate with external intelligence feeds
        # For now, simulated based on general Arctic tensions
        
        score = 0
        factors = []
        
        # Simulated tension periods (in practice, this would be data-driven)
        month = timestamp.month
        year = timestamp.year
        
        # Heightened tensions during certain periods
        if month in [3, 4, 5]:  # Spring military exercises
            score += 0.5
            factors.append("Spring military exercise season")
        
        if month in [9, 10]:  # Autumn tensions
            score += 0.3
            factors.append("Autumn geopolitical tensions")
        
        # Recent events (would be fed from intelligence sources)
        days_since_incident = (timestamp - datetime(2024, 10, 1)).days
        if days_since_incident < 30:
            score += 1
            factors.append("Recent geopolitical incident")
        
        return {
            'score': score,
            'factors': factors
        }
    
    def _check_threat_databases(self, vessel_id: str, imo: str, mmsi: str) -> Dict:
        """Check vessel against threat databases."""
        # Simulated database checks
        # In practice, this would query real threat intelligence databases
        
        # Simple simulation based on vessel characteristics
        hits = {
            'sanctions_list': False,
            'watch_list': False,
            'previous_violations': False
        }
        
        # Simulate some hits for demonstration
        if vessel_id and 'SUSPICIOUS' in vessel_id.upper():
            hits['watch_list'] = True
        
        if imo and len(imo) != 7:  # Invalid IMO format
            hits['previous_violations'] = True
        
        return hits
    
    def _assess_owner_risk(self, owner: str) -> Dict:
        """Assess risk based on vessel owner/operator."""
        score = 0
        factors = []
        
        # Simulated owner risk assessment
        # In practice, this would check against corporate databases
        
        if not owner or owner.upper() in ['UNKNOWN', 'N/A', '']:
            score += 1
            factors.append("Unknown vessel owner")
        
        # Check for shell companies (simplified)
        if 'LLC' in owner and len(owner.split()) < 3:
            score += 0.5
            factors.append("Possible shell company registration")
        
        return {
            'score': score,
            'factors': factors
        }
    
    def _generate_risk_recommendations(self, risk_level: str, component_scores: Dict) -> List[str]:
        """Generate recommendations based on risk assessment."""
        recommendations = []
        
        if risk_level == 'CRITICAL':
            recommendations.append("IMMEDIATE ACTION REQUIRED - Alert maritime security")
            recommendations.append("Initiate real-time tracking")
            recommendations.append("Coordinate with naval assets")
            recommendations.append("Prepare diplomatic notifications if foreign vessel")
        
        elif risk_level == 'HIGH':
            recommendations.append("Increase monitoring frequency")
            recommendations.append("Alert relevant authorities")
            recommendations.append("Correlate with other intelligence sources")
            recommendations.append("Prepare incident response procedures")
        
        elif risk_level == 'MEDIUM':
            recommendations.append("Continue enhanced monitoring")
            recommendations.append("Log all activities for pattern analysis")
            recommendations.append("Cross-reference with vessel databases")
        
        elif risk_level == 'LOW':
            recommendations.append("Maintain standard monitoring")
            recommendations.append("Include in routine reports")
        
        # Specific recommendations based on component scores
        if component_scores['behavioral_patterns']['score'] >= 6:
            recommendations.append("Conduct detailed behavioral pattern analysis")
        
        if component_scores['location_context']['score'] >= 6:
            recommendations.append("Verify vessel permissions for current area")
        
        if component_scores['intelligence_indicators']['score'] >= 5:
            recommendations.append("Run comprehensive background check")
        
        return recommendations
    
    def generate_risk_report(self, vessel_assessments: List[Dict]) -> Dict:
        """
        Generate comprehensive risk report for multiple vessels.
        
        Args:
            vessel_assessments (List[Dict]): Risk assessments for multiple vessels
            
        Returns:
            Dict: Comprehensive risk report
        """
        if not vessel_assessments:
            return {'error': 'No vessel assessments provided'}
        
        # Sort by risk score
        vessel_assessments.sort(key=lambda x: x['overall_risk_score'], reverse=True)
        
        # Count by risk level
        risk_level_counts = {}
        for assessment in vessel_assessments:
            level = assessment['risk_level']
            risk_level_counts[level] = risk_level_counts.get(level, 0) + 1
        
        # Identify top threats
        top_threats = vessel_assessments[:5]  # Top 5 highest risk
        
        # Calculate statistics
        scores = [a['overall_risk_score'] for a in vessel_assessments]
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'total_vessels_assessed': len(vessel_assessments),
            'risk_level_distribution': risk_level_counts,
            'statistics': {
                'highest_risk_score': max(scores),
                'average_risk_score': np.mean(scores),
                'median_risk_score': np.median(scores),
                'critical_threats': risk_level_counts.get('CRITICAL', 0),
                'high_threats': risk_level_counts.get('HIGH', 0)
            },
            'top_threats': top_threats,
            'threat_summary': self._generate_threat_summary(vessel_assessments),
            'regional_assessment': self._assess_regional_threat_level(vessel_assessments),
            'recommendations': self._generate_overall_recommendations(vessel_assessments)
        }
        
        return report
    
    def _generate_threat_summary(self, assessments: List[Dict]) -> Dict:
        """Generate summary of threat patterns."""
        # Analyze common risk factors
        all_risk_factors = []
        for assessment in assessments:
            all_risk_factors.extend(assessment['risk_factors'])
        
        # Count occurrences
        from collections import Counter
        factor_counts = Counter(all_risk_factors)
        
        return {
            'most_common_threats': factor_counts.most_common(5),
            'emerging_patterns': self._identify_emerging_patterns(assessments)
        }
    
    def _identify_emerging_patterns(self, assessments: List[Dict]) -> List[str]:
        """Identify emerging threat patterns."""
        patterns = []
        
        # Look for patterns in high-risk vessels
        high_risk_vessels = [a for a in assessments if a['risk_level'] in ['HIGH', 'CRITICAL']]
        
        if len(high_risk_vessels) > 3:
            patterns.append(f"Elevated threat activity: {len(high_risk_vessels)} high-risk vessels")
        
        # Check for geographic clustering
        locations = []
        for assessment in high_risk_vessels:
            for component in assessment['component_scores'].values():
                details = component.get('details', {})
                if 'closest_infrastructure' in details:
                    locations.append(details['closest_infrastructure'])
        
        if locations:
            from collections import Counter
            location_counts = Counter(locations)
            most_targeted = location_counts.most_common(1)[0]
            if most_targeted[1] > 1:
                patterns.append(f"Multiple threats near {most_targeted[0]}")
        
        return patterns
    
    def _assess_regional_threat_level(self, assessments: List[Dict]) -> str:
        """Assess overall regional threat level."""
        critical_count = len([a for a in assessments if a['risk_level'] == 'CRITICAL'])
        high_count = len([a for a in assessments if a['risk_level'] == 'HIGH'])
        
        if critical_count >= 3:
            return 'CRITICAL'
        elif critical_count >= 1 or high_count >= 5:
            return 'HIGH'
        elif high_count >= 2:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _generate_overall_recommendations(self, assessments: List[Dict]) -> List[str]:
        """Generate overall recommendations for the region."""
        recommendations = []
        
        critical_count = len([a for a in assessments if a['risk_level'] == 'CRITICAL'])
        high_count = len([a for a in assessments if a['risk_level'] == 'HIGH'])
        
        if critical_count > 0:
            recommendations.append("ALERT: Critical threats detected - activate emergency protocols")
        
        if high_count >= 3:
            recommendations.append("Increase regional security posture")
        
        recommendations.append("Continue systematic monitoring of all identified vessels")
        recommendations.append("Maintain coordination with allied maritime forces")
        
        return recommendations


if __name__ == "__main__":
    # Example usage
    scorer = RiskScorer()
    
    # Example vessel data
    test_vessel = {
        'vessel_id': 'SUSPICIOUS_001',
        'latitude': 69.15,
        'longitude': 33.35,
        'estimated_length': 120,
        'vessel_type': 'unknown',
        'nationality': 'UNKNOWN',
        'ais_data': None,  # Dark vessel
        'behavior_analysis': {
            'pattern_classification': {
                'pattern': 'surveillance_pattern',
                'confidence': 0.8
            },
            'anomalies': [
                {'type': 'suspicious_stop', 'severity': 'high'},
                {'type': 'communication_gap', 'severity': 'medium'}
            ]
        },
        'vessel_history': {
            'ais_gaps_count': 8,
            'suspicious_meetings': 2
        }
    }
    
    # Calculate risk score
    risk_assessment = scorer.calculate_comprehensive_risk_score(test_vessel)
    
    print(f"Risk Assessment:")
    print(f"Overall Score: {risk_assessment['overall_risk_score']:.1f}")
    print(f"Risk Level: {risk_assessment['risk_level']}")
    print(f"Key Risk Factors: {risk_assessment['risk_factors'][:3]}")
    print(f"Recommendations: {risk_assessment['recommendations'][:2]}")