"""
Simple vessel detection and tracking for Arctic maritime research.
Clean, functional implementation for educational purposes.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from geopy.distance import geodesic
from typing import List, Dict, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VesselDetector:
    """Simple vessel detection using AIS data and basic pattern recognition."""
    
    def __init__(self, proximity_threshold_km: float = 1.0):
        """
        Initialize vessel detector.
        
        Args:
            proximity_threshold_km: Distance threshold for vessel matching
        """
        self.proximity_threshold = proximity_threshold_km
        
    def detect_vessels_from_ais(self, ais_data: List[Dict]) -> pd.DataFrame:
        """
        Extract vessel information from AIS data.
        
        Args:
            ais_data: List of AIS messages
            
        Returns:
            DataFrame with vessel positions and info
        """
        if not ais_data:
            return pd.DataFrame()
        
        vessels = []
        for message in ais_data:
            vessel = {
                'vessel_id': message.get('mmsi', 'unknown'),
                'latitude': float(message.get('latitude', 0)),
                'longitude': float(message.get('longitude', 0)),
                'speed': float(message.get('speed_over_ground', 0)),
                'heading': float(message.get('course_over_ground', 0)),
                'timestamp': message.get('timestamp', datetime.now().isoformat()),
                'vessel_name': message.get('vessel_name', 'Unknown'),
                'vessel_type': message.get('ship_type', 'unknown')
            }
            vessels.append(vessel)
        
        df = pd.DataFrame(vessels)
        
        # Clean data
        df = df.dropna(subset=['latitude', 'longitude'])
        df = df[(df['latitude'] != 0) & (df['longitude'] != 0)]
        
        # Add derived features
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['time_of_day'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        
        logger.info(f"Processed {len(df)} vessel positions from AIS data")
        return df
    
    def calculate_vessel_features(self, vessel_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate additional features for each vessel.
        
        Args:
            vessel_df: DataFrame with vessel positions
            
        Returns:
            DataFrame with additional features
        """
        result_df = vessel_df.copy()
        
        # Calculate distance to shore (simplified - use latitude as proxy)
        result_df['distance_to_shore'] = np.abs(result_df['latitude'] - 70.0) * 111  # km
        
        # Calculate vessel length estimate (based on vessel type)
        type_to_length = {
            'fishing': 25, 'cargo': 100, 'tanker': 150, 
            'passenger': 80, 'other': 50, 'unknown': 40
        }
        result_df['vessel_length'] = result_df['vessel_type'].map(
            lambda x: type_to_length.get(str(x).lower(), 40)
        )
        
        # Speed categories
        result_df['speed_category'] = pd.cut(
            result_df['speed'], 
            bins=[0, 2, 8, 15, 25, 100], 
            labels=['stationary', 'slow', 'normal', 'fast', 'very_fast']
        )
        
        # Add Arctic zone indicator
        result_df['in_arctic'] = result_df['latitude'] > 66.5
        
        return result_df
    
    def find_vessel_clusters(self, vessel_df: pd.DataFrame, 
                           time_window_minutes: int = 30) -> List[Dict]:
        """
        Find clusters of vessels that might be operating together.
        
        Args:
            vessel_df: DataFrame with vessel positions
            time_window_minutes: Time window for clustering
            
        Returns:
            List of vessel clusters
        """
        clusters = []
        
        if len(vessel_df) < 2:
            return clusters
        
        # Group by time windows
        vessel_df = vessel_df.sort_values('timestamp')
        
        # Simple clustering based on proximity
        for i, vessel1 in vessel_df.iterrows():
            nearby_vessels = []
            
            for j, vessel2 in vessel_df.iterrows():
                if i >= j:  # Skip self and already processed
                    continue
                
                # Check time proximity
                time_diff = abs((vessel1['timestamp'] - vessel2['timestamp']).total_seconds() / 60)
                if time_diff > time_window_minutes:
                    continue
                
                # Check spatial proximity
                distance = geodesic(
                    (vessel1['latitude'], vessel1['longitude']),
                    (vessel2['latitude'], vessel2['longitude'])
                ).kilometers
                
                if distance <= self.proximity_threshold:
                    nearby_vessels.append({
                        'vessel_id': vessel2['vessel_id'],
                        'distance_km': distance,
                        'time_diff_minutes': time_diff
                    })
            
            if nearby_vessels:
                cluster = {
                    'center_vessel': vessel1['vessel_id'],
                    'center_position': (vessel1['latitude'], vessel1['longitude']),
                    'timestamp': vessel1['timestamp'],
                    'nearby_vessels': nearby_vessels,
                    'cluster_size': len(nearby_vessels) + 1
                }
                clusters.append(cluster)
        
        logger.info(f"Found {len(clusters)} vessel clusters")
        return clusters
    
    def analyze_vessel_patterns(self, vessel_df: pd.DataFrame) -> Dict:
        """
        Analyze patterns in vessel behavior.
        
        Args:
            vessel_df: DataFrame with vessel data
            
        Returns:
            Analysis results
        """
        if vessel_df.empty:
            return {'error': 'No vessel data provided'}
        
        analysis = {
            'total_vessels': len(vessel_df),
            'unique_vessels': vessel_df['vessel_id'].nunique(),
            'time_span': {
                'start': vessel_df['timestamp'].min(),
                'end': vessel_df['timestamp'].max(),
                'duration_hours': (vessel_df['timestamp'].max() - 
                                 vessel_df['timestamp'].min()).total_seconds() / 3600
            },
            'geographic_bounds': {
                'north': vessel_df['latitude'].max(),
                'south': vessel_df['latitude'].min(),
                'east': vessel_df['longitude'].max(),
                'west': vessel_df['longitude'].min()
            },
            'speed_statistics': {
                'mean_speed': vessel_df['speed'].mean(),
                'max_speed': vessel_df['speed'].max(),
                'stationary_vessels': len(vessel_df[vessel_df['speed'] < 2])
            },
            'vessel_types': vessel_df['vessel_type'].value_counts().to_dict(),
            'arctic_vessels': len(vessel_df[vessel_df['in_arctic'] == True])
        }
        
        return analysis


