"""
Test suite for maritime anomaly detection autoencoder.
"""

import pytest
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch

# Add parent directory to path for imports
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.autoencoder import MaritimeAnomalyDetector, create_synthetic_training_data


class TestMaritimeAnomalyDetector:
    """Test class for MaritimeAnomalyDetector."""
    
    @pytest.fixture
    def detector(self):
        """Create a detector instance for testing."""
        return MaritimeAnomalyDetector(input_dim=10, encoding_dim=5)
    
    @pytest.fixture
    def sample_vessel_data(self):
        """Sample vessel data for testing."""
        return {
            'distance_to_cable': 1000,
            'distance_to_military_base': 20000,
            'vessel_size': 50,
            'estimated_speed': 10,
            'time_stationary': 1,
            'time_of_day': 14,
            'day_of_week': 2,
            'distance_to_port': 30000,
            'weather_severity': 3,
            'repeat_visits': 2
        }
    
    def test_initialization(self, detector):
        """Test detector initialization."""
        assert detector.input_dim == 10
        assert detector.encoding_dim == 5
        assert detector.model is None
        assert detector.threshold is None
        assert detector.scaler is not None
    
    def test_extract_features(self, detector, sample_vessel_data):
        """Test feature extraction from vessel data."""
        features = detector.extract_features(sample_vessel_data)
        
        assert isinstance(features, np.ndarray)
        assert features.shape == (1, 10)
        assert features[0][0] == 1000  # distance_to_cable
        assert features[0][3] == 10    # estimated_speed
    
    def test_extract_features_missing_data(self, detector):
        """Test feature extraction with missing data."""
        incomplete_data = {'vessel_size': 30}
        features = detector.extract_features(incomplete_data)
        
        assert isinstance(features, np.ndarray)
        assert features.shape == (1, 10)
        assert features[0][2] == 30  # vessel_size
        assert features[0][0] == 0   # missing distance_to_cable defaults to 0
    
    def test_build_autoencoder(self, detector):
        """Test autoencoder architecture building."""
        model = detector._build_autoencoder()
        
        assert model is not None
        assert len(model.layers) == 5  # input, encoder layers, decoder layers
        assert model.input_shape == (None, 10)
        assert model.output_shape == (None, 10)
    
    @patch('models.autoencoder.tf.keras.models.Model.fit')
    def test_train(self, mock_fit, detector):
        """Test training process."""
        # Create synthetic training data
        training_data = np.random.rand(100, 10)
        
        # Mock the fit method to avoid actual training
        mock_history = Mock()
        mock_fit.return_value = mock_history
        
        # Mock predict method for threshold calculation
        with patch.object(detector, '_build_autoencoder') as mock_build:
            mock_model = Mock()
            mock_model.predict.return_value = training_data + np.random.normal(0, 0.1, training_data.shape)
            mock_build.return_value = mock_model
            
            history = detector.train(training_data, epochs=10, batch_size=16)
            
            assert detector.model is not None
            assert detector.threshold is not None
            assert detector.threshold > 0
            mock_fit.assert_called_once()
    
    def test_predict_anomaly_with_trained_model(self, detector, sample_vessel_data):
        """Test anomaly prediction with a trained model."""
        # Mock a trained model
        detector.model = Mock()
        detector.model.predict.return_value = np.array([[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]])
        detector.threshold = 0.5
        detector.scaler.fit([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]])  # Fit with dummy data
        
        result = detector.predict_anomaly(sample_vessel_data)
        
        assert isinstance(result, dict)
        assert 'is_anomaly' in result
        assert 'anomaly_score' in result
        assert 'reconstruction_error' in result
        assert 'threshold' in result
        assert isinstance(result['is_anomaly'], bool)
        assert 0 <= result['anomaly_score'] <= 10
    
    def test_predict_anomaly_no_model(self, detector, sample_vessel_data):
        """Test prediction fails gracefully without trained model."""
        with pytest.raises(AttributeError):
            detector.predict_anomaly(sample_vessel_data)
    
    def test_save_and_load_model(self, detector):
        """Test model saving and loading."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = os.path.join(temp_dir, "test_model")
            
            # Create mock objects for saving
            detector.model = Mock()
            detector.threshold = 0.5
            detector.scaler.fit([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]])
            
            # Mock the save methods
            with patch('joblib.dump') as mock_joblib_dump, \
                 patch.object(detector.model, 'save') as mock_model_save:
                
                detector.save_model(filepath)
                
                mock_model_save.assert_called_once_with(f"{filepath}_autoencoder.h5")
                assert mock_joblib_dump.call_count == 2  # scaler and threshold
    
    def test_predict_with_array_input(self, detector):
        """Test prediction with numpy array input."""
        detector.model = Mock()
        detector.model.predict.return_value = np.array([[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]])
        detector.threshold = 0.5
        detector.scaler.fit([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]])
        
        features_array = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        result = detector.predict_anomaly(features_array)
        
        assert isinstance(result, dict)
        assert 'is_anomaly' in result


class TestSyntheticDataGeneration:
    """Test synthetic data generation utilities."""
    
    def test_create_synthetic_training_data(self):
        """Test synthetic training data creation."""
        data = create_synthetic_training_data(100)
        
        assert isinstance(data, np.ndarray)
        assert data.shape == (100, 10)
        assert np.all(data >= 0)  # All values should be non-negative
    
    def test_synthetic_data_variety(self):
        """Test that synthetic data contains variety."""
        data = create_synthetic_training_data(1000)
        
        # Check that we have variation in the data
        for i in range(10):
            column_std = np.std(data[:, i])
            assert column_std > 0, f"Column {i} has no variation"
    
    def test_synthetic_data_deterministic(self):
        """Test that synthetic data generation is deterministic."""
        data1 = create_synthetic_training_data(50)
        data2 = create_synthetic_training_data(50)
        
        np.testing.assert_array_equal(data1, data2)


class TestAnomalyDetectionIntegration:
    """Integration tests for the complete anomaly detection pipeline."""
    
    def test_end_to_end_pipeline(self):
        """Test complete pipeline from training to prediction."""
        # Create detector
        detector = MaritimeAnomalyDetector(input_dim=10, encoding_dim=5)
        
        # Generate training data
        training_data = create_synthetic_training_data(200)
        
        # Train with minimal epochs for speed
        with patch('models.autoencoder.tf.keras.models.Model.fit') as mock_fit:
            mock_fit.return_value = Mock()
            
            # Mock model prediction for threshold calculation
            with patch.object(detector, '_build_autoencoder') as mock_build:
                mock_model = Mock()
                # Return data similar to input for threshold calculation
                mock_model.predict.return_value = training_data + np.random.normal(0, 0.1, training_data.shape)
                mock_build.return_value = mock_model
                
                detector.train(training_data, epochs=1)
        
        # Test normal vessel
        normal_vessel = {
            'distance_to_cable': 5000,
            'distance_to_military_base': 20000,
            'vessel_size': 30,
            'estimated_speed': 5,
            'time_stationary': 2,
            'time_of_day': 12,
            'day_of_week': 2,
            'distance_to_port': 50000,
            'weather_severity': 3,
            'repeat_visits': 2
        }
        
        # Mock prediction for normal vessel
        detector.model.predict.return_value = np.array([[0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5]])
        
        normal_result = detector.predict_anomaly(normal_vessel)
        
        # Test suspicious vessel
        suspicious_vessel = {
            'distance_to_cable': 100,    # Very close to cable
            'distance_to_military_base': 5000,
            'vessel_size': 80,
            'estimated_speed': 2,        # Slow/loitering
            'time_stationary': 8,
            'time_of_day': 2,           # Night time
            'day_of_week': 6,
            'distance_to_port': 100000,
            'weather_severity': 1,
            'repeat_visits': 5
        }
        
        # Mock prediction for suspicious vessel (higher reconstruction error)
        detector.model.predict.return_value = np.array([[0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1]])
        
        suspicious_result = detector.predict_anomaly(suspicious_vessel)
        
        # Verify results
        assert isinstance(normal_result, dict)
        assert isinstance(suspicious_result, dict)
        
        # Both should have required keys
        for result in [normal_result, suspicious_result]:
            assert 'is_anomaly' in result
            assert 'anomaly_score' in result
            assert 'reconstruction_error' in result


if __name__ == "__main__":
    pytest.main([__file__])