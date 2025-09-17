"""
Pattern analysis module for ArcticShadowTracker.

This module implements sophisticated behavioral pattern analysis to identify
suspicious vessel activities, classify behavior types, and predict potential threats.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from geopy.distance import geodesic
import logging
from typing import List, Dict, Tuple, Optional, Any


class BehaviorPatternAnalyzer:
    """
    Analyze vessel behavioral patterns to identify suspicious activities.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scaler = StandardScaler()
        
        # Pattern definitions
        self.known_patterns = {
            'normal_fishing': {
                'speed_range': (2, 8),
                'turning_frequency': 'high',
                'stationary_periods': 'common',
                'area_size': 'small_to_medium',
                'time_pattern': 'day_night'
            },
            'normal_transit': {
                'speed_range': (8, 25),
                'turning_frequency': 'low',
                'stationary_periods': 'rare',
                'area_size': 'linear',
                'time_pattern': 'continuous'
            },
            'normal_patrol': {
                'speed_range': (5, 15),
                'turning_frequency': 'medium',
                'stationary_periods': 'occasional',
                'area_size': 'defined_route',
                'time_pattern': 'scheduled'
            },
            'surveillance_pattern': {
                'speed_range': (3, 12),
                'turning_frequency': 'low',
                'stationary_periods': 'extended',
                'area_size': 'focused',
                'time_pattern': 'target_dependent'
            },
            'evasive_maneuvers': {
                'speed_range': (10, 30),
                'turning_frequency': 'very_high',
                'stationary_periods': 'none',
                'area_size': 'erratic',
                'time_pattern': 'reactive'
            },
            'rendezvous_pattern': {
                'speed_range': (5, 15),
                'turning_frequency': 'convergent',
                'stationary_periods': 'synchronized',
                'area_size': 'meeting_point',
                'time_pattern': 'coordinated'
            }
        }
        
    def analyze_vessel_behavior(self, vessel_id: str, track_history: List[Dict],
                               time_window_hours: int = 24) -> Dict:
        """
        Analyze behavioral patterns for a single vessel.
        
        Args:
            vessel_id (str): Unique vessel identifier
            track_history (List[Dict]): Historical position data
            time_window_hours (int): Analysis time window
            
        Returns:
            Dict: Behavioral analysis results
        """
        if len(track_history) < 3:
            return {'error': 'Insufficient track data for analysis'}
        
        # Filter to recent data
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        recent_track = [
            pos for pos in track_history
            if datetime.fromisoformat(pos['timestamp']) > cutoff_time
        ]
        
        if len(recent_track) < 3:
            return {'error': 'Insufficient recent track data'}
        
        # Extract behavioral features
        movement_features = self._extract_movement_features(recent_track)
        temporal_features = self._extract_temporal_features(recent_track)
        spatial_features = self._extract_spatial_features(recent_track)
        
        # Classify behavior pattern
        pattern_classification = self._classify_behavior_pattern(
            movement_features, temporal_features, spatial_features
        )
        
        # Detect anomalies
        anomalies = self._detect_behavioral_anomalies(recent_track)
        
        # Calculate suspicion score
        suspicion_score = self._calculate_suspicion_score(
            pattern_classification, anomalies, movement_features
        )
        
        analysis_result = {
            'vessel_id': vessel_id,
            'analysis_timestamp': datetime.now().isoformat(),
            'time_window_hours': time_window_hours,
            'track_points_analyzed': len(recent_track),
            'movement_features': movement_features,
            'temporal_features': temporal_features,
            'spatial_features': spatial_features,
            'pattern_classification': pattern_classification,
            'anomalies': anomalies,
            'suspicion_score': suspicion_score,
            'behavioral_assessment': self._generate_behavioral_assessment(
                pattern_classification, suspicion_score, anomalies
            )
        }
        
        return analysis_result
    
    def _extract_movement_features(self, track: List[Dict]) -> Dict:
        """Extract movement-related features from vessel track."""
        if len(track) < 2:
            return {}
        
        speeds = []
        headings = []
        accelerations = []
        
        for i in range(len(track) - 1):
            pos1, pos2 = track[i], track[i + 1]
            
            # Calculate speed
            distance = geodesic(
                (pos1['latitude'], pos1['longitude']),
                (pos2['latitude'], pos2['longitude'])
            ).meters
            
            time_diff = (
                datetime.fromisoformat(pos2['timestamp']) - 
                datetime.fromisoformat(pos1['timestamp'])
            ).total_seconds()
            
            if time_diff > 0:
                speed = distance / time_diff * 3.6  # km/h
                speeds.append(speed)
                
                # Calculate heading
                heading = self._calculate_bearing(
                    pos1['latitude'], pos1['longitude'],
                    pos2['latitude'], pos2['longitude']
                )
                headings.append(heading)
        
        # Calculate accelerations
        for i in range(len(speeds) - 1):
            if i + 1 < len(track) - 1:
                time_diff = (
                    datetime.fromisoformat(track[i + 2]['timestamp']) - 
                    datetime.fromisoformat(track[i + 1]['timestamp'])
                ).total_seconds()
                if time_diff > 0:
                    acceleration = (speeds[i + 1] - speeds[i]) / time_diff
                    accelerations.append(acceleration)
        
        # Calculate heading changes
        heading_changes = []
        for i in range(len(headings) - 1):
            change = abs(headings[i + 1] - headings[i])
            # Handle wrap-around
            if change > 180:
                change = 360 - change
            heading_changes.append(change)
        
        features = {
            'average_speed': np.mean(speeds) if speeds else 0,
            'max_speed': np.max(speeds) if speeds else 0,
            'speed_variance': np.var(speeds) if speeds else 0,
            'speed_consistency': 1 / (1 + np.std(speeds)) if speeds else 0,
            'average_acceleration': np.mean(np.abs(accelerations)) if accelerations else 0,
            'max_acceleration': np.max(np.abs(accelerations)) if accelerations else 0,
            'turning_frequency': len([c for c in heading_changes if c > 30]) / len(heading_changes) if heading_changes else 0,
            'average_heading_change': np.mean(heading_changes) if heading_changes else 0,
            'max_heading_change': np.max(heading_changes) if heading_changes else 0,
            'stationary_periods': len([s for s in speeds if s < 1]) / len(speeds) if speeds else 0,
            'high_speed_periods': len([s for s in speeds if s > 20]) / len(speeds) if speeds else 0
        }
        
        return features
    
    def _extract_temporal_features(self, track: List[Dict]) -> Dict:
        """Extract temporal pattern features."""
        timestamps = [datetime.fromisoformat(pos['timestamp']) for pos in track]
        
        # Hour of day analysis
        hours = [ts.hour for ts in timestamps]
        
        # Day of week analysis
        weekdays = [ts.weekday() for ts in timestamps]
        
        # Activity gaps
        gaps = []
        for i in range(len(timestamps) - 1):
            gap = (timestamps[i + 1] - timestamps[i]).total_seconds() / 3600
            gaps.append(gap)
        
        features = {
            'activity_span_hours': (timestamps[-1] - timestamps[0]).total_seconds() / 3600,
            'most_active_hour': max(set(hours), key=hours.count) if hours else 12,
            'night_activity_ratio': len([h for h in hours if h < 6 or h > 22]) / len(hours) if hours else 0,
            'weekend_activity_ratio': len([d for d in weekdays if d >= 5]) / len(weekdays) if weekdays else 0,
            'average_position_interval': np.mean(gaps) if gaps else 0,
            'max_gap_hours': np.max(gaps) if gaps else 0,
            'position_frequency': len(track) / ((timestamps[-1] - timestamps[0]).total_seconds() / 3600) if len(timestamps) > 1 else 0,
            'activity_regularity': 1 / (1 + np.std(gaps)) if gaps else 0
        }
        
        return features
    
    def _extract_spatial_features(self, track: List[Dict]) -> Dict:
        """Extract spatial pattern features."""
        if len(track) < 2:
            return {}
        
        lats = [pos['latitude'] for pos in track]
        lons = [pos['longitude'] for pos in track]
        
        # Calculate bounding box
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        
        # Calculate center of activity
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)
        
        # Calculate distances from center
        distances_from_center = [
            geodesic((center_lat, center_lon), (lat, lon)).meters
            for lat, lon in zip(lats, lons)
        ]
        
        # Calculate track length
        total_distance = 0
        for i in range(len(track) - 1):
            dist = geodesic(
                (track[i]['latitude'], track[i]['longitude']),
                (track[i + 1]['latitude'], track[i + 1]['longitude'])
            ).meters
            total_distance += dist
        
        # Calculate sinuosity (path complexity)
        straight_distance = geodesic(
            (track[0]['latitude'], track[0]['longitude']),
            (track[-1]['latitude'], track[-1]['longitude'])
        ).meters
        
        sinuosity = total_distance / straight_distance if straight_distance > 0 else 1
        
        features = {
            'operating_area_km2': lat_range * lon_range * 111 * 111,  # Approximate
            'bounding_box_aspect_ratio': max(lat_range, lon_range) / min(lat_range, lon_range) if min(lat_range, lon_range) > 0 else 1,
            'center_of_activity': {'lat': center_lat, 'lon': center_lon},
            'max_distance_from_center': np.max(distances_from_center),
            'average_distance_from_center': np.mean(distances_from_center),
            'activity_concentration': 1 / (1 + np.std(distances_from_center)),
            'total_distance_km': total_distance / 1000,
            'sinuosity': sinuosity,
            'revisit_tendency': self._calculate_revisit_tendency(track)
        }
        
        return features
    
    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing between two points."""
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        
        dlon = lon2 - lon1
        y = np.sin(dlon) * np.cos(lat2)
        x = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
        
        bearing = np.arctan2(y, x)
        return (np.degrees(bearing) + 360) % 360
    
    def _calculate_revisit_tendency(self, track: List[Dict]) -> float:
        """Calculate how often vessel returns to previous locations."""
        if len(track) < 4:
            return 0
        
        revisits = 0
        threshold_meters = 500  # 500m threshold for considering a revisit
        
        for i, pos1 in enumerate(track[:-2]):
            for j in range(i + 2, len(track)):
                pos2 = track[j]
                distance = geodesic(
                    (pos1['latitude'], pos1['longitude']),
                    (pos2['latitude'], pos2['longitude'])
                ).meters
                
                if distance < threshold_meters:
                    revisits += 1
                    break  # Count only first revisit to avoid multiple counts
        
        return revisits / len(track)
    
    def _classify_behavior_pattern(self, movement_features: Dict, 
                                  temporal_features: Dict, 
                                  spatial_features: Dict) -> Dict:
        """Classify vessel behavior pattern based on extracted features."""
        if not all([movement_features, temporal_features, spatial_features]):
            return {'pattern': 'unknown', 'confidence': 0}
        
        pattern_scores = {}
        
        for pattern_name, pattern_def in self.known_patterns.items():
            score = 0
            max_score = 0
            
            # Check speed characteristics
            avg_speed = movement_features.get('average_speed', 0)
            speed_range = pattern_def['speed_range']
            if speed_range[0] <= avg_speed <= speed_range[1]:
                score += 2
            max_score += 2
            
            # Check turning behavior
            turning_freq = movement_features.get('turning_frequency', 0)
            if pattern_def['turning_frequency'] == 'high' and turning_freq > 0.3:
                score += 1
            elif pattern_def['turning_frequency'] == 'medium' and 0.1 <= turning_freq <= 0.3:
                score += 1
            elif pattern_def['turning_frequency'] == 'low' and turning_freq < 0.1:
                score += 1
            max_score += 1
            
            # Check stationary behavior
            stationary_ratio = movement_features.get('stationary_periods', 0)
            if pattern_def['stationary_periods'] == 'common' and stationary_ratio > 0.3:
                score += 1
            elif pattern_def['stationary_periods'] == 'occasional' and 0.1 <= stationary_ratio <= 0.3:
                score += 1
            elif pattern_def['stationary_periods'] == 'rare' and stationary_ratio < 0.1:
                score += 1
            elif pattern_def['stationary_periods'] == 'extended' and stationary_ratio > 0.5:
                score += 1
            max_score += 1
            
            # Check area characteristics
            sinuosity = spatial_features.get('sinuosity', 1)
            if pattern_def['area_size'] == 'linear' and sinuosity < 1.5:
                score += 1
            elif pattern_def['area_size'] == 'small_to_medium' and spatial_features.get('operating_area_km2', 0) < 100:
                score += 1
            elif pattern_def['area_size'] == 'focused' and spatial_features.get('activity_concentration', 0) > 0.7:
                score += 1
            max_score += 1
            
            # Calculate normalized score
            pattern_scores[pattern_name] = score / max_score if max_score > 0 else 0
        
        # Find best matching pattern
        best_pattern = max(pattern_scores, key=pattern_scores.get)
        confidence = pattern_scores[best_pattern]
        
        return {
            'pattern': best_pattern,
            'confidence': confidence,
            'all_scores': pattern_scores,
            'is_suspicious': best_pattern in ['surveillance_pattern', 'evasive_maneuvers', 'rendezvous_pattern']
        }
    
    def _detect_behavioral_anomalies(self, track: List[Dict]) -> List[Dict]:
        """Detect anomalous behaviors in vessel track."""
        anomalies = []
        
        if len(track) < 3:
            return anomalies
        
        # Extract speeds for analysis
        speeds = []
        for i in range(len(track) - 1):
            pos1, pos2 = track[i], track[i + 1]
            distance = geodesic(
                (pos1['latitude'], pos1['longitude']),
                (pos2['latitude'], pos2['longitude'])
            ).meters
            time_diff = (
                datetime.fromisoformat(pos2['timestamp']) - 
                datetime.fromisoformat(pos1['timestamp'])
            ).total_seconds()
            
            if time_diff > 0:
                speed = distance / time_diff * 3.6  # km/h
                speeds.append(speed)
        
        # Detect speed anomalies
        if speeds:
            speed_mean = np.mean(speeds)
            speed_std = np.std(speeds)
            
            for i, speed in enumerate(speeds):
                if speed > speed_mean + 3 * speed_std:
                    anomalies.append({
                        'type': 'excessive_speed',
                        'timestamp': track[i + 1]['timestamp'],
                        'value': speed,
                        'threshold': speed_mean + 3 * speed_std,
                        'severity': 'high' if speed > 40 else 'medium'
                    })
                elif speed > 0 and speed < speed_mean - 2 * speed_std and speed < 1:
                    anomalies.append({
                        'type': 'suspicious_stop',
                        'timestamp': track[i + 1]['timestamp'],
                        'value': speed,
                        'threshold': speed_mean - 2 * speed_std,
                        'severity': 'medium'
                    })
        
        # Detect location anomalies (unusual positions)
        positions = [(pos['latitude'], pos['longitude']) for pos in track]
        if len(positions) > 5:
            # Use DBSCAN to find outlier positions
            coords_array = np.array(positions)
            db = DBSCAN(eps=0.01, min_samples=3).fit(coords_array)  # eps in degrees
            
            outlier_indices = np.where(db.labels_ == -1)[0]
            for idx in outlier_indices:
                anomalies.append({
                    'type': 'location_outlier',
                    'timestamp': track[idx]['timestamp'],
                    'position': positions[idx],
                    'severity': 'medium'
                })
        
        # Detect temporal anomalies
        timestamps = [datetime.fromisoformat(pos['timestamp']) for pos in track]
        for i in range(len(timestamps) - 1):
            gap = (timestamps[i + 1] - timestamps[i]).total_seconds() / 3600
            
            if gap > 12:  # Gap longer than 12 hours
                anomalies.append({
                    'type': 'communication_gap',
                    'start_time': track[i]['timestamp'],
                    'end_time': track[i + 1]['timestamp'],
                    'duration_hours': gap,
                    'severity': 'high' if gap > 24 else 'medium'
                })
        
        return anomalies
    
    def _calculate_suspicion_score(self, pattern_classification: Dict, 
                                  anomalies: List[Dict], 
                                  movement_features: Dict) -> float:
        """Calculate overall suspicion score for vessel behavior."""
        suspicion_score = 0
        
        # Base score from pattern classification
        if pattern_classification.get('is_suspicious', False):
            suspicion_score += 3
        
        pattern_confidence = pattern_classification.get('confidence', 0)
        if pattern_confidence < 0.5:  # Low confidence = uncertain behavior
            suspicion_score += 2
        
        # Score from anomalies
        high_severity_anomalies = len([a for a in anomalies if a.get('severity') == 'high'])
        medium_severity_anomalies = len([a for a in anomalies if a.get('severity') == 'medium'])
        
        suspicion_score += high_severity_anomalies * 2
        suspicion_score += medium_severity_anomalies * 1
        
        # Score from movement characteristics
        if movement_features.get('speed_variance', 0) > 50:  # Highly variable speed
            suspicion_score += 1
        
        if movement_features.get('turning_frequency', 0) > 0.5:  # Frequent course changes
            suspicion_score += 1
        
        if movement_features.get('stationary_periods', 0) > 0.4:  # Frequent stops
            suspicion_score += 1
        
        # Normalize to 0-10 scale
        return min(10, suspicion_score)
    
    def _generate_behavioral_assessment(self, pattern_classification: Dict, 
                                       suspicion_score: float, 
                                       anomalies: List[Dict]) -> Dict:
        """Generate human-readable behavioral assessment."""
        assessment = {
            'overall_assessment': '',
            'risk_level': '',
            'key_observations': [],
            'recommendations': []
        }
        
        # Determine risk level
        if suspicion_score >= 8:
            assessment['risk_level'] = 'HIGH'
        elif suspicion_score >= 5:
            assessment['risk_level'] = 'MEDIUM'
        elif suspicion_score >= 2:
            assessment['risk_level'] = 'LOW'
        else:
            assessment['risk_level'] = 'MINIMAL'
        
        # Generate overall assessment
        pattern = pattern_classification.get('pattern', 'unknown')
        confidence = pattern_classification.get('confidence', 0)
        
        if pattern in ['surveillance_pattern', 'evasive_maneuvers']:
            assessment['overall_assessment'] = f"Vessel exhibits {pattern.replace('_', ' ')} with {confidence:.1%} confidence. Requires monitoring."
        elif pattern == 'rendezvous_pattern':
            assessment['overall_assessment'] = "Vessel appears to be coordinating with other vessels. Investigate potential meetings."
        elif confidence < 0.5:
            assessment['overall_assessment'] = "Vessel behavior is inconsistent with known patterns. Uncertain classification."
        else:
            assessment['overall_assessment'] = f"Vessel exhibits normal {pattern.replace('_', ' ')} behavior."
        
        # Key observations
        if anomalies:
            assessment['key_observations'].append(f"{len(anomalies)} behavioral anomalies detected")
        
        if pattern_classification.get('is_suspicious', False):
            assessment['key_observations'].append("Behavior matches suspicious pattern")
        
        # Recommendations
        if assessment['risk_level'] in ['HIGH', 'MEDIUM']:
            assessment['recommendations'].append("Increase monitoring frequency")
            assessment['recommendations'].append("Correlate with other intelligence sources")
        
        if any(a['type'] == 'communication_gap' for a in anomalies):
            assessment['recommendations'].append("Investigate communication gaps")
        
        if assessment['risk_level'] == 'HIGH':
            assessment['recommendations'].append("Consider immediate investigation")
        
        return assessment


class FleetPatternAnalyzer:
    """
    Analyze patterns across multiple vessels to detect coordinated activities.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detect_coordinated_behavior(self, vessel_tracks: Dict[str, List[Dict]], 
                                   time_window_hours: int = 6,
                                   proximity_threshold_km: float = 10) -> List[Dict]:
        """
        Detect coordinated behavior between multiple vessels.
        
        Args:
            vessel_tracks (Dict): Vessel tracks keyed by vessel ID
            time_window_hours (int): Time window for correlation analysis
            proximity_threshold_km (float): Distance threshold for coordination
            
        Returns:
            List[Dict]: Detected coordination events
        """
        coordination_events = []
        
        # Get current time window
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=time_window_hours)
        
        # Filter recent positions for all vessels
        recent_positions = {}
        for vessel_id, track in vessel_tracks.items():
            recent_track = [
                pos for pos in track
                if datetime.fromisoformat(pos['timestamp']) > cutoff_time
            ]
            if len(recent_track) >= 2:
                recent_positions[vessel_id] = recent_track
        
        # Check for spatial coordination
        spatial_groups = self._find_spatial_groups(recent_positions, proximity_threshold_km)
        for group in spatial_groups:
            if len(group['vessels']) >= 2:
                coordination_events.append({
                    'type': 'spatial_coordination',
                    'vessels': group['vessels'],
                    'center_position': group['center'],
                    'max_distance_km': group['max_distance'],
                    'duration_hours': group['duration'],
                    'timestamp': current_time.isoformat()
                })
        
        # Check for temporal coordination
        temporal_events = self._find_temporal_coordination(recent_positions)
        coordination_events.extend(temporal_events)
        
        # Check for movement coordination
        movement_events = self._find_movement_coordination(recent_positions)
        coordination_events.extend(movement_events)
        
        return coordination_events
    
    def _find_spatial_groups(self, vessel_positions: Dict, threshold_km: float) -> List[Dict]:
        """Find groups of vessels in close proximity."""
        groups = []
        
        # Get latest position for each vessel
        latest_positions = {}
        for vessel_id, track in vessel_positions.items():
            if track:
                latest_positions[vessel_id] = track[-1]
        
        # Find vessels within threshold distance
        vessel_ids = list(latest_positions.keys())
        for i, vessel1_id in enumerate(vessel_ids):
            group_vessels = [vessel1_id]
            pos1 = latest_positions[vessel1_id]
            
            for j in range(i + 1, len(vessel_ids)):
                vessel2_id = vessel_ids[j]
                pos2 = latest_positions[vessel2_id]
                
                distance = geodesic(
                    (pos1['latitude'], pos1['longitude']),
                    (pos2['latitude'], pos2['longitude'])
                ).kilometers
                
                if distance <= threshold_km:
                    group_vessels.append(vessel2_id)
            
            if len(group_vessels) >= 2:
                # Calculate group center and stats
                group_positions = [latest_positions[vid] for vid in group_vessels]
                center_lat = np.mean([pos['latitude'] for pos in group_positions])
                center_lon = np.mean([pos['longitude'] for pos in group_positions])
                
                # Calculate max distance from center
                max_distance = max([
                    geodesic((center_lat, center_lon), 
                            (pos['latitude'], pos['longitude'])).kilometers
                    for pos in group_positions
                ])
                
                groups.append({
                    'vessels': group_vessels,
                    'center': {'lat': center_lat, 'lon': center_lon},
                    'max_distance': max_distance,
                    'duration': self._calculate_group_duration(vessel_positions, group_vessels)
                })
        
        return groups
    
    def _calculate_group_duration(self, vessel_positions: Dict, group_vessels: List[str]) -> float:
        """Calculate how long vessels have been in proximity."""
        if len(group_vessels) < 2:
            return 0
        
        # Find common time period where all vessels were close
        # This is a simplified version - in practice, you'd need more sophisticated analysis
        min_track_length = min(len(vessel_positions[vid]) for vid in group_vessels)
        
        # Estimate based on position frequency
        if min_track_length > 0:
            first_pos = vessel_positions[group_vessels[0]][0]
            last_pos = vessel_positions[group_vessels[0]][-1]
            total_duration = (
                datetime.fromisoformat(last_pos['timestamp']) - 
                datetime.fromisoformat(first_pos['timestamp'])
            ).total_seconds() / 3600
            
            return total_duration
        
        return 0
    
    def _find_temporal_coordination(self, vessel_positions: Dict) -> List[Dict]:
        """Find temporally coordinated behaviors."""
        events = []
        
        # Look for synchronized starts/stops
        vessel_events = {}
        for vessel_id, track in vessel_positions.items():
            vessel_events[vessel_id] = self._extract_vessel_events(track)
        
        # Find synchronized events
        for event_type in ['start', 'stop', 'course_change']:
            sync_events = self._find_synchronized_events(vessel_events, event_type)
            events.extend(sync_events)
        
        return events
    
    def _extract_vessel_events(self, track: List[Dict]) -> Dict[str, List[Dict]]:
        """Extract events (starts, stops, course changes) from vessel track."""
        events = {'start': [], 'stop': [], 'course_change': []}
        
        if len(track) < 2:
            return events
        
        # Calculate speeds
        speeds = []
        for i in range(len(track) - 1):
            pos1, pos2 = track[i], track[i + 1]
            distance = geodesic(
                (pos1['latitude'], pos1['longitude']),
                (pos2['latitude'], pos2['longitude'])
            ).meters
            time_diff = (
                datetime.fromisoformat(pos2['timestamp']) - 
                datetime.fromisoformat(pos1['timestamp'])
            ).total_seconds()
            
            speed = distance / time_diff * 3.6 if time_diff > 0 else 0
            speeds.append(speed)
        
        # Detect start/stop events
        for i, speed in enumerate(speeds):
            if i > 0:
                prev_speed = speeds[i - 1]
                if prev_speed < 1 and speed > 3:  # Start moving
                    events['start'].append({
                        'timestamp': track[i + 1]['timestamp'],
                        'position': {'lat': track[i + 1]['latitude'], 
                                   'lon': track[i + 1]['longitude']}
                    })
                elif prev_speed > 3 and speed < 1:  # Stop moving
                    events['stop'].append({
                        'timestamp': track[i + 1]['timestamp'],
                        'position': {'lat': track[i + 1]['latitude'], 
                                   'lon': track[i + 1]['longitude']}
                    })
        
        return events
    
    def _find_synchronized_events(self, vessel_events: Dict, event_type: str) -> List[Dict]:
        """Find synchronized events across vessels."""
        sync_events = []
        time_threshold_minutes = 30  # Events within 30 minutes are considered synchronized
        
        # Get all events of specified type
        all_events = []
        for vessel_id, events in vessel_events.items():
            for event in events.get(event_type, []):
                all_events.append({
                    'vessel_id': vessel_id,
                    'timestamp': datetime.fromisoformat(event['timestamp']),
                    'position': event['position']
                })
        
        # Sort by timestamp
        all_events.sort(key=lambda x: x['timestamp'])
        
        # Find groups of synchronized events
        i = 0
        while i < len(all_events):
            sync_group = [all_events[i]]
            base_time = all_events[i]['timestamp']
            
            # Find other events within time threshold
            j = i + 1
            while j < len(all_events):
                time_diff = (all_events[j]['timestamp'] - base_time).total_seconds() / 60
                if time_diff <= time_threshold_minutes:
                    sync_group.append(all_events[j])
                    j += 1
                else:
                    break
            
            # If we found synchronized events from multiple vessels
            if len(sync_group) >= 2:
                vessel_ids = list(set([event['vessel_id'] for event in sync_group]))
                if len(vessel_ids) >= 2:
                    sync_events.append({
                        'type': f'synchronized_{event_type}',
                        'vessels': vessel_ids,
                        'timestamp': base_time.isoformat(),
                        'event_count': len(sync_group),
                        'time_span_minutes': (sync_group[-1]['timestamp'] - base_time).total_seconds() / 60
                    })
            
            i = j if j > i + 1 else i + 1
        
        return sync_events
    
    def _find_movement_coordination(self, vessel_positions: Dict) -> List[Dict]:
        """Find coordinated movement patterns."""
        events = []
        
        # Look for vessels following similar routes
        vessel_ids = list(vessel_positions.keys())
        for i in range(len(vessel_ids)):
            for j in range(i + 1, len(vessel_ids)):
                vessel1_id = vessel_ids[i]
                vessel2_id = vessel_ids[j]
                
                track1 = vessel_positions[vessel1_id]
                track2 = vessel_positions[vessel2_id]
                
                # Calculate route similarity
                similarity = self._calculate_route_similarity(track1, track2)
                
                if similarity > 0.7:  # High similarity threshold
                    events.append({
                        'type': 'coordinated_movement',
                        'vessels': [vessel1_id, vessel2_id],
                        'route_similarity': similarity,
                        'timestamp': datetime.now().isoformat()
                    })
        
        return events
    
    def _calculate_route_similarity(self, track1: List[Dict], track2: List[Dict]) -> float:
        """Calculate similarity between two vessel routes."""
        if len(track1) < 2 or len(track2) < 2:
            return 0
        
        # Simplified similarity calculation based on position correlation
        # In practice, you'd use more sophisticated algorithms like DTW
        
        # Sample positions at regular intervals
        def sample_track(track, num_samples=10):
            if len(track) <= num_samples:
                return track
            
            step = len(track) // num_samples
            return [track[i * step] for i in range(num_samples)]
        
        samples1 = sample_track(track1)
        samples2 = sample_track(track2)
        
        # Calculate average distance between corresponding points
        if len(samples1) != len(samples2):
            return 0
        
        total_distance = 0
        for pos1, pos2 in zip(samples1, samples2):
            distance = geodesic(
                (pos1['latitude'], pos1['longitude']),
                (pos2['latitude'], pos2['longitude'])
            ).kilometers
            total_distance += distance
        
        average_distance = total_distance / len(samples1)
        
        # Convert to similarity score (0-1)
        # Closer routes have higher similarity
        similarity = max(0, 1 - (average_distance / 50))  # 50km normalization
        
        return similarity


if __name__ == "__main__":
    # Example usage
    analyzer = BehaviorPatternAnalyzer()
    
    # Example vessel track
    example_track = [
        {'latitude': 70.0, 'longitude': 30.0, 'timestamp': '2024-11-15T10:00:00'},
        {'latitude': 70.1, 'longitude': 30.1, 'timestamp': '2024-11-15T11:00:00'},
        {'latitude': 70.1, 'longitude': 30.1, 'timestamp': '2024-11-15T12:00:00'},  # Stationary
        {'latitude': 70.2, 'longitude': 30.2, 'timestamp': '2024-11-15T13:00:00'},
    ]
    
    # Analyze behavior
    analysis = analyzer.analyze_vessel_behavior('TEST_VESSEL', example_track)
    
    print(f"Behavior Analysis:")
    print(f"Pattern: {analysis['pattern_classification']['pattern']}")
    print(f"Suspicion Score: {analysis['suspicion_score']}")
    print(f"Risk Level: {analysis['behavioral_assessment']['risk_level']}")