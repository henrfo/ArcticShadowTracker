"""
Pattern learning module for maritime behavioral analysis.

This module implements various machine learning approaches to learn and classify
patterns in vessel behavior, including movement patterns, temporal patterns,
and interaction patterns with infrastructure.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import joblib
from datetime import datetime, timedelta


class VesselPatternLearner:
    """
    Learn and classify patterns in vessel behavior using multiple ML approaches.
    """
    
    def __init__(self):
        self.movement_clusterer = None
        self.temporal_clusterer = None
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.behavior_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.patterns = {}
        
    def extract_movement_features(self, vessel_tracks):
        """
        Extract movement pattern features from vessel tracks.
        
        Args:
            vessel_tracks (list): List of vessel position tracks
            
        Returns:
            np.array: Movement feature matrix
        """
        features = []
        
        for track in vessel_tracks:
            if len(track) < 2:
                continue
                
            # Calculate basic movement statistics
            speeds = [self._calculate_speed(track[i], track[i+1]) 
                     for i in range(len(track)-1)]
            headings = [self._calculate_heading(track[i], track[i+1]) 
                       for i in range(len(track)-1)]
            
            # Movement features
            track_features = [
                np.mean(speeds),                    # Average speed
                np.std(speeds),                     # Speed variability
                np.max(speeds),                     # Maximum speed
                len([s for s in speeds if s < 1]),  # Time spent stationary
                self._calculate_track_length(track), # Total distance
                self._calculate_sinuosity(track),    # Path complexity
                np.std(headings),                   # Heading variability
                len(track),                         # Number of positions
                self._calculate_area_coverage(track), # Area covered
                self._detect_looping_behavior(track)  # Circular patterns
            ]
            
            features.append(track_features)
        
        return np.array(features)
    
    def extract_temporal_features(self, vessel_activities):
        """
        Extract temporal pattern features from vessel activities.
        
        Args:
            vessel_activities (list): List of timestamped vessel activities
            
        Returns:
            np.array: Temporal feature matrix
        """
        features = []
        
        for activity_log in vessel_activities:
            if not activity_log:
                continue
                
            timestamps = [datetime.fromisoformat(entry['timestamp']) 
                         for entry in activity_log]
            
            # Temporal features
            temporal_features = [
                self._hour_of_day_pattern(timestamps),      # Peak activity hour
                self._day_of_week_pattern(timestamps),      # Peak activity day
                self._activity_duration_pattern(timestamps), # Typical session length
                self._regularity_score(timestamps),         # How regular the pattern is
                len(timestamps),                            # Total activities
                self._night_activity_ratio(timestamps),     # Ratio of night activities
                self._weekend_activity_ratio(timestamps),   # Weekend vs weekday
                self._seasonal_pattern(timestamps),         # Seasonal preferences
                self._burst_activity_detection(timestamps), # Sudden activity spikes
                self._dormancy_periods(timestamps)          # Long inactive periods
            ]
            
            features.append(temporal_features)
        
        return np.array(features)
    
    def learn_movement_patterns(self, vessel_tracks, n_clusters=5):
        """
        Learn movement patterns using clustering.
        
        Args:
            vessel_tracks (list): Vessel movement tracks
            n_clusters (int): Number of movement pattern clusters
        """
        movement_features = self.extract_movement_features(vessel_tracks)
        movement_features_scaled = self.scaler.fit_transform(movement_features)
        
        # Use K-means for movement pattern clustering
        self.movement_clusterer = KMeans(n_clusters=n_clusters, random_state=42)
        movement_labels = self.movement_clusterer.fit_predict(movement_features_scaled)
        
        # Interpret movement patterns
        self.patterns['movement'] = self._interpret_movement_clusters(
            movement_features, movement_labels, n_clusters
        )
        
        return movement_labels
    
    def learn_temporal_patterns(self, vessel_activities):
        """
        Learn temporal patterns using clustering.
        
        Args:
            vessel_activities (list): Timestamped vessel activities
        """
        temporal_features = self.extract_temporal_features(vessel_activities)
        temporal_features_scaled = self.scaler.fit_transform(temporal_features)
        
        # Use DBSCAN for temporal pattern clustering (can find variable clusters)
        self.temporal_clusterer = DBSCAN(eps=0.5, min_samples=5)
        temporal_labels = self.temporal_clusterer.fit_predict(temporal_features_scaled)
        
        # Interpret temporal patterns
        self.patterns['temporal'] = self._interpret_temporal_clusters(
            temporal_features, temporal_labels
        )
        
        return temporal_labels
    
    def detect_anomalous_patterns(self, vessel_data):
        """
        Detect anomalous patterns using isolation forest.
        
        Args:
            vessel_data (np.array): Combined vessel feature data
            
        Returns:
            np.array: Anomaly labels (-1 for anomaly, 1 for normal)
        """
        vessel_data_scaled = self.scaler.transform(vessel_data)
        anomaly_labels = self.anomaly_detector.fit_predict(vessel_data_scaled)
        
        return anomaly_labels
    
    def classify_vessel_behavior(self, vessel_features, behavior_labels):
        """
        Train a classifier to categorize vessel behavior types.
        
        Args:
            vessel_features (np.array): Feature matrix
            behavior_labels (list): Behavior type labels
        """
        vessel_features_scaled = self.scaler.fit_transform(vessel_features)
        self.behavior_classifier.fit(vessel_features_scaled, behavior_labels)
        
        # Store feature importance
        self.patterns['feature_importance'] = {
            'features': ['speed_mean', 'speed_std', 'speed_max', 'stationary_time',
                        'track_length', 'sinuosity', 'heading_var', 'n_positions',
                        'area_coverage', 'looping_behavior'],
            'importance': self.behavior_classifier.feature_importances_
        }
    
    def predict_vessel_type(self, vessel_features):
        """
        Predict vessel behavior type for new data.
        
        Args:
            vessel_features (np.array): Feature vector for vessel
            
        Returns:
            str: Predicted behavior type
        """
        vessel_features_scaled = self.scaler.transform(vessel_features.reshape(1, -1))
        prediction = self.behavior_classifier.predict(vessel_features_scaled)
        probability = self.behavior_classifier.predict_proba(vessel_features_scaled)
        
        return {
            'predicted_type': prediction[0],
            'confidence': np.max(probability),
            'probabilities': dict(zip(self.behavior_classifier.classes_, probability[0]))
        }
    
    def _calculate_speed(self, pos1, pos2):
        """Calculate speed between two positions."""
        distance = self._haversine_distance(pos1['lat'], pos1['lon'], 
                                           pos2['lat'], pos2['lon'])
        time_diff = (datetime.fromisoformat(pos2['timestamp']) - 
                    datetime.fromisoformat(pos1['timestamp'])).total_seconds() / 3600
        return distance / time_diff if time_diff > 0 else 0
    
    def _calculate_heading(self, pos1, pos2):
        """Calculate heading between two positions."""
        lat1, lon1 = np.radians(pos1['lat']), np.radians(pos1['lon'])
        lat2, lon2 = np.radians(pos2['lat']), np.radians(pos2['lon'])
        
        dlon = lon2 - lon1
        y = np.sin(dlon) * np.cos(lat2)
        x = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dlon)
        
        heading = np.arctan2(y, x)
        return np.degrees(heading) % 360
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        """Calculate haversine distance between two points."""
        R = 6371  # Earth's radius in km
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
        return 2 * R * np.arcsin(np.sqrt(a))
    
    def _calculate_track_length(self, track):
        """Calculate total track length."""
        total_length = 0
        for i in range(len(track) - 1):
            total_length += self._haversine_distance(
                track[i]['lat'], track[i]['lon'],
                track[i+1]['lat'], track[i+1]['lon']
            )
        return total_length
    
    def _calculate_sinuosity(self, track):
        """Calculate track sinuosity (path complexity)."""
        if len(track) < 3:
            return 0
        
        track_length = self._calculate_track_length(track)
        straight_distance = self._haversine_distance(
            track[0]['lat'], track[0]['lon'],
            track[-1]['lat'], track[-1]['lon']
        )
        
        return track_length / straight_distance if straight_distance > 0 else float('inf')
    
    def _calculate_area_coverage(self, track):
        """Calculate area covered by the track."""
        if len(track) < 3:
            return 0
        
        lats = [pos['lat'] for pos in track]
        lons = [pos['lon'] for pos in track]
        
        # Simple bounding box area
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        
        return lat_range * lon_range
    
    def _detect_looping_behavior(self, track):
        """Detect circular/looping movement patterns."""
        if len(track) < 4:
            return 0
        
        # Count how many times vessel returns to similar positions
        loop_count = 0
        for i, pos1 in enumerate(track[:-3]):
            for j in range(i+3, len(track)):
                distance = self._haversine_distance(
                    pos1['lat'], pos1['lon'],
                    track[j]['lat'], track[j]['lon']
                )
                if distance < 0.5:  # Within 500m
                    loop_count += 1
                    break
        
        return loop_count / len(track)
    
    def _hour_of_day_pattern(self, timestamps):
        """Find peak activity hour."""
        hours = [ts.hour for ts in timestamps]
        return max(set(hours), key=hours.count) if hours else 12
    
    def _day_of_week_pattern(self, timestamps):
        """Find peak activity day of week."""
        days = [ts.weekday() for ts in timestamps]
        return max(set(days), key=days.count) if days else 0
    
    def _activity_duration_pattern(self, timestamps):
        """Calculate typical activity session duration."""
        if len(timestamps) < 2:
            return 0
        
        gaps = [(timestamps[i+1] - timestamps[i]).total_seconds() / 3600 
                for i in range(len(timestamps)-1)]
        
        # Sessions separated by gaps > 4 hours
        session_gaps = [gap for gap in gaps if gap > 4]
        return np.mean(session_gaps) if session_gaps else np.mean(gaps)
    
    def _regularity_score(self, timestamps):
        """Calculate how regular the activity pattern is."""
        if len(timestamps) < 3:
            return 0
        
        intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() 
                    for i in range(len(timestamps)-1)]
        return 1 / (1 + np.std(intervals) / np.mean(intervals)) if intervals else 0
    
    def _night_activity_ratio(self, timestamps):
        """Calculate ratio of night-time activities."""
        night_activities = sum(1 for ts in timestamps if ts.hour < 6 or ts.hour > 22)
        return night_activities / len(timestamps) if timestamps else 0
    
    def _weekend_activity_ratio(self, timestamps):
        """Calculate ratio of weekend activities."""
        weekend_activities = sum(1 for ts in timestamps if ts.weekday() >= 5)
        return weekend_activities / len(timestamps) if timestamps else 0
    
    def _seasonal_pattern(self, timestamps):
        """Identify seasonal pattern preference."""
        if not timestamps:
            return 0
        
        months = [ts.month for ts in timestamps]
        return max(set(months), key=months.count)
    
    def _burst_activity_detection(self, timestamps):
        """Detect sudden activity bursts."""
        if len(timestamps) < 5:
            return 0
        
        # Calculate activity density in 24-hour windows
        timestamps.sort()
        burst_count = 0
        
        for i in range(len(timestamps) - 4):
            window_end = timestamps[i] + timedelta(hours=24)
            activities_in_window = sum(1 for ts in timestamps[i:] if ts <= window_end)
            
            if activities_in_window >= 5:  # 5+ activities in 24h = burst
                burst_count += 1
        
        return burst_count / len(timestamps)
    
    def _dormancy_periods(self, timestamps):
        """Calculate average dormancy period length."""
        if len(timestamps) < 2:
            return 0
        
        gaps = [(timestamps[i+1] - timestamps[i]).total_seconds() / (24 * 3600) 
                for i in range(len(timestamps)-1)]
        
        # Dormancy = gaps > 7 days
        dormancy_periods = [gap for gap in gaps if gap > 7]
        return np.mean(dormancy_periods) if dormancy_periods else 0
    
    def _interpret_movement_clusters(self, features, labels, n_clusters):
        """Interpret movement pattern clusters."""
        patterns = {}
        
        for cluster_id in range(n_clusters):
            cluster_features = features[labels == cluster_id]
            if len(cluster_features) == 0:
                continue
            
            avg_features = np.mean(cluster_features, axis=0)
            
            # Interpret based on feature values
            if avg_features[0] < 5:  # Low speed
                if avg_features[3] > 0.5:  # High stationary time
                    pattern_type = "Loitering/Fishing"
                else:
                    pattern_type = "Slow Transit"
            elif avg_features[0] > 15:  # High speed
                pattern_type = "Fast Transit/Military"
            elif avg_features[5] > 2:  # High sinuosity
                pattern_type = "Search Pattern"
            else:
                pattern_type = "Regular Navigation"
            
            patterns[cluster_id] = {
                'type': pattern_type,
                'avg_speed': avg_features[0],
                'stationary_ratio': avg_features[3],
                'sinuosity': avg_features[5],
                'sample_count': len(cluster_features)
            }
        
        return patterns
    
    def _interpret_temporal_clusters(self, features, labels):
        """Interpret temporal pattern clusters."""
        patterns = {}
        unique_labels = set(labels)
        
        for cluster_id in unique_labels:
            if cluster_id == -1:  # DBSCAN noise
                continue
                
            cluster_features = features[labels == cluster_id]
            if len(cluster_features) == 0:
                continue
            
            avg_features = np.mean(cluster_features, axis=0)
            
            # Interpret based on temporal features
            if avg_features[5] > 0.5:  # High night activity
                pattern_type = "Night Operations"
            elif avg_features[6] > 0.7:  # High weekend activity
                pattern_type = "Recreational/Weekend"
            elif avg_features[3] > 0.8:  # High regularity
                pattern_type = "Scheduled Operations"
            else:
                pattern_type = "Irregular Activity"
            
            patterns[cluster_id] = {
                'type': pattern_type,
                'peak_hour': int(avg_features[0]),
                'night_ratio': avg_features[5],
                'weekend_ratio': avg_features[6],
                'regularity': avg_features[3],
                'sample_count': len(cluster_features)
            }
        
        return patterns
    
    def save_model(self, filepath):
        """Save all trained models."""
        joblib.dump({
            'movement_clusterer': self.movement_clusterer,
            'temporal_clusterer': self.temporal_clusterer,
            'anomaly_detector': self.anomaly_detector,
            'behavior_classifier': self.behavior_classifier,
            'scaler': self.scaler,
            'patterns': self.patterns
        }, f"{filepath}_pattern_learner.pkl")
    
    def load_model(self, filepath):
        """Load trained models."""
        models = joblib.load(f"{filepath}_pattern_learner.pkl")
        self.movement_clusterer = models['movement_clusterer']
        self.temporal_clusterer = models['temporal_clusterer']
        self.anomaly_detector = models['anomaly_detector']
        self.behavior_classifier = models['behavior_classifier']
        self.scaler = models['scaler']
        self.patterns = models['patterns']