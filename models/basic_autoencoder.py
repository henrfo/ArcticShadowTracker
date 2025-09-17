"""
Simple and clean autoencoder for Arctic maritime anomaly detection.
Educational implementation focused on clarity and functionality.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow import keras
from typing import Tuple, Dict, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleAnomalyDetector:
    """Simple autoencoder for detecting anomalous vessel behavior patterns."""
    
    def __init__(self, input_features: int = 8):
        """
        Initialize the anomaly detector.
        
        Args:
            input_features: Number of input features
        """
        self.input_features = input_features
        self.model = None
        self.scaler = StandardScaler()
        self.threshold = None
        
    def build_model(self) -> keras.Model:
        """Build a simple autoencoder model."""
        # Input layer
        input_layer = keras.layers.Input(shape=(self.input_features,))
        
        # Encoder
        encoded = keras.layers.Dense(16, activation='relu')(input_layer)
        encoded = keras.layers.Dense(8, activation='relu')(encoded)
        encoded = keras.layers.Dense(4, activation='relu')(encoded)
        
        # Decoder
        decoded = keras.layers.Dense(8, activation='relu')(encoded)
        decoded = keras.layers.Dense(16, activation='relu')(decoded)
        decoded = keras.layers.Dense(self.input_features, activation='linear')(decoded)
        
        # Create model
        model = keras.Model(input_layer, decoded)
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        
        return model
    
    def prepare_data(self, vessel_data: pd.DataFrame) -> np.ndarray:
        """
        Prepare vessel data for training/prediction.
        
        Args:
            vessel_data: DataFrame with vessel features
            
        Returns:
            Normalized feature array
        """
        # Select key features for anomaly detection
        feature_columns = [
            'latitude', 'longitude', 'speed', 'heading',
            'distance_to_shore', 'time_of_day', 'day_of_week', 'vessel_length'
        ]
        
        # Ensure all columns exist
        for col in feature_columns:
            if col not in vessel_data.columns:
                vessel_data[col] = 0.0
        
        features = vessel_data[feature_columns].values
        
        # Handle missing values
        features = np.nan_to_num(features, nan=0.0)
        
        return features
    
    def train(self, vessel_data: pd.DataFrame, epochs: int = 50, validation_split: float = 0.2) -> Dict:
        """
        Train the autoencoder on normal vessel behavior.
        
        Args:
            vessel_data: Training data
            epochs: Number of training epochs
            validation_split: Fraction of data for validation
            
        Returns:
            Training history
        """
        logger.info("Preparing training data...")
        
        # Prepare features
        features = self.prepare_data(vessel_data)
        
        # Normalize features
        features_scaled = self.scaler.fit_transform(features)
        
        # Build model
        self.model = self.build_model()
        
        logger.info(f"Training autoencoder with {len(features)} samples...")
        
        # Train model
        history = self.model.fit(
            features_scaled, features_scaled,
            epochs=epochs,
            batch_size=32,
            validation_split=validation_split,
            shuffle=True,
            verbose=1
        )
        
        # Calculate threshold from training data
        reconstructions = self.model.predict(features_scaled, verbose=0)
        reconstruction_errors = np.mean(np.square(features_scaled - reconstructions), axis=1)
        
        # Set threshold as 95th percentile of reconstruction errors
        self.threshold = np.percentile(reconstruction_errors, 95)
        
        logger.info(f"Training complete. Anomaly threshold: {self.threshold:.4f}")
        
        return {
            'loss': history.history['loss'],
            'val_loss': history.history['val_loss'],
            'threshold': self.threshold
        }
    
    def predict_anomaly(self, vessel_data: pd.DataFrame) -> Dict:
        """
        Predict if vessel behavior is anomalous.
        
        Args:
            vessel_data: Vessel data to analyze
            
        Returns:
            Anomaly prediction results
        """
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Prepare features
        features = self.prepare_data(vessel_data)
        features_scaled = self.scaler.transform(features)
        
        # Get reconstruction
        reconstruction = self.model.predict(features_scaled, verbose=0)
        
        # Calculate reconstruction error
        reconstruction_error = np.mean(np.square(features_scaled - reconstruction), axis=1)
        
        # Determine anomalies
        is_anomaly = reconstruction_error > self.threshold
        
        # Calculate anomaly scores (0-1 scale)
        max_error = self.threshold * 3  # Scale factor
        anomaly_scores = np.clip(reconstruction_error / max_error, 0, 1)
        
        results = []
        for i in range(len(vessel_data)):
            results.append({
                'vessel_index': i,
                'reconstruction_error': float(reconstruction_error[i]),
                'anomaly_score': float(anomaly_scores[i]),
                'is_anomaly': bool(is_anomaly[i]),
                'threshold': float(self.threshold)
            })
        
        return results
    
    def save_model(self, filepath: str):
        """Save the trained model and scaler."""
        if self.model is None:
            raise ValueError("No model to save. Train the model first.")
        
        # Save model
        self.model.save(f"{filepath}_model.h5")
        
        # Save scaler and threshold
        import joblib
        joblib.dump(self.scaler, f"{filepath}_scaler.pkl")
        joblib.dump(self.threshold, f"{filepath}_threshold.pkl")
        
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load a trained model and scaler."""
        # Load model
        self.model = keras.models.load_model(f"{filepath}_model.h5")
        
        # Load scaler and threshold
        import joblib
        self.scaler = joblib.load(f"{filepath}_scaler.pkl")
        self.threshold = joblib.load(f"{filepath}_threshold.pkl")
        
        logger.info(f"Model loaded from {filepath}")


