"""
Simple pattern analysis for Arctic vessel behavior.
Clean implementation focused on educational clarity.
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


class VesselPatternAnalyzer:
    """Analyze vessel movement patterns and behavior."""
    
    def __init__(self):
        """Initialize pattern analyzer."""
        self.behavior_patterns = {
            'fishing': {'speed_range': (2, 8), 'pattern': 'irregular'},
            'transit': {'speed_range': (8, 20), 'pattern': 'linear'},
            'patrol': {'speed_range': (5, 15), 'pattern': 'repetitive'},
            'loitering': {'speed_range': (0, 3), 'pattern': 'stationary'}
        }
    
    def analyze_vessel_track(self, vessel_positions: pd.DataFrame) -> Dict:
        """
        Analyze a single vessel's movement track.
        
        Args:
            vessel_positions: DataFrame with vessel positions over time
            
        Returns:
            Analysis results for the vessel
        """
        if len(vessel_positions) < 2:
            return {'error': 'Insufficient position data'}
        
        # Sort by time
        positions = vessel_positions.sort_values('timestamp').copy()
        
        # Calculate movement features
        movement_stats = self._calculate_movement_statistics(positions)
        
        # Classify behavior
        behavior_classification = self._classify_behavior(movement_stats)
        
        # Detect patterns
        patterns = self._detect_movement_patterns(positions)
        
        # Calculate area of operation
        operating_area = self._calculate_operating_area(positions)
        
        analysis = {
            'vessel_id': positions['vessel_id'].iloc[0],
            'track_duration_hours': movement_stats['duration_hours'],
            'total_distance_km': movement_stats['total_distance'],
            'average_speed': movement_stats['avg_speed'],
            'max_speed': movement_stats['max_speed'],
            'speed_variance': movement_stats['speed_variance'],
            'behavior_classification': behavior_classification,
            'movement_patterns': patterns,
            'operating_area': operating_area,
            'position_count': len(positions)
        }
        
        return analysis
    
    def _calculate_movement_statistics(self, positions: pd.DataFrame) -> Dict:
        """Calculate basic movement statistics."""
        stats = {}
        
        # Time span
        start_time = positions['timestamp'].min()
        end_time = positions['timestamp'].max()
        stats['duration_hours'] = (end_time - start_time).total_seconds() / 3600
        
        # Calculate distances and speeds
        distances = []
        speeds = []
        
        for i in range(len(positions) - 1):
            pos1 = positions.iloc[i]
            pos2 = positions.iloc[i + 1]
            
            # Distance between consecutive points
            distance = geodesic(
                (pos1['latitude'], pos1['longitude']),
                (pos2['latitude'], pos2['longitude'])
            ).kilometers
            distances.append(distance)
            
            # Speed calculation
            time_diff = (pos2['timestamp'] - pos1['timestamp']).total_seconds() / 3600
            if time_diff > 0:
                speed = distance / time_diff
                speeds.append(speed)
        
        stats['total_distance'] = sum(distances)
        stats['avg_speed'] = np.mean(speeds) if speeds else 0
        stats['max_speed'] = np.max(speeds) if speeds else 0
        stats['speed_variance'] = np.var(speeds) if speeds else 0
        
        return stats
    
    def _classify_behavior(self, movement_stats: Dict) -> str:
        """Classify vessel behavior based on movement statistics."""
        avg_speed = movement_stats['avg_speed']
        speed_variance = movement_stats['speed_variance']
        
        # Simple rule-based classification
        if avg_speed < 3:
            return 'loitering'
        elif avg_speed > 15 and speed_variance < 5:
            return 'transit'
        elif speed_variance > 10:
            return 'fishing'
        elif 5 <= avg_speed <= 15:
            return 'patrol'
        else:
            return 'unknown'
    
    def _detect_movement_patterns(self, positions: pd.DataFrame) -> Dict:
        """Detect specific movement patterns."""
        patterns = {
            'is_circular': False,
            'is_linear': False,
            'revisits_locations': False,
            'has_stops': False
        }
        
        if len(positions) < 5:
            return patterns
        
        # Check for circular movement
        start_pos = (positions.iloc[0]['latitude'], positions.iloc[0]['longitude'])
        end_pos = (positions.iloc[-1]['latitude'], positions.iloc[-1]['longitude'])
        
        start_end_distance = geodesic(start_pos, end_pos).kilometers
        patterns['is_circular'] = start_end_distance < 2.0  # Within 2km
        
        # Check for linear movement
        total_distance = 0
        for i in range(len(positions) - 1):
            pos1 = positions.iloc[i]
            pos2 = positions.iloc[i + 1]
            distance = geodesic(
                (pos1['latitude'], pos1['longitude']),
                (pos2['latitude'], pos2['longitude'])
            ).kilometers
            total_distance += distance
        
        direct_distance = geodesic(start_pos, end_pos).kilometers
        if total_distance > 0:
            linearity = direct_distance / total_distance
            patterns['is_linear'] = linearity > 0.8
        
        # Check for stops (low speed periods)
        if 'speed' in positions.columns:
            low_speed_count = len(positions[positions['speed'] < 2])
            patterns['has_stops'] = low_speed_count > len(positions) * 0.2
        
        # Check for location revisits (simplified)
        unique_locations = len(positions.drop_duplicates(
            subset=['latitude', 'longitude'], 
            keep='first'
        ))
        patterns['revisits_locations'] = unique_locations < len(positions) * 0.8
        
        return patterns
    
    def _calculate_operating_area(self, positions: pd.DataFrame) -> Dict:
        """Calculate the vessel's operating area."""
        lats = positions['latitude']
        lons = positions['longitude']
        
        # Bounding box
        north = lats.max()
        south = lats.min()
        east = lons.max()
        west = lons.min()
        
        # Center point
        center_lat = lats.mean()
        center_lon = lons.mean()
        
        # Calculate distances from center
        distances_from_center = []
        for _, pos in positions.iterrows():
            distance = geodesic(
                (center_lat, center_lon),
                (pos['latitude'], pos['longitude'])
            ).kilometers
            distances_from_center.append(distance)
        
        area = {
            'bounding_box': {
                'north': north, 'south': south,
                'east': east, 'west': west
            },
            'center': {'latitude': center_lat, 'longitude': center_lon},
            'max_radius_km': max(distances_from_center) if distances_from_center else 0,
            'avg_radius_km': np.mean(distances_from_center) if distances_from_center else 0
        }
        
        return area


