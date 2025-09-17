"""
Simple risk scoring system for Arctic vessel analysis.
Educational implementation with clear logic and precise calculations.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleRiskScorer:
    """Simple, transparent risk scoring for vessel behavior assessment."""
    
    def __init__(self):
        """Initialize risk scorer with clear scoring rules."""
        
        # Risk factor weights (must sum to 1.0)
        self.weights = {
            'location': 0.25,       # Where the vessel is operating
            'behavior': 0.30,       # How the vessel is behaving
            'temporal': 0.20,       # When the vessel is operating
            'vessel_info': 0.25     # What we know about the vessel
        }
        
        # Scoring rules (0-10 scale)
        self.scoring_rules = {
            'location': {
                'arctic_bonus': 2.0,           # Operating in Arctic waters
                'shore_distance_penalty': 1.0, # Very close to shore
                'remote_bonus': 1.5            # Very remote location
            },
            'behavior': {
                'loitering_penalty': 3.0,      # Staying in one place
                'high_speed_penalty': 2.0,     # Unusually high speed
                'erratic_movement': 2.5,       # Unpredictable movement
                'normal_bonus': -1.0           # Normal behavior reduces risk
            },
            'temporal': {
                'night_penalty': 1.5,          # Operating at night
                'weekend_penalty': 0.5,        # Weekend operations
                'continuous_penalty': 1.0      # Operating continuously
            },
            'vessel_info': {
                'unknown_type_penalty': 2.0,   # Unknown vessel type
                'no_ais_penalty': 3.0,         # No AIS transponder
                'large_vessel_bonus': 1.0      # Large vessels easier to track
            }
        }
    
    def calculate_risk_score(self, vessel_data: Dict) -> Dict:
        """
        Calculate risk score for a single vessel.
        
        Args:
            vessel_data: Dictionary with vessel information
            
        Returns:
            Risk assessment with score and explanation
        """
        # Calculate component scores
        location_score = self._score_location_factors(vessel_data)
        behavior_score = self._score_behavior_factors(vessel_data)
        temporal_score = self._score_temporal_factors(vessel_data)
        vessel_score = self._score_vessel_factors(vessel_data)
        
        # Calculate weighted total
        total_score = (
            location_score * self.weights['location'] +
            behavior_score * self.weights['behavior'] +
            temporal_score * self.weights['temporal'] +
            vessel_score * self.weights['vessel_info']
        )
        
        # Ensure score is in 0-10 range
        total_score = max(0, min(10, total_score))
        
        # Determine risk level
        risk_level = self._determine_risk_level(total_score)
        
        result = {
            'vessel_id': vessel_data.get('vessel_id', 'unknown'),
            'total_risk_score': round(total_score, 2),
            'risk_level': risk_level,
            'component_scores': {
                'location': round(location_score, 2),
                'behavior': round(behavior_score, 2),
                'temporal': round(temporal_score, 2),
                'vessel_info': round(vessel_score, 2)
            },
            'risk_factors': self._identify_risk_factors(vessel_data),
            'assessment_time': datetime.now().isoformat()
        }
        
        return result
    
    def _score_location_factors(self, vessel_data: Dict) -> float:
        """Score location-related risk factors."""
        score = 0.0
        
        # Check if in Arctic waters
        latitude = vessel_data.get('latitude', 0)
        if latitude > 66.5:  # Arctic Circle
            score += self.scoring_rules['location']['arctic_bonus']
        
        # Distance to shore
        distance_to_shore = vessel_data.get('distance_to_shore', 100)
        if distance_to_shore < 5:  # Very close to shore
            score += self.scoring_rules['location']['shore_distance_penalty']
        elif distance_to_shore > 200:  # Very remote
            score += self.scoring_rules['location']['remote_bonus']
        
        return score
    
    def _score_behavior_factors(self, vessel_data: Dict) -> float:
        """Score behavior-related risk factors."""
        score = 0.0
        
        # Speed analysis
        speed = vessel_data.get('speed', 0)
        if speed < 2:  # Loitering
            score += self.scoring_rules['behavior']['loitering_penalty']
        elif speed > 25:  # Very high speed
            score += self.scoring_rules['behavior']['high_speed_penalty']
        elif 5 <= speed <= 15:  # Normal speed
            score += self.scoring_rules['behavior']['normal_bonus']
        
        # Movement pattern
        pattern = vessel_data.get('movement_pattern', 'unknown')
        if pattern in ['erratic', 'irregular']:
            score += self.scoring_rules['behavior']['erratic_movement']
        
        # Speed variance (indicates erratic behavior)
        speed_variance = vessel_data.get('speed_variance', 0)
        if speed_variance > 20:  # High variance
            score += self.scoring_rules['behavior']['erratic_movement'] * 0.5
        
        return score
    
    def _score_temporal_factors(self, vessel_data: Dict) -> float:
        """Score time-related risk factors."""
        score = 0.0
        
        # Time of day
        time_of_day = vessel_data.get('time_of_day', 12)
        if time_of_day < 6 or time_of_day > 22:  # Night time
            score += self.scoring_rules['temporal']['night_penalty']
        
        # Day of week
        day_of_week = vessel_data.get('day_of_week', 2)
        if day_of_week >= 5:  # Weekend
            score += self.scoring_rules['temporal']['weekend_penalty']
        
        # Continuous operation
        operation_duration = vessel_data.get('operation_duration_hours', 0)
        if operation_duration > 24:  # Operating over 24 hours
            score += self.scoring_rules['temporal']['continuous_penalty']
        
        return score
    
    def _score_vessel_factors(self, vessel_data: Dict) -> float:
        """Score vessel-specific factors."""
        score = 0.0
        
        # Vessel type
        vessel_type = vessel_data.get('vessel_type', 'unknown')
        if vessel_type == 'unknown':
            score += self.scoring_rules['vessel_info']['unknown_type_penalty']
        
        # AIS status
        has_ais = vessel_data.get('has_ais', True)
        if not has_ais:
            score += self.scoring_rules['vessel_info']['no_ais_penalty']
        
        # Vessel size
        vessel_length = vessel_data.get('vessel_length', 0)
        if vessel_length > 100:  # Large vessel
            score += self.scoring_rules['vessel_info']['large_vessel_bonus']
        
        return score
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level based on score."""
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
    
    def _identify_risk_factors(self, vessel_data: Dict) -> List[str]:
        """Identify specific risk factors present."""
        factors = []
        
        # Location factors
        latitude = vessel_data.get('latitude', 0)
        if latitude > 66.5:
            factors.append("Operating in Arctic waters")
        
        distance_to_shore = vessel_data.get('distance_to_shore', 100)
        if distance_to_shore < 5:
            factors.append("Very close to shore")
        elif distance_to_shore > 200:
            factors.append("Operating in remote area")
        
        # Behavior factors
        speed = vessel_data.get('speed', 0)
        if speed < 2:
            factors.append("Loitering behavior")
        elif speed > 25:
            factors.append("Unusually high speed")
        
        # Temporal factors
        time_of_day = vessel_data.get('time_of_day', 12)
        if time_of_day < 6 or time_of_day > 22:
            factors.append("Night-time operations")
        
        # Vessel factors
        if not vessel_data.get('has_ais', True):
            factors.append("No AIS transponder")
        
        if vessel_data.get('vessel_type', 'unknown') == 'unknown':
            factors.append("Unknown vessel type")
        
        return factors
    
    def score_vessel_fleet(self, fleet_data: List[Dict]) -> Dict:
        """
        Score multiple vessels and provide fleet analysis.
        
        Args:
            fleet_data: List of vessel data dictionaries
            
        Returns:
            Fleet risk analysis
        """
        if not fleet_data:
            return {'error': 'No vessel data provided'}
        
        # Score individual vessels
        vessel_scores = []
        for vessel_data in fleet_data:
            score_result = self.calculate_risk_score(vessel_data)
            vessel_scores.append(score_result)
        
        # Fleet statistics
        total_scores = [v['total_risk_score'] for v in vessel_scores]
        risk_levels = [v['risk_level'] for v in vessel_scores]
        
        # Count by risk level
        risk_level_counts = {}
        for level in risk_levels:
            risk_level_counts[level] = risk_level_counts.get(level, 0) + 1
        
        # Find highest risk vessels
        highest_risk_vessels = sorted(
            vessel_scores, 
            key=lambda x: x['total_risk_score'], 
            reverse=True
        )[:5]
        
        fleet_analysis = {
            'fleet_size': len(fleet_data),
            'average_risk_score': round(np.mean(total_scores), 2),
            'max_risk_score': round(np.max(total_scores), 2),
            'min_risk_score': round(np.min(total_scores), 2),
            'risk_level_distribution': risk_level_counts,
            'highest_risk_vessels': highest_risk_vessels,
            'fleet_risk_level': self._determine_fleet_risk_level(risk_level_counts),
            'analysis_time': datetime.now().isoformat(),
            'all_vessels': vessel_scores
        }
        
        return fleet_analysis
    
    def _determine_fleet_risk_level(self, risk_level_counts: Dict) -> str:
        """Determine overall fleet risk level."""
        critical_count = risk_level_counts.get('CRITICAL', 0)
        high_count = risk_level_counts.get('HIGH', 0)
        total_vessels = sum(risk_level_counts.values())
        
        if critical_count > 0:
            return 'CRITICAL'
        elif high_count > total_vessels * 0.3:  # More than 30% high risk
            return 'HIGH'
        elif high_count > 0:
            return 'MEDIUM'
        else:
            return 'LOW'