def create_sample_data(n_samples: int = 1000) -> pd.DataFrame:
    """
    Create sample vessel data for testing.
    
    Args:
        n_samples: Number of samples to generate
        
    Returns:
        DataFrame with sample vessel data
    """
    np.random.seed(42)  # For reproducible results
    
    # Normal vessel behavior patterns
    data = {
        'latitude': np.random.normal(70.0, 1.0, n_samples),  # Arctic waters
        'longitude': np.random.normal(30.0, 2.0, n_samples),
        'speed': np.random.gamma(2, 3, n_samples),  # Realistic speed distribution
        'heading': np.random.uniform(0, 360, n_samples),
        'distance_to_shore': np.random.exponential(20, n_samples),
        'time_of_day': np.random.uniform(0, 24, n_samples),
        'day_of_week': np.random.randint(0, 7, n_samples),
        'vessel_length': np.random.gamma(3, 15, n_samples),
    }
    
    # Add some anomalous patterns (10% of data)
    n_anomalies = int(0.1 * n_samples)
    anomaly_indices = np.random.choice(n_samples, n_anomalies, replace=False)
    
    # Anomalous patterns: very high speed, unusual locations, etc.
    data['speed'][anomaly_indices] = np.random.uniform(30, 50, n_anomalies)
    data['latitude'][anomaly_indices] = np.random.uniform(75, 80, n_anomalies)
    
    return pd.DataFrame(data)


def main():
    """Example usage of the anomaly detector."""
    logger.info("=== Arctic Maritime Anomaly Detection Demo ===")
    
    # Create sample data
    logger.info("Generating sample vessel data...")
    vessel_data = create_sample_data(1000)
    
    # Initialize detector
    detector = SimpleAnomalyDetector(input_features=8)
    
    # Train the model
    logger.info("Training anomaly detection model...")
    history = detector.train(vessel_data, epochs=20)
    
    # Test on new data
    logger.info("Testing anomaly detection...")
    test_data = create_sample_data(100)
    results = detector.predict_anomaly(test_data)
    
    # Summary
    anomalies = [r for r in results if r['is_anomaly']]
    logger.info(f"Detected {len(anomalies)} anomalies out of {len(results)} vessels")
    
    # Show top anomalies
    anomalies_sorted = sorted(results, key=lambda x: x['anomaly_score'], reverse=True)
    logger.info("Top 5 most anomalous vessels:")
    for i, result in enumerate(anomalies_sorted[:5]):
        logger.info(f"  {i+1}. Vessel {result['vessel_index']}: "
                   f"Score {result['anomaly_score']:.3f}, "
                   f"Error {result['reconstruction_error']:.4f}")
    
    return detector, results


if __name__ == "__main__":
    detector, results = main()