class FleetAnalyzer:
    """Analyze patterns across multiple vessels."""
    
    def __init__(self):
        """Initialize fleet analyzer."""
        pass
    
    def analyze_fleet_behavior(self, vessel_data: pd.DataFrame) -> Dict:
        """
        Analyze behavior patterns across a fleet of vessels.
        
        Args:
            vessel_data: DataFrame with multiple vessels' position data
            
        Returns:
            Fleet analysis results
        """
        if vessel_data.empty:
            return {'error': 'No vessel data provided'}
        
        # Group by vessel
        vessel_groups = vessel_data.groupby('vessel_id')
        
        # Analyze each vessel
        vessel_analyzer = VesselPatternAnalyzer()
        individual_analyses = {}
        
        for vessel_id, group in vessel_groups:
            analysis = vessel_analyzer.analyze_vessel_track(group)
            individual_analyses[vessel_id] = analysis
        
        # Fleet-wide statistics
        fleet_stats = self._calculate_fleet_statistics(individual_analyses)
        
        # Find interesting patterns
        fleet_patterns = self._detect_fleet_patterns(vessel_data, individual_analyses)
        
        analysis = {
            'fleet_size': len(individual_analyses),
            'analysis_period': {
                'start': vessel_data['timestamp'].min(),
                'end': vessel_data['timestamp'].max()
            },
            'fleet_statistics': fleet_stats,
            'fleet_patterns': fleet_patterns,
            'individual_vessels': individual_analyses
        }
        
        return analysis
    
    def _calculate_fleet_statistics(self, individual_analyses: Dict) -> Dict:
        """Calculate fleet-wide statistics."""
        valid_analyses = [a for a in individual_analyses.values() if 'error' not in a]
        
        if not valid_analyses:
            return {'error': 'No valid vessel analyses'}
        
        # Aggregate statistics
        speeds = [a['average_speed'] for a in valid_analyses]
        distances = [a['total_distance_km'] for a in valid_analyses]
        durations = [a['track_duration_hours'] for a in valid_analyses]
        
        # Behavior classification counts
        behaviors = [a['behavior_classification'] for a in valid_analyses]
        behavior_counts = {}
        for behavior in behaviors:
            behavior_counts[behavior] = behavior_counts.get(behavior, 0) + 1
        
        stats = {
            'average_speed': {
                'mean': np.mean(speeds),
                'median': np.median(speeds),
                'std': np.std(speeds)
            },
            'total_distance': {
                'mean': np.mean(distances),
                'total': sum(distances)
            },
            'track_duration': {
                'mean': np.mean(durations),
                'total': sum(durations)
            },
            'behavior_distribution': behavior_counts,
            'vessels_analyzed': len(valid_analyses)
        }
        
        return stats
    
    def _detect_fleet_patterns(self, vessel_data: pd.DataFrame, 
                              individual_analyses: Dict) -> Dict:
        """Detect patterns across the fleet."""
        patterns = {
            'coordinated_movement': [],
            'formation_sailing': [],
            'rendezvous_points': [],
            'synchronized_activities': []
        }
        
        # Find vessels operating in same area
        coordinated_vessels = self._find_coordinated_vessels(vessel_data)
        patterns['coordinated_movement'] = coordinated_vessels
        
        # Find potential rendezvous points
        rendezvous = self._find_rendezvous_points(vessel_data)
        patterns['rendezvous_points'] = rendezvous
        
        return patterns
    
    def _find_coordinated_vessels(self, vessel_data: pd.DataFrame, 
                                 distance_threshold: float = 5.0) -> List[Dict]:
        """Find vessels that appear to be coordinating their movements."""
        coordinated_groups = []
        
        # Group by time windows
        vessel_data['time_bucket'] = vessel_data['timestamp'].dt.floor('1H')
        
        for time_bucket, time_group in vessel_data.groupby('time_bucket'):
            if len(time_group) < 2:
                continue
            
            # Find vessels close to each other
            vessels_in_bucket = time_group.groupby('vessel_id').first()
            
            for i, (vessel1_id, vessel1) in enumerate(vessels_in_bucket.iterrows()):
                close_vessels = []
                
                for j, (vessel2_id, vessel2) in enumerate(vessels_in_bucket.iterrows()):
                    if i >= j:  # Skip self and already processed pairs
                        continue
                    
                    distance = geodesic(
                        (vessel1['latitude'], vessel1['longitude']),
                        (vessel2['latitude'], vessel2['longitude'])
                    ).kilometers
                    
                    if distance <= distance_threshold:
                        close_vessels.append({
                            'vessel_id': vessel2_id,
                            'distance_km': distance
                        })
                
                if close_vessels:
                    coordinated_groups.append({
                        'time': time_bucket,
                        'primary_vessel': vessel1_id,
                        'position': (vessel1['latitude'], vessel1['longitude']),
                        'coordinated_vessels': close_vessels
                    })
        
        return coordinated_groups
    
    def _find_rendezvous_points(self, vessel_data: pd.DataFrame) -> List[Dict]:
        """Find potential meeting points between vessels."""
        rendezvous_points = []
        
        # Simple approach: find locations where multiple vessels have been
        # within a small area at different times
        
        # Grid the area into cells
        lat_bins = np.arange(
            vessel_data['latitude'].min(),
            vessel_data['latitude'].max() + 0.1,
            0.1  # ~11km grid cells
        )
        lon_bins = np.arange(
            vessel_data['longitude'].min(),
            vessel_data['longitude'].max() + 0.1,
            0.1
        )
        
        # Assign each position to a grid cell
        vessel_data['lat_bin'] = pd.cut(vessel_data['latitude'], lat_bins)
        vessel_data['lon_bin'] = pd.cut(vessel_data['longitude'], lon_bins)
        
        # Find cells with multiple vessels
        for (lat_bin, lon_bin), group in vessel_data.groupby(['lat_bin', 'lon_bin']):
            unique_vessels = group['vessel_id'].nunique()
            
            if unique_vessels >= 3:  # At least 3 different vessels
                rendezvous_points.append({
                    'location': {
                        'latitude': group['latitude'].mean(),
                        'longitude': group['longitude'].mean()
                    },
                    'vessel_count': unique_vessels,
                    'vessels': group['vessel_id'].unique().tolist(),
                    'time_span': {
                        'start': group['timestamp'].min(),
                        'end': group['timestamp'].max()
                    }
                })
        
        return rendezvous_points