def create_sample_vessel_data(n_vessels: int = 20) -> List[Dict]:
    """
    Create sample vessel data for testing risk scoring.
    
    Args:
        n_vessels: Number of vessels to create
        
    Returns:
        List of vessel data dictionaries
    """
    np.random.seed(42)
    vessels = []
    
    vessel_types = ['fishing', 'cargo', 'tanker', 'passenger', 'research', 'unknown']
    
    for i in range(n_vessels):
        # Create diverse vessel scenarios
        vessel = {
            'vessel_id': f'VESSEL_{i:03d}',
            'latitude': np.random.uniform(69.0, 72.0),  # Arctic waters
            'longitude': np.random.uniform(20.0, 40.0),
            'speed': max(0, np.random.normal(8, 4)),
            'speed_variance': np.random.exponential(5),
            'heading': np.random.uniform(0, 360),
            'vessel_type': np.random.choice(vessel_types),
            'vessel_length': np.random.gamma(2, 30),
            'has_ais': np.random.choice([True, False], p=[0.8, 0.2]),
            'distance_to_shore': np.random.exponential(50),
            'time_of_day': np.random.uniform(0, 24),
            'day_of_week': np.random.randint(0, 7),
            'operation_duration_hours': np.random.exponential(12),
            'movement_pattern': np.random.choice(['regular', 'irregular', 'erratic'], p=[0.6, 0.3, 0.1])
        }
        
        # Create some deliberately high-risk vessels
        if i < 3:  # First 3 vessels are high-risk
            vessel.update({
                'speed': np.random.uniform(0, 2),  # Loitering
                'has_ais': False,  # No AIS
                'vessel_type': 'unknown',
                'time_of_day': np.random.uniform(1, 5),  # Night time
                'distance_to_shore': np.random.uniform(1, 3),  # Very close to shore
                'movement_pattern': 'erratic'
            })
        
        vessels.append(vessel)
    
    return vessels