class PatternDetector:
    """Detect specific behavioral patterns in vessel data."""
    
    def __init__(self):
        """Initialize pattern detector."""
        pass
    
    def detect_loitering(self, vessel_df: pd.DataFrame, 
                        speed_threshold: float = 2.0,
                        duration_threshold_hours: float = 2.0) -> List[Dict]:
        """
        Detect vessels that are loitering (staying in one area).
        
        Args:
            vessel_df: Vessel position data
            speed_threshold: Maximum speed to consider stationary
            duration_threshold_hours: Minimum duration to flag as loitering
            
        Returns:
            List of loitering incidents
        """
        loitering_incidents = []
        
        # Group by vessel
        for vessel_id, group in vessel_df.groupby('vessel_id'):
            group = group.sort_values('timestamp')
            
            # Find periods of low speed
            low_speed = group[group['speed'] <= speed_threshold]
            
            if len(low_speed) < 2:
                continue
            
            # Check if low speed period is long enough
            duration = (low_speed['timestamp'].max() - low_speed['timestamp'].min()).total_seconds() / 3600
            
            if duration >= duration_threshold_hours:
                # Calculate average position during loitering
                avg_lat = low_speed['latitude'].mean()
                avg_lon = low_speed['longitude'].mean()
                
                incident = {
                    'vessel_id': vessel_id,
                    'start_time': low_speed['timestamp'].min(),
                    'end_time': low_speed['timestamp'].max(),
                    'duration_hours': duration,
                    'average_position': (avg_lat, avg_lon),
                    'position_count': len(low_speed),
                    'average_speed': low_speed['speed'].mean()
                }
                loitering_incidents.append(incident)
        
        logger.info(f"Detected {len(loitering_incidents)} loitering incidents")
        return loitering_incidents
    
    def detect_unusual_speeds(self, vessel_df: pd.DataFrame) -> List[Dict]:
        """
        Detect vessels with unusual speed patterns.
        
        Args:
            vessel_df: Vessel data
            
        Returns:
            List of unusual speed incidents
        """
        unusual_speeds = []
        
        # Calculate speed statistics
        mean_speed = vessel_df['speed'].mean()
        std_speed = vessel_df['speed'].std()
        
        # Define thresholds (statistical outliers)
        high_threshold = mean_speed + 2 * std_speed
        
        # Find unusual speeds
        for _, vessel in vessel_df.iterrows():
            if vessel['speed'] > high_threshold:
                incident = {
                    'vessel_id': vessel['vessel_id'],
                    'timestamp': vessel['timestamp'],
                    'position': (vessel['latitude'], vessel['longitude']),
                    'speed': vessel['speed'],
                    'threshold': high_threshold,
                    'severity': 'high' if vessel['speed'] > high_threshold * 1.5 else 'medium'
                }
                unusual_speeds.append(incident)
        
        logger.info(f"Detected {len(unusual_speeds)} unusual speed incidents")
        return unusual_speeds
    
    def detect_night_activity(self, vessel_df: pd.DataFrame) -> List[Dict]:
        """
        Detect vessels active during night hours.
        
        Args:
            vessel_df: Vessel data
            
        Returns:
            List of night activity incidents
        """
        # Define night hours (simplified for Arctic - would need seasonal adjustment)
        night_hours = [22, 23, 0, 1, 2, 3, 4, 5]
        
        night_vessels = vessel_df[vessel_df['time_of_day'].isin(night_hours)]
        
        incidents = []
        for vessel_id, group in night_vessels.groupby('vessel_id'):
            # Only flag if significant activity at night
            if len(group) >= 3:  # At least 3 position reports
                incident = {
                    'vessel_id': vessel_id,
                    'night_positions': len(group),
                    'time_span': {
                        'start': group['timestamp'].min(),
                        'end': group['timestamp'].max()
                    },
                    'average_speed': group['speed'].mean(),
                    'positions': group[['latitude', 'longitude', 'timestamp']].to_dict('records')
                }
                incidents.append(incident)
        
        logger.info(f"Detected {len(incidents)} night activity incidents")
        return incidents