def create_sample_fleet_data(n_vessels: int = 10, 
                           duration_hours: int = 12) -> pd.DataFrame:
    """
    Create sample fleet data for testing.
    
    Args:
        n_vessels: Number of vessels to simulate
        duration_hours: Duration of simulation
        
    Returns:
        DataFrame with fleet position data
    """
    np.random.seed(42)
    
    all_positions = []
    base_time = datetime.now() - timedelta(hours=duration_hours)
    
    for vessel_idx in range(n_vessels):
        vessel_id = f"VESSEL_{vessel_idx:03d}"
        
        # Starting position
        start_lat = np.random.uniform(69.5, 71.5)
        start_lon = np.random.uniform(25.0, 35.0)
        
        # Simulate movement over time
        current_lat = start_lat
        current_lon = start_lon
        
        for hour in range(duration_hours):
            # Random walk with slight bias
            lat_change = np.random.normal(0, 0.02)
            lon_change = np.random.normal(0, 0.02)
            
            current_lat += lat_change
            current_lon += lon_change
            
            # Simulate speed
            speed = max(0, np.random.normal(8, 3))
            
            position = {
                'vessel_id': vessel_id,
                'latitude': current_lat,
                'longitude': current_lon,
                'speed': speed,
                'heading': np.random.uniform(0, 360),
                'timestamp': base_time + timedelta(hours=hour),
                'vessel_type': np.random.choice(['fishing', 'cargo', 'research'])
            }
            all_positions.append(position)
    
    return pd.DataFrame(all_positions)


