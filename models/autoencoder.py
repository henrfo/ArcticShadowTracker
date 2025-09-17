"""
Autoencoder for anomaly detection in maritime vessel behavior.

This module implements an autoencoder neural network to learn patterns of normal
vessel behavior and identify anomalies that might indicate suspicious activity.
"""

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
from sklearn.preprocessing import StandardScaler
import joblib


class MaritimeAnomalyDetector:
    """
    Autoencoder-based anomaly detector for vessel behavior analysis.
    
    Uses reconstruction error to identify vessels with unusual patterns
    that deviate from normal maritime behavior.
    """
    
    def __init__(self, input_dim=10, encoding_dim=5):
        """
        Initialize the anomaly detector.
        
        Args:
            input_dim (int): Number of input features
            encoding_dim (int): Dimension of the encoded representation
        """
        self.input_dim = input_dim
        self.encoding_dim = encoding_dim
        self.model = None
        self.scaler = StandardScaler()
        self.threshold = None
        
    def _build_autoencoder(self):
        """Build the autoencoder architecture."""
        # Encoder
        input_layer = layers.Input(shape=(self.input_dim,))
        encoded = layers.Dense(self.encoding_dim * 2, activation='relu')(input_layer)
        encoded = layers.Dropout(0.2)(encoded)
        encoded = layers.Dense(self.encoding_dim, activation='relu')(encoded)
        
        # Decoder
        decoded = layers.Dense(self.encoding_dim * 2, activation='relu')(encoded)
        decoded = layers.Dropout(0.2)(decoded)
        decoded = layers.Dense(self.input_dim, activation='linear')(decoded)
        
        # Autoencoder model
        autoencoder = models.Model(input_layer, decoded)
        autoencoder.compile(optimizer='adam', loss='mse')
        
        return autoencoder
    
    def extract_features(self, vessel_data):
        """
        Extract features for anomaly detection.
        
        Args:
            vessel_data (dict): Dictionary containing vessel information
            
        Returns:
            np.array: Feature vector for the vessel
        """
        features = [
            vessel_data.get('distance_to_cable', 0),
            vessel_data.get('distance_to_military_base', 0),
            vessel_data.get('vessel_size', 0),
            vessel_data.get('estimated_speed', 0),
            vessel_data.get('time_stationary', 0),
            vessel_data.get('time_of_day', 0),  # 0-23
            vessel_data.get('day_of_week', 0),   # 0-6
            vessel_data.get('distance_to_port', 0),
            vessel_data.get('weather_severity', 0),  # 0-10
            vessel_data.get('repeat_visits', 0)
        ]
        
        return np.array(features).reshape(1, -1)
    
    def train(self, training_data, epochs=100, batch_size=32, validation_split=0.2):
        """
        Train the autoencoder on normal vessel behavior.
        
        Args:
            training_data (np.array): Training data with normal behavior patterns
            epochs (int): Number of training epochs
            batch_size (int): Training batch size
            validation_split (float): Fraction of data for validation
        """
        # Normalize the data
        training_data_scaled = self.scaler.fit_transform(training_data)
        
        # Build and train the model
        self.model = self._build_autoencoder()
        
        history = self.model.fit(
            training_data_scaled,
            training_data_scaled,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            shuffle=True,
            verbose=1
        )
        
        # Calculate threshold based on training reconstruction errors
        train_predictions = self.model.predict(training_data_scaled)
        train_errors = np.mean(np.square(training_data_scaled - train_predictions), axis=1)
        
        # Set threshold as 95th percentile of training errors
        self.threshold = np.percentile(train_errors, 95)
        
        return history
    
    def predict_anomaly(self, vessel_data):
        """
        Predict if a vessel exhibits anomalous behavior.
        
        Args:
            vessel_data (dict or np.array): Vessel data to analyze
            
        Returns:
            dict: Prediction results including anomaly score and classification
        """
        if isinstance(vessel_data, dict):
            features = self.extract_features(vessel_data)
        else:
            features = vessel_data.reshape(1, -1)
        
        # Normalize features
        features_scaled = self.scaler.transform(features)
        
        # Get reconstruction
        reconstruction = self.model.predict(features_scaled, verbose=0)
        
        # Calculate reconstruction error
        reconstruction_error = np.mean(np.square(features_scaled - reconstruction))
        
        # Classify as anomaly
        is_anomaly = reconstruction_error > self.threshold
        
        # Calculate normalized anomaly score (0-10)
        anomaly_score = min(10, (reconstruction_error / self.threshold) * 5)
        
        return {
            'is_anomaly': bool(is_anomaly),
            'anomaly_score': float(anomaly_score),
            'reconstruction_error': float(reconstruction_error),
            'threshold': float(self.threshold)
        }
    
    def save_model(self, filepath):
        """Save the trained model and scaler."""
        self.model.save(f"{filepath}_autoencoder.h5")
        joblib.dump(self.scaler, f"{filepath}_scaler.pkl")
        joblib.dump(self.threshold, f"{filepath}_threshold.pkl")
    
    def load_model(self, filepath):
        """Load a trained model and scaler."""
        self.model = tf.keras.models.load_model(f"{filepath}_autoencoder.h5")
        self.scaler = joblib.load(f"{filepath}_scaler.pkl")
        self.threshold = joblib.load(f"{filepath}_threshold.pkl")


