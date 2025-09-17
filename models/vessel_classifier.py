"""
Vessel classification module for maritime surveillance.

This module implements machine learning models to classify vessels based on
satellite imagery features, AIS data, and behavioral patterns into categories
such as fishing vessels, cargo ships, naval vessels, and unknown/suspicious vessels.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import cross_val_score, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix
import joblib
import cv2


class VesselClassifier:
    """
    Multi-modal vessel classifier using imagery, AIS, and behavioral features.
    """
    
    def __init__(self, model_type='random_forest'):
        """
        Initialize vessel classifier.
        
        Args:
            model_type (str): Type of classifier ('random_forest', 'gradient_boost', 'svm', 'neural_net')
        """
        self.model_type = model_type
        self.model = self._create_model(model_type)
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = []
        self.vessel_types = [
            'fishing_vessel',
            'cargo_ship', 
            'tanker',
            'naval_vessel',
            'research_vessel',
            'patrol_boat',
            'submarine',
            'unknown_military',
            'suspicious_civilian'
        ]
        
    def _create_model(self, model_type):
        """Create the specified model type."""
        models = {
            'random_forest': RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            ),
            'gradient_boost': GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            ),
            'svm': SVC(
                kernel='rbf',
                probability=True,
                class_weight='balanced',
                random_state=42
            ),
            'neural_net': MLPClassifier(
                hidden_layer_sizes=(100, 50),
                activation='relu',
                solver='adam',
                random_state=42,
                max_iter=1000
            )
        }
        
        return models.get(model_type, models['random_forest'])
    
    def extract_imagery_features(self, sar_image_patch):
        """
        Extract features from SAR imagery patch containing a vessel.
        
        Args:
            sar_image_patch (np.array): SAR image patch around detected vessel
            
        Returns:
            list: Extracted imagery features
        """
        if sar_image_patch is None or sar_image_patch.size == 0:
            return [0] * 15
        
        # Ensure proper data type and range
        if sar_image_patch.dtype != np.uint8:
            sar_image_patch = cv2.normalize(sar_image_patch, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        
        # Basic intensity features
        intensity_features = [
            np.mean(sar_image_patch),           # Mean intensity
            np.std(sar_image_patch),            # Intensity variation
            np.max(sar_image_patch),            # Peak intensity
            np.min(sar_image_patch),            # Minimum intensity
            np.percentile(sar_image_patch, 95), # 95th percentile
        ]
        
        # Shape and size features
        # Threshold to find vessel pixels
        _, binary = cv2.threshold(sar_image_patch, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            
            # Geometric features
            area = cv2.contourArea(largest_contour)
            perimeter = cv2.arcLength(largest_contour, True)
            
            # Bounding rectangle
            x, y, w, h = cv2.boundingRect(largest_contour)
            aspect_ratio = float(w) / h if h > 0 else 0
            extent = float(area) / (w * h) if w * h > 0 else 0
            
            # Ellipse fitting (if possible)
            if len(largest_contour) >= 5:
                ellipse = cv2.fitEllipse(largest_contour)
                major_axis = max(ellipse[1])
                minor_axis = min(ellipse[1])
                eccentricity = np.sqrt(1 - (minor_axis / major_axis)**2) if major_axis > 0 else 0
            else:
                major_axis = max(w, h)
                minor_axis = min(w, h)
                eccentricity = 0
            
            shape_features = [
                area,                           # Vessel area
                perimeter,                      # Vessel perimeter
                aspect_ratio,                   # Length/width ratio
                extent,                         # Filled area ratio
                major_axis,                     # Length estimate
                minor_axis,                     # Width estimate
                eccentricity,                   # Shape elongation
                perimeter**2 / (4 * np.pi * area) if area > 0 else 0,  # Circularity
            ]
        else:
            shape_features = [0] * 8
        
        # Texture features using GLCM approximation
        texture_features = self._calculate_texture_features(sar_image_patch)
        
        return intensity_features + shape_features + texture_features
    
    def _calculate_texture_features(self, image):
        """Calculate basic texture features."""
        # Convert to grayscale if needed
        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Simple texture measures
        # Local binary pattern approximation
        rows, cols = image.shape
        lbp_sum = 0
        count = 0
        
        for i in range(1, rows-1):
            for j in range(1, cols-1):
                center = image[i, j]
                code = 0
                neighbors = [
                    image[i-1, j-1], image[i-1, j], image[i-1, j+1],
                    image[i, j+1], image[i+1, j+1], image[i+1, j],
                    image[i+1, j-1], image[i, j-1]
                ]
                
                for k, neighbor in enumerate(neighbors):
                    if neighbor >= center:
                        code |= (1 << k)
                
                lbp_sum += code
                count += 1
        
        lbp_mean = lbp_sum / count if count > 0 else 0
        
        # Gradient features
        grad_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        return [
            lbp_mean,                      # Local binary pattern
            np.mean(gradient_magnitude),   # Average gradient magnitude
        ]
    
    def extract_ais_features(self, ais_data):
        """
        Extract features from AIS data.
        
        Args:
            ais_data (dict): AIS message data
            
        Returns:
            list: AIS-derived features
        """
        if not ais_data:
            return [0] * 10
        
        features = [
            ais_data.get('speed_over_ground', 0),     # SOG
            ais_data.get('course_over_ground', 0),    # COG
            ais_data.get('heading', 0),               # True heading
            ais_data.get('rate_of_turn', 0),          # ROT
            ais_data.get('ship_type', 0),             # Ship type code
            ais_data.get('length', 0),                # Vessel length
            ais_data.get('width', 0),                 # Vessel width
            ais_data.get('draught', 0),               # Draught
            ais_data.get('nav_status', 0),            # Navigation status
            1 if ais_data.get('destination') else 0,  # Has destination
        ]
        
        return features
    
    def extract_behavioral_features(self, vessel_history):
        """
        Extract behavioral features from vessel history.
        
        Args:
            vessel_history (dict): Historical vessel behavior data
            
        Returns:
            list: Behavioral features
        """
        if not vessel_history:
            return [0] * 12
        
        features = [
            vessel_history.get('avg_speed', 0),           # Average speed
            vessel_history.get('speed_variance', 0),      # Speed consistency
            vessel_history.get('typical_area_size', 0),   # Operating area size
            vessel_history.get('port_visits', 0),         # Port visit frequency
            vessel_history.get('night_activity_ratio', 0), # Night operations
            vessel_history.get('ais_gaps_count', 0),      # AIS transmission gaps
            vessel_history.get('pattern_regularity', 0),  # Behavioral regularity
            vessel_history.get('restricted_area_visits', 0), # Protected area entries
            vessel_history.get('formation_sailing', 0),   # Group behavior
            vessel_history.get('loitering_incidents', 0), # Stationary periods
            vessel_history.get('course_changes', 0),      # Navigation changes
            vessel_history.get('suspicious_meetings', 0), # Vessel encounters
        ]
        
        return features
    
    def extract_contextual_features(self, context_data):
        """
        Extract contextual features (location, time, environment).
        
        Args:
            context_data (dict): Environmental and contextual data
            
        Returns:
            list: Contextual features
        """
        if not context_data:
            return [0] * 8
        
        features = [
            context_data.get('distance_to_shore', 0),     # Distance to nearest shore
            context_data.get('distance_to_port', 0),      # Distance to nearest port
            context_data.get('water_depth', 0),           # Water depth
            context_data.get('sea_state', 0),             # Sea conditions
            context_data.get('hour_of_day', 12),          # Time of day
            context_data.get('day_of_year', 180),         # Seasonality
            context_data.get('in_shipping_lane', 0),      # Commercial shipping lane
            context_data.get('in_fishing_area', 0),       # Known fishing grounds
        ]
        
        return features
    
    def combine_features(self, imagery_patch=None, ais_data=None, 
                        vessel_history=None, context_data=None):
        """
        Combine all feature types into a single feature vector.
        
        Args:
            imagery_patch: SAR image patch
            ais_data: AIS message data
            vessel_history: Historical behavior data
            context_data: Environmental context
            
        Returns:
            np.array: Combined feature vector
        """
        # Extract features from each modality
        imagery_features = self.extract_imagery_features(imagery_patch) if imagery_patch is not None else [0] * 15
        ais_features = self.extract_ais_features(ais_data) if ais_data else [0] * 10
        behavioral_features = self.extract_behavioral_features(vessel_history) if vessel_history else [0] * 12
        contextual_features = self.extract_contextual_features(context_data) if context_data else [0] * 8
        
        # Combine all features
        combined_features = (imagery_features + ais_features + 
                           behavioral_features + contextual_features)
        
        return np.array(combined_features)
    
    def train(self, training_data, labels):
        """
        Train the vessel classifier.
        
        Args:
            training_data (list): List of feature dictionaries
            labels (list): Vessel type labels
        """
        # Extract features for all training samples
        feature_matrix = []
        for sample in training_data:
            features = self.combine_features(
                sample.get('imagery'),
                sample.get('ais_data'),
                sample.get('vessel_history'),
                sample.get('context_data')
            )
            feature_matrix.append(features)
        
        X = np.array(feature_matrix)
        
        # Encode labels
        y = self.label_encoder.fit_transform(labels)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train the model
        self.model.fit(X_scaled, y)
        
        # Store feature names for interpretation
        self.feature_names = (
            [f'img_{i}' for i in range(15)] +
            [f'ais_{i}' for i in range(10)] +
            [f'behavior_{i}' for i in range(12)] +
            [f'context_{i}' for i in range(8)]
        )
        
        # Evaluate using cross-validation
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=5)
        print(f"Cross-validation accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std() * 2:.3f})")
        
        return self.model
    
    def predict(self, imagery_patch=None, ais_data=None, 
                vessel_history=None, context_data=None):
        """
        Predict vessel type for new data.
        
        Args:
            imagery_patch: SAR image patch
            ais_data: AIS message data
            vessel_history: Historical behavior data
            context_data: Environmental context
            
        Returns:
            dict: Prediction results
        """
        # Extract and combine features
        features = self.combine_features(imagery_patch, ais_data, 
                                       vessel_history, context_data)
        
        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Make prediction
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]
        
        # Decode prediction
        vessel_type = self.label_encoder.inverse_transform([prediction])[0]
        
        # Create probability dictionary
        prob_dict = {}
        for i, vessel_class in enumerate(self.label_encoder.classes_):
            prob_dict[vessel_class] = probabilities[i]
        
        # Calculate confidence and risk scores
        confidence = np.max(probabilities)
        
        # Risk scoring based on vessel type and confidence
        risk_score = self._calculate_risk_score(vessel_type, confidence, prob_dict)
        
        return {
            'vessel_type': vessel_type,
            'confidence': confidence,
            'probabilities': prob_dict,
            'risk_score': risk_score,
            'features_used': {
                'imagery': imagery_patch is not None,
                'ais': ais_data is not None,
                'history': vessel_history is not None,
                'context': context_data is not None
            }
        }
    
    def _calculate_risk_score(self, vessel_type, confidence, probabilities):
        """
        Calculate risk score based on vessel type and classification confidence.
        
        Args:
            vessel_type (str): Predicted vessel type
            confidence (float): Classification confidence
            probabilities (dict): All class probabilities
            
        Returns:
            float: Risk score (0-10)
        """
        # Base risk scores for different vessel types
        base_risks = {
            'fishing_vessel': 2,
            'cargo_ship': 1,
            'tanker': 2,
            'naval_vessel': 6,
            'research_vessel': 1,
            'patrol_boat': 4,
            'submarine': 9,
            'unknown_military': 8,
            'suspicious_civilian': 7
        }
        
        base_risk = base_risks.get(vessel_type, 5)
        
        # Adjust risk based on confidence
        # Low confidence increases risk
        confidence_factor = 1 + (1 - confidence)
        
        # Check for high probability of suspicious types
        suspicious_prob = (probabilities.get('submarine', 0) + 
                          probabilities.get('unknown_military', 0) + 
                          probabilities.get('suspicious_civilian', 0))
        
        suspicious_factor = 1 + suspicious_prob
        
        # Calculate final risk score
        risk_score = base_risk * confidence_factor * suspicious_factor
        
        return min(10, risk_score)
    
    def get_feature_importance(self):
        """Get feature importance scores."""
        if hasattr(self.model, 'feature_importances_'):
            importance_dict = {}
            for i, importance in enumerate(self.model.feature_importances_):
                feature_name = self.feature_names[i] if i < len(self.feature_names) else f'feature_{i}'
                importance_dict[feature_name] = importance
            return importance_dict
        else:
            return None
    
    def hyperparameter_tuning(self, training_data, labels):
        """
        Perform hyperparameter tuning for the model.
        
        Args:
            training_data (list): Training data
            labels (list): Training labels
        """
        # Prepare data
        feature_matrix = []
        for sample in training_data:
            features = self.combine_features(
                sample.get('imagery'),
                sample.get('ais_data'),
                sample.get('vessel_history'),
                sample.get('context_data')
            )
            feature_matrix.append(features)
        
        X = np.array(feature_matrix)
        y = self.label_encoder.fit_transform(labels)
        X_scaled = self.scaler.fit_transform(X)
        
        # Define parameter grids for different models
        param_grids = {
            'random_forest': {
                'n_estimators': [50, 100, 200],
                'max_depth': [5, 10, 15, None],
                'min_samples_split': [2, 5, 10]
            },
            'gradient_boost': {
                'n_estimators': [50, 100, 200],
                'learning_rate': [0.05, 0.1, 0.2],
                'max_depth': [3, 6, 9]
            },
            'svm': {
                'C': [0.1, 1, 10],
                'gamma': ['scale', 'auto', 0.001, 0.01]
            }
        }
        
        param_grid = param_grids.get(self.model_type, {})
        
        if param_grid:
            grid_search = GridSearchCV(
                self.model, param_grid, cv=5, 
                scoring='accuracy', n_jobs=-1
            )
            grid_search.fit(X_scaled, y)
            
            self.model = grid_search.best_estimator_
            print(f"Best parameters: {grid_search.best_params_}")
            print(f"Best score: {grid_search.best_score_:.3f}")
            
            return grid_search.best_params_
        else:
            print(f"No parameter grid defined for {self.model_type}")
            return None
    
    def save_model(self, filepath):
        """Save the trained model and preprocessors."""
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'label_encoder': self.label_encoder,
            'feature_names': self.feature_names,
            'model_type': self.model_type
        }, f"{filepath}_vessel_classifier.pkl")
    
    def load_model(self, filepath):
        """Load a trained model and preprocessors."""
        model_data = joblib.load(f"{filepath}_vessel_classifier.pkl")
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoder = model_data['label_encoder']
        self.feature_names = model_data['feature_names']
        self.model_type = model_data['model_type']


def create_synthetic_training_data(n_samples=1000):
    """
    Create synthetic training data for initial model development.
    
    Args:
        n_samples (int): Number of synthetic samples to generate
        
    Returns:
        tuple: (training_data, labels)
    """
    np.random.seed(42)
    
    training_data = []
    labels = []
    
    vessel_types = [
        'fishing_vessel', 'cargo_ship', 'tanker', 'naval_vessel',
        'research_vessel', 'patrol_boat', 'submarine', 'unknown_military'
    ]
    
    for _ in range(n_samples):
        vessel_type = np.random.choice(vessel_types)
        
        # Generate synthetic features based on vessel type
        if vessel_type == 'fishing_vessel':
            sample = {
                'ais_data': {
                    'speed_over_ground': np.random.normal(4, 2),
                    'ship_type': 30,  # Fishing vessel type
                    'length': np.random.normal(25, 10),
                    'width': np.random.normal(8, 3)
                },
                'vessel_history': {
                    'avg_speed': np.random.normal(4, 1),
                    'night_activity_ratio': np.random.uniform(0.3, 0.8),
                    'loitering_incidents': np.random.poisson(5)
                }
            }
        elif vessel_type == 'cargo_ship':
            sample = {
                'ais_data': {
                    'speed_over_ground': np.random.normal(12, 3),
                    'ship_type': 70,  # Cargo vessel type
                    'length': np.random.normal(150, 50),
                    'width': np.random.normal(25, 8)
                },
                'vessel_history': {
                    'avg_speed': np.random.normal(12, 2),
                    'night_activity_ratio': np.random.uniform(0.4, 0.6),
                    'port_visits': np.random.poisson(2)
                }
            }
        # Add more vessel type patterns...
        else:
            sample = {'ais_data': {}, 'vessel_history': {}}
        
        training_data.append(sample)
        labels.append(vessel_type)
    
    return training_data, labels


if __name__ == "__main__":
    # Example usage
    classifier = VesselClassifier(model_type='random_forest')
    
    # Generate synthetic training data
    training_data, labels = create_synthetic_training_data(500)
    
    # Train the classifier
    classifier.train(training_data, labels)
    
    # Test prediction
    test_sample = {
        'ais_data': {
            'speed_over_ground': 2,
            'ship_type': 0,  # Unknown type
            'length': 60,
            'width': 12
        },
        'vessel_history': {
            'avg_speed': 3,
            'night_activity_ratio': 0.9,
            'ais_gaps_count': 10,
            'loitering_incidents': 8
        }
    }
    
    result = classifier.predict(
        ais_data=test_sample['ais_data'],
        vessel_history=test_sample['vessel_history']
    )
    
    print(f"Classification result: {result}")