"""
Test suite for risk scoring functionality.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

# Add parent directory to path for imports
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.risk_scoring import RiskScorer


class TestRiskScorer:
    """Test class for RiskScorer."""
    
    @pytest.fixture
    def scorer(self):
        """Create a risk scorer instance for testing."""
        return RiskScorer()
    
    @pytest.fixture
    def sample_vessel_data(self):
        """Sample vessel data for comprehensive testing."""
        return {
            'vessel_id': 'TEST_VESSEL_001',
            'latitude': 69.15,
            'longitude': 33.35,
            'estimated_length': 120,
            'vessel_type': 'cargo',
            'nationality': 'NO',
            'ais_data': {
                'mmsi': '123456789',
                'speed_over_ground': 12
            },
            'imo_number': '1234567',
            'mmsi': '123456789',
            'behavior_analysis': {
                'pattern_classification': {
                    'pattern': 'normal_transit',
                    'confidence': 0.85
                },
                'anomalies': [],
                'movement_features': {
                    'speed_variance': 25,
                    'turning_frequency': 0.1,
                    'stationary_periods': 0.05
                }
            },
            'vessel_history': {
                'ais_gaps_count': 2,
                'suspicious_meetings': 0
            },
            'distance_to_port': 45000,
            'in_territorial_waters': True,
            'restricted_zone_violations': []
        }
    
    @pytest.fixture
    def high_risk_vessel_data(self):
        """Sample high-risk vessel data for testing."""
        return {
            'vessel_id': 'SUSPICIOUS_001',
            'latitude': 69.15,
            'longitude': 33.35,
            'estimated_length': 150,
            'vessel_type': 'unknown',
            'nationality': 'UNKNOWN',
            'ais_data': None,  # Dark vessel
            'behavior_analysis': {
                'pattern_classification': {
                    'pattern': 'surveillance_pattern',
                    'confidence': 0.3  # Low confidence
                },
                'anomalies': [
                    {'type': 'suspicious_stop', 'severity': 'high'},
                    {'type': 'communication_gap', 'severity': 'medium'}
                ],
                'movement_features': {
                    'speed_variance': 150,  # High variance
                    'turning_frequency': 0.6,  # Frequent turns
                    'stationary_periods': 0.5  # Lots of loitering
                }
            },
            'vessel_history': {
                'ais_gaps_count': 15,  # Many gaps
                'suspicious_meetings': 3
            },
            'distance_to_port': 200000,  # Very far from port
            'in_territorial_waters': False,
            'restricted_zone_violations': [
                {'alert_level': 'critical', 'zone_name': 'Military Zone A'}
            ],
            'jamming_detected': True,
            'spoofing_detected': True
        }
    
    def test_initialization(self, scorer):
        """Test scorer initialization."""
        assert scorer.risk_weights is not None
        assert len(scorer.risk_weights) == 5
        assert scorer.critical_infrastructure is not None
        assert scorer.threat_matrices is not None
        assert scorer.logger is not None
    
    def test_risk_weights_sum_to_one(self, scorer):
        """Test that risk weights sum to 1.0."""
        total_weight = sum(scorer.risk_weights.values())
        assert abs(total_weight - 1.0) < 0.01  # Allow for small floating point errors
    
    def test_score_vessel_characteristics_normal(self, scorer, sample_vessel_data):
        """Test vessel characteristics scoring for normal vessel."""
        result = scorer._score_vessel_characteristics(sample_vessel_data)
        
        assert 'score' in result
        assert 'risk_factors' in result
        assert 'mitigating_factors' in result
        assert 'details' in result
        
        assert 0 <= result['score'] <= 10
        assert isinstance(result['risk_factors'], list)
        assert isinstance(result['mitigating_factors'], list)
    
    def test_score_vessel_characteristics_high_risk(self, scorer, high_risk_vessel_data):
        """Test vessel characteristics scoring for high-risk vessel."""
        result = scorer._score_vessel_characteristics(high_risk_vessel_data)
        
        assert result['score'] > 5  # Should be high risk
        assert len(result['risk_factors']) > 0
        assert 'dark vessel' in ' '.join(result['risk_factors']).lower()
    
    def test_score_behavioral_patterns_normal(self, scorer, sample_vessel_data):
        """Test behavioral pattern scoring for normal vessel."""
        result = scorer._score_behavioral_patterns(sample_vessel_data)
        
        assert 'score' in result
        assert 'risk_factors' in result
        assert 'mitigating_factors' in result
        
        assert result['score'] < 5  # Should be low risk for normal behavior
    
    def test_score_behavioral_patterns_suspicious(self, scorer, high_risk_vessel_data):
        """Test behavioral pattern scoring for suspicious vessel."""
        result = scorer._score_behavioral_patterns(high_risk_vessel_data)
        
        assert result['score'] > 5  # Should be high risk
        assert len(result['risk_factors']) > 0
    
    def test_score_location_context(self, scorer, sample_vessel_data):
        """Test location context scoring."""
        result = scorer._score_location_context(sample_vessel_data)
        
        assert 'score' in result
        assert 'risk_factors' in result
        assert 'mitigating_factors' in result
        assert 'details' in result
        
        assert 0 <= result['score'] <= 10
    
    def test_score_location_context_near_infrastructure(self, scorer):
        """Test location scoring when near critical infrastructure."""
        vessel_near_severomorsk = {
            'latitude': 69.07,  # Near Severomorsk naval base
            'longitude': 33.42,
            'distance_to_port': 10000,
            'in_territorial_waters': False,
            'restricted_zone_violations': []
        }
        
        result = scorer._score_location_context(vessel_near_severomorsk)
        
        # Should have high risk due to proximity to naval base
        assert result['score'] > 3
        assert len(result['risk_factors']) > 0
    
    def test_score_temporal_factors(self, scorer, sample_vessel_data):
        """Test temporal factors scoring."""
        # Test with current time
        sample_vessel_data['detection_time'] = datetime.now().isoformat()
        
        result = scorer._score_temporal_factors(sample_vessel_data)
        
        assert 'score' in result
        assert 'risk_factors' in result
        assert 'details' in result
        
        assert 0 <= result['score'] <= 10
    
    def test_score_temporal_factors_night_activity(self, scorer, sample_vessel_data):
        """Test temporal scoring for night activity."""
        # Set detection time to early morning (suspicious hours)
        night_time = datetime.now().replace(hour=3, minute=0, second=0)
        sample_vessel_data['detection_time'] = night_time.isoformat()
        
        result = scorer._score_temporal_factors(sample_vessel_data)
        
        assert result['score'] > 0  # Should have some risk for night activity
    
    def test_score_intelligence_indicators(self, scorer, sample_vessel_data):
        """Test intelligence indicators scoring."""
        result = scorer._score_intelligence_indicators(sample_vessel_data)
        
        assert 'score' in result
        assert 'risk_factors' in result
        assert 'details' in result
        
        assert 0 <= result['score'] <= 10
    
    def test_score_intelligence_indicators_high_risk(self, scorer, high_risk_vessel_data):
        """Test intelligence scoring for high-risk indicators."""
        result = scorer._score_intelligence_indicators(high_risk_vessel_data)
        
        # Should have high score due to jamming and spoofing
        assert result['score'] > 5
        assert 'jamming' in ' '.join(result['risk_factors']).lower()
        assert 'spoofing' in ' '.join(result['risk_factors']).lower()
    
    def test_calculate_comprehensive_risk_score_normal(self, scorer, sample_vessel_data):
        """Test comprehensive risk scoring for normal vessel."""
        assessment = scorer.calculate_comprehensive_risk_score(sample_vessel_data)
        
        assert 'vessel_id' in assessment
        assert 'overall_risk_score' in assessment
        assert 'risk_level' in assessment
        assert 'component_scores' in assessment
        assert 'risk_factors' in assessment
        assert 'recommendations' in assessment
        
        assert assessment['vessel_id'] == 'TEST_VESSEL_001'
        assert 0 <= assessment['overall_risk_score'] <= 10
        assert assessment['risk_level'] in ['MINIMAL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        
        # Normal vessel should have low-medium risk
        assert assessment['overall_risk_score'] < 6
    
    def test_calculate_comprehensive_risk_score_high_risk(self, scorer, high_risk_vessel_data):
        """Test comprehensive risk scoring for high-risk vessel."""
        assessment = scorer.calculate_comprehensive_risk_score(high_risk_vessel_data)
        
        # High-risk vessel should have high score
        assert assessment['overall_risk_score'] > 5
        assert assessment['risk_level'] in ['HIGH', 'CRITICAL']
        assert len(assessment['risk_factors']) > 5
        assert len(assessment['recommendations']) > 3
    
    def test_determine_risk_level(self, scorer):
        """Test risk level determination."""
        assert scorer._determine_risk_level(0.5) == 'MINIMAL'
        assert scorer._determine_risk_level(2.5) == 'LOW'
        assert scorer._determine_risk_level(4.5) == 'MEDIUM'
        assert scorer._determine_risk_level(6.5) == 'HIGH'
        assert scorer._determine_risk_level(8.5) == 'CRITICAL'
    
    def test_assess_geopolitical_context(self, scorer):
        """Test geopolitical context assessment."""
        test_date = datetime(2024, 3, 15)  # Spring military exercise season
        result = scorer._assess_geopolitical_context(test_date)
        
        assert 'score' in result
        assert 'factors' in result
        assert isinstance(result['score'], (int, float))
        assert isinstance(result['factors'], list)
    
    def test_check_threat_databases(self, scorer):
        """Test threat database checking."""
        # Test with suspicious vessel ID
        result = scorer._check_threat_databases('SUSPICIOUS_VESSEL', '1234567', '123456789')
        
        assert 'sanctions_list' in result
        assert 'watch_list' in result
        assert 'previous_violations' in result
        
        # Should flag suspicious vessel
        assert result['watch_list'] == True
    
    def test_assess_owner_risk(self, scorer):
        """Test owner risk assessment."""
        # Test unknown owner
        result = scorer._assess_owner_risk('')
        assert result['score'] > 0
        
        # Test normal owner
        result = scorer._assess_owner_risk('Maersk Line AS')
        assert result['score'] == 0
        
        # Test potential shell company
        result = scorer._assess_owner_risk('XYZ LLC')
        assert result['score'] > 0
    
    def test_generate_risk_recommendations(self, scorer):
        """Test risk recommendation generation."""
        # Test critical risk recommendations
        component_scores = {
            'vessel_characteristics': {'score': 8},
            'behavioral_patterns': {'score': 7},
            'location_context': {'score': 6},
            'temporal_factors': {'score': 5},
            'intelligence_indicators': {'score': 9}
        }
        
        recommendations = scorer._generate_risk_recommendations('CRITICAL', component_scores)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any('IMMEDIATE ACTION' in rec for rec in recommendations)
    
    def test_generate_risk_report_empty(self, scorer):
        """Test risk report generation with no assessments."""
        report = scorer.generate_risk_report([])
        
        assert 'error' in report
    
    def test_generate_risk_report_with_assessments(self, scorer, sample_vessel_data, high_risk_vessel_data):
        """Test risk report generation with multiple assessments."""
        # Generate assessments
        normal_assessment = scorer.calculate_comprehensive_risk_score(sample_vessel_data)
        high_risk_assessment = scorer.calculate_comprehensive_risk_score(high_risk_vessel_data)
        
        assessments = [normal_assessment, high_risk_assessment]
        
        report = scorer.generate_risk_report(assessments)
        
        assert 'report_timestamp' in report
        assert 'total_vessels_assessed' in report
        assert 'risk_level_distribution' in report
        assert 'statistics' in report
        assert 'top_threats' in report
        assert 'threat_summary' in report
        assert 'regional_assessment' in report
        assert 'recommendations' in report
        
        assert report['total_vessels_assessed'] == 2
        assert report['statistics']['highest_risk_score'] >= report['statistics']['average_risk_score']
    
    def test_identify_emerging_patterns(self, scorer):
        """Test emerging pattern identification."""
        # Create multiple high-risk assessments
        assessments = []
        for i in range(4):
            assessment = {
                'risk_level': 'HIGH',
                'component_scores': {
                    'location_context': {
                        'details': {'closest_infrastructure': 'Test Infrastructure'}
                    }
                }
            }
            assessments.append(assessment)
        
        patterns = scorer._identify_emerging_patterns(assessments)
        
        assert isinstance(patterns, list)
        assert len(patterns) > 0
    
    def test_assess_regional_threat_level(self, scorer):
        """Test regional threat level assessment."""
        # Test with multiple critical threats
        critical_assessments = [{'risk_level': 'CRITICAL'} for _ in range(3)]
        level = scorer._assess_regional_threat_level(critical_assessments)
        assert level == 'CRITICAL'
        
        # Test with high threats
        high_assessments = [{'risk_level': 'HIGH'} for _ in range(2)]
        level = scorer._assess_regional_threat_level(high_assessments)
        assert level == 'MEDIUM'
        
        # Test with low threats
        low_assessments = [{'risk_level': 'LOW'} for _ in range(5)]
        level = scorer._assess_regional_threat_level(low_assessments)
        assert level == 'LOW'


class TestRiskScoringEdgeCases:
    """Test edge cases and error conditions for risk scoring."""
    
    @pytest.fixture
    def scorer(self):
        return RiskScorer()
    
    def test_missing_vessel_data(self, scorer):
        """Test handling of missing vessel data."""
        minimal_data = {'vessel_id': 'MINIMAL_001'}
        
        assessment = scorer.calculate_comprehensive_risk_score(minimal_data)
        
        # Should handle missing data gracefully
        assert assessment['overall_risk_score'] >= 0
        assert assessment['risk_level'] is not None
    
    def test_invalid_coordinates(self, scorer):
        """Test handling of invalid coordinates."""
        invalid_data = {
            'vessel_id': 'INVALID_001',
            'latitude': 999,  # Invalid latitude
            'longitude': 999  # Invalid longitude
        }
        
        assessment = scorer.calculate_comprehensive_risk_score(invalid_data)
        
        # Should handle gracefully
        assert assessment['overall_risk_score'] >= 0
    
    def test_future_detection_time(self, scorer):
        """Test handling of future detection times."""
        future_data = {
            'vessel_id': 'FUTURE_001',
            'detection_time': (datetime.now() + timedelta(days=30)).isoformat()
        }
        
        assessment = scorer.calculate_comprehensive_risk_score(future_data)
        
        # Should handle future times gracefully
        assert assessment['overall_risk_score'] >= 0
    
    def test_extreme_vessel_size(self, scorer):
        """Test handling of extreme vessel sizes."""
        giant_vessel = {
            'vessel_id': 'GIANT_001',
            'estimated_length': 500,  # Extremely large
            'vessel_type': 'cargo'
        }
        
        assessment = scorer.calculate_comprehensive_risk_score(giant_vessel)
        
        # Should handle extreme sizes
        assert assessment['overall_risk_score'] >= 0
        assert assessment['component_scores']['vessel_characteristics']['score'] > 0
    
    def test_negative_values(self, scorer):
        """Test handling of negative values in data."""
        negative_data = {
            'vessel_id': 'NEGATIVE_001',
            'estimated_length': -50,  # Negative length
            'distance_to_port': -1000,  # Negative distance
            'vessel_history': {
                'ais_gaps_count': -5  # Negative count
            }
        }
        
        assessment = scorer.calculate_comprehensive_risk_score(negative_data)
        
        # Should handle negative values gracefully
        assert assessment['overall_risk_score'] >= 0


class TestRiskScoringIntegration:
    """Integration tests for risk scoring system."""
    
    def test_end_to_end_risk_assessment(self):
        """Test complete risk assessment pipeline."""
        scorer = RiskScorer()
        
        # Create a scenario with multiple vessels
        vessels = [
            {
                'vessel_id': 'FISHING_001',
                'latitude': 70.0,
                'longitude': 30.0,
                'vessel_type': 'fishing',
                'nationality': 'NO',
                'ais_data': {'mmsi': '111111111'},
                'behavior_analysis': {
                    'pattern_classification': {'pattern': 'normal_fishing', 'confidence': 0.9},
                    'anomalies': []
                }
            },
            {
                'vessel_id': 'SUSPICIOUS_001',
                'latitude': 69.07,  # Near naval base
                'longitude': 33.42,
                'vessel_type': 'unknown',
                'nationality': 'UNKNOWN',
                'ais_data': None,
                'behavior_analysis': {
                    'pattern_classification': {'pattern': 'surveillance_pattern', 'confidence': 0.8},
                    'anomalies': [{'severity': 'high'}]
                }
            },
            {
                'vessel_id': 'CARGO_001',
                'latitude': 68.0,
                'longitude': 28.0,
                'vessel_type': 'cargo',
                'nationality': 'DE',
                'ais_data': {'mmsi': '333333333'},
                'behavior_analysis': {
                    'pattern_classification': {'pattern': 'normal_transit', 'confidence': 0.85},
                    'anomalies': []
                }
            }
        ]
        
        # Generate assessments for all vessels
        assessments = []
        for vessel in vessels:
            assessment = scorer.calculate_comprehensive_risk_score(vessel)
            assessments.append(assessment)
        
        # Generate comprehensive report
        report = scorer.generate_risk_report(assessments)
        
        # Verify results
        assert len(assessments) == 3
        assert report['total_vessels_assessed'] == 3
        
        # Find the suspicious vessel assessment
        suspicious_assessment = next(a for a in assessments if a['vessel_id'] == 'SUSPICIOUS_001')
        fishing_assessment = next(a for a in assessments if a['vessel_id'] == 'FISHING_001')
        
        # Suspicious vessel should have higher risk than fishing vessel
        assert suspicious_assessment['overall_risk_score'] > fishing_assessment['overall_risk_score']
        
        # Report should identify threats appropriately
        if report['statistics']['critical_threats'] > 0:
            assert report['regional_assessment'] in ['HIGH', 'CRITICAL']


if __name__ == "__main__":
    pytest.main([__file__])