def main():
    """Example usage of pattern analysis."""
    logger.info("=== Arctic Vessel Pattern Analysis Demo ===")
    
    # Create sample data
    logger.info("Generating sample fleet data...")
    fleet_data = create_sample_fleet_data(n_vessels=8, duration_hours=24)
    
    # Fleet analysis
    logger.info("Analyzing fleet patterns...")
    fleet_analyzer = FleetAnalyzer()
    fleet_analysis = fleet_analyzer.analyze_fleet_behavior(fleet_data)
    
    # Display results
    print(f"\n=== FLEET ANALYSIS RESULTS ===")
    print(f"Fleet size: {fleet_analysis['fleet_size']} vessels")
    
    stats = fleet_analysis['fleet_statistics']
    print(f"Average speed: {stats['average_speed']['mean']:.1f} ± {stats['average_speed']['std']:.1f} km/h")
    print(f"Total distance traveled: {stats['total_distance']['total']:.1f} km")
    
    print(f"\nBehavior distribution:")
    for behavior, count in stats['behavior_distribution'].items():
        print(f"  {behavior}: {count} vessels")
    
    # Pattern detection
    patterns = fleet_analysis['fleet_patterns']
    print(f"\nCoordinated movements: {len(patterns['coordinated_movement'])}")
    print(f"Rendezvous points: {len(patterns['rendezvous_points'])}")
    
    return fleet_analysis


if __name__ == "__main__":
    analysis = main()