def create_synthetic_training_data(n_samples=1000):
    """
    Create synthetic training data for initial model development.
    
    Args:
        n_samples (int): Number of synthetic samples to generate
        
    Returns:
        np.array: Synthetic training data representing normal vessel behavior
    """
    np.random.seed(42)
    
    # Generate normal vessel behavior patterns
    normal_data = []
    
    for _ in range(n_samples):
        # Normal fishing vessel
        if np.random.rand() < 0.4:
            sample = [
                np.random.normal(5000, 2000),  # distance_to_cable (far from cables)
                np.random.normal(20000, 5000), # distance_to_military_base
                np.random.normal(30, 10),      # vessel_size
                np.random.normal(5, 2),        # estimated_speed
                np.random.normal(2, 1),        # time_stationary
                np.random.randint(6, 18),      # time_of_day (daylight hours)
                np.random.randint(0, 7),       # day_of_week
                np.random.normal(50000, 20000), # distance_to_port
                np.random.normal(3, 2),        # weather_severity
                np.random.normal(2, 1)         # repeat_visits
            ]
        
        # Normal cargo vessel
        elif np.random.rand() < 0.7:
            sample = [
                np.random.normal(8000, 3000),  # distance_to_cable
                np.random.normal(30000, 10000), # distance_to_military_base
                np.random.normal(100, 30),     # vessel_size (larger)
                np.random.normal(12, 3),       # estimated_speed (faster)
                np.random.normal(0.5, 0.3),    # time_stationary (moving)
                np.random.randint(0, 24),      # time_of_day (any time)
                np.random.randint(0, 7),       # day_of_week
                np.random.normal(30000, 15000), # distance_to_port
                np.random.normal(4, 2),        # weather_severity
                np.random.normal(1, 0.5)       # repeat_visits
            ]
        
        # Normal patrol vessel
        else:
            sample = [
                np.random.normal(3000, 1000),  # distance_to_cable (patrol near infrastructure)
                np.random.normal(10000, 3000), # distance_to_military_base
                np.random.normal(50, 15),      # vessel_size
                np.random.normal(8, 2),        # estimated_speed
                np.random.normal(1, 0.5),      # time_stationary
                np.random.randint(0, 24),      # time_of_day
                np.random.randint(0, 7),       # day_of_week
                np.random.normal(15000, 5000), # distance_to_port
                np.random.normal(5, 2),        # weather_severity
                np.random.normal(3, 1)         # repeat_visits
            ]
        
        normal_data.append(sample)
    
    return np.array(normal_data)


if __name__ == "__main__":
    # Example usage
    detector = MaritimeAnomalyDetector()
    
    # Generate synthetic training data
    training_data = create_synthetic_training_data(1000)
    
    # Train the model
    detector.train(training_data, epochs=50)
    
    # Test with a suspicious vessel
    suspicious_vessel = {
        'distance_to_cable': 100,        # Very close to cable
        'distance_to_military_base': 5000, # Close to military
        'vessel_size': 80,
        'estimated_speed': 2,            # Slow/loitering
        'time_stationary': 8,            # Stationary for long time
        'time_of_day': 2,               # Night time
        'day_of_week': 6,               # Weekend
        'distance_to_port': 100000,     # Far from port
        'weather_severity': 1,          # Good weather (no excuse for loitering)
        'repeat_visits': 5              # Multiple visits
    }
    
    result = detector.predict_anomaly(suspicious_vessel)
    print(f"Anomaly detection result: {result}")