def create_sample_ais_data(n_vessels: int = 50, n_positions_per_vessel: int = 10) -> List[Dict]:
    """
    Create sample AIS data for testing.
    
    Args:
        n_vessels: Number of vessels to simulate
        n_positions_per_vessel: Position reports per vessel
        
    Returns:
        List of AIS messages
    """
    np.random.seed(42)
    ais_messages = []
    
    base_time = datetime.now() - timedelta(hours=24)
    
    for vessel_idx in range(n_vessels):
        vessel_id = f"12345{vessel_idx:03d}"
        
        # Random starting position in Arctic waters
        base_lat = np.random.uniform(69.0, 72.0)
        base_lon = np.random.uniform(20.0, 40.0)
        
        # Vessel characteristics
        vessel_types = ['fishing', 'cargo', 'tanker', 'passenger', 'other']
        vessel_type = np.random.choice(vessel_types)
        
        for pos_idx in range(n_positions_per_vessel):
            # Simulate vessel movement
            lat_offset = np.random.normal(0, 0.01)  # Small random movement
            lon_offset = np.random.normal(0, 0.01)
            
            # Time progression
            time_offset = timedelta(minutes=pos_idx * 30 + np.random.randint(-10, 10))
            
            message = {
                'mmsi': vessel_id,
                'latitude': base_lat + lat_offset,
                'longitude': base_lon + lon_offset,
                'speed_over_ground': max(0, np.random.normal(8, 3)),  # Realistic speed
                'course_over_ground': np.random.uniform(0, 360),
                'timestamp': (base_time + time_offset).isoformat(),
                'vessel_name': f"Test Vessel {vessel_idx}",
                'ship_type': vessel_type
            }
            ais_messages.append(message)
    
    return ais_messages


def main():
    """Example usage of vessel detection system."""
    logger.info("=== Arctic Vessel Detection Demo ===")
    
    # Create sample AIS data
    logger.info("Generating sample AIS data...")
    ais_data = create_sample_ais_data(n_vessels=20, n_positions_per_vessel=15)
    
    # Initialize detector
    detector = VesselDetector(proximity_threshold_km=2.0)
    
    # Process AIS data
    logger.info("Processing vessel positions...")
    vessel_df = detector.detect_vessels_from_ais(ais_data)
    vessel_df = detector.calculate_vessel_features(vessel_df)
    
    # Analyze patterns
    logger.info("Analyzing vessel patterns...")
    analysis = detector.analyze_vessel_patterns(vessel_df)
    
    print(f"\n=== ANALYSIS RESULTS ===")
    print(f"Total vessel positions: {analysis['total_vessels']}")
    print(f"Unique vessels: {analysis['unique_vessels']}")
    print(f"Vessels in Arctic: {analysis['arctic_vessels']}")
    print(f"Average speed: {analysis['speed_statistics']['mean_speed']:.1f} knots")
    print(f"Stationary vessels: {analysis['speed_statistics']['stationary_vessels']}")
    
    # Find clusters
    clusters = detector.find_vessel_clusters(vessel_df, time_window_minutes=60)
    print(f"Vessel clusters found: {len(clusters)}")
    
    # Pattern detection
    pattern_detector = PatternDetector()
    
    loitering = pattern_detector.detect_loitering(vessel_df)
    unusual_speeds = pattern_detector.detect_unusual_speeds(vessel_df)
    night_activity = pattern_detector.detect_night_activity(vessel_df)
    
    print(f"\n=== PATTERN DETECTION ===")
    print(f"Loitering incidents: {len(loitering)}")
    print(f"Unusual speed incidents: {len(unusual_speeds)}")
    print(f"Night activity incidents: {len(night_activity)}")
    
    return vessel_df, analysis, clusters


if __name__ == "__main__":
    vessel_df, analysis, clusters = main()