def main():
    """Example usage of risk scoring system."""
    logger.info("=== Arctic Vessel Risk Scoring Demo ===")
    
    # Create sample data
    logger.info("Generating sample vessel data...")
    vessel_data = create_sample_vessel_data(15)
    
    # Initialize risk scorer
    scorer = SimpleRiskScorer()
    
    # Score fleet
    logger.info("Calculating risk scores...")
    fleet_analysis = scorer.score_vessel_fleet(vessel_data)
    
    # Display results
    print(f"\n=== FLEET RISK ANALYSIS ===")
    print(f"Fleet size: {fleet_analysis['fleet_size']} vessels")
    print(f"Average risk score: {fleet_analysis['average_risk_score']}/10")
    print(f"Fleet risk level: {fleet_analysis['fleet_risk_level']}")
    
    print(f"\nRisk level distribution:")
    for level, count in fleet_analysis['risk_level_distribution'].items():
        print(f"  {level}: {count} vessels")
    
    print(f"\nTop 5 highest risk vessels:")
    for i, vessel in enumerate(fleet_analysis['highest_risk_vessels']):
        print(f"  {i+1}. {vessel['vessel_id']}: {vessel['total_risk_score']}/10 ({vessel['risk_level']})")
        print(f"     Risk factors: {', '.join(vessel['risk_factors'])}")
    
    return fleet_analysis


if __name__ == "__main__":
    analysis = main()