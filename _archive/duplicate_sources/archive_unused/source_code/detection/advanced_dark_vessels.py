"""
Dark vessel detection module for ArcticShadowTracker.

This module implements the core functionality to detect vessels that appear in
satellite imagery but are not broadcasting AIS signals ("dark vessels").
"""

import numpy as np
import cv2
import rasterio
from datetime import datetime, timedelta
from geopy.distance import geodesic
import logging
from typing import List, Dict, Tuple, Optional


class DarkVesselDetector:
    """
    Main class for detecting dark vessels by comparing satellite imagery 
    with AIS broadcast data.
    """
    
    def __init__(self, matching_threshold_meters: float = 500, 
                 vessel_size_threshold: int = 20,
                 confidence_threshold: float = 0.7):
        """
        Initialize the dark vessel detector.
        
        Args:
            matching_threshold_meters (float): Max distance to match SAR vessel with AIS signal
            vessel_size_threshold (int): Minimum vessel size in pixels
            confidence_threshold (float): Minimum confidence for vessel detection
            
        Raises:
            ValueError: If parameters are invalid
        """
        if matching_threshold_meters <= 0:
            raise ValueError(f"matching_threshold_meters must be positive, got {matching_threshold_meters}")
        if vessel_size_threshold <= 0:
            raise ValueError(f"vessel_size_threshold must be positive, got {vessel_size_threshold}")
        if not 0 <= confidence_threshold <= 1:
            raise ValueError(f"confidence_threshold must be between 0 and 1, got {confidence_threshold}")
            
        self.matching_threshold = matching_threshold_meters
        self.size_threshold = vessel_size_threshold
        self.confidence_threshold = confidence_threshold
        self.logger = logging.getLogger(__name__)
        
    def detect_vessels_in_sar(self, sar_image_path: str, 
                             roi_bounds: Optional[Tuple[float, float, float, float]] = None) -> List[Dict]:
        """
        Detect vessels in SAR imagery using image processing techniques.
        
        Args:
            sar_image_path (str): Path to SAR image file
            roi_bounds (tuple): Optional (min_lat, min_lon, max_lat, max_lon) bounds
            
        Returns:
            List[Dict]: List of detected vessels with coordinates and metadata
            
        Raises:
            FileNotFoundError: If SAR image file doesn't exist
            ValueError: If image format is invalid or ROI bounds are malformed
            RuntimeError: If image processing fails
        """
        if not isinstance(sar_image_path, str) or not sar_image_path.strip():
            raise ValueError("sar_image_path must be a non-empty string")
            
        if roi_bounds is not None:
            if not isinstance(roi_bounds, (tuple, list)) or len(roi_bounds) != 4:
                raise ValueError("roi_bounds must be a 4-element tuple: (min_lat, min_lon, max_lat, max_lon)")
            min_lat, min_lon, max_lat, max_lon = roi_bounds
            if not (-90 <= min_lat <= max_lat <= 90):
                raise ValueError(f"Invalid latitude bounds: {min_lat}, {max_lat}")
            if not (-180 <= min_lon <= max_lon <= 180):
                raise ValueError(f"Invalid longitude bounds: {min_lon}, {max_lon}")
        
        detected_vessels = []
        
        try:
            # Read SAR image
            with rasterio.open(sar_image_path) as src:
                # Read image data
                image = src.read(1)  # Assuming single band SAR
                if image is None or image.size == 0:
                    raise ValueError("Empty or invalid SAR image")
                    
                transform = src.transform
                crs = src.crs
                
                # Convert to uint8 for processing
                image_norm = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
                
                # Apply vessel detection algorithm
                vessel_pixels = self._detect_bright_objects(image_norm)
                
                # Convert pixel coordinates to geographic coordinates
                for vessel_pixel in vessel_pixels:
                    try:
                        lat, lon = self._pixel_to_geo(vessel_pixel['centroid'], transform)
                        
                        # Validate coordinates
                        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                            self.logger.warning(f"Invalid coordinates: {lat}, {lon}")
                            continue
                        
                        # Check if vessel is within ROI if specified
                        if roi_bounds and not self._point_in_bounds(lat, lon, roi_bounds):
                            continue
                        
                        vessel_data = {
                            'detection_id': f"SAR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(detected_vessels)}",
                            'latitude': float(lat),
                            'longitude': float(lon),
                            'pixel_coordinates': vessel_pixel['centroid'],
                            'estimated_length': float(vessel_pixel['length_pixels'] * self._get_pixel_size(transform)),
                            'estimated_width': float(vessel_pixel['width_pixels'] * self._get_pixel_size(transform)),
                            'vessel_area_pixels': int(vessel_pixel['area']),
                            'intensity_mean': float(vessel_pixel['intensity_mean']),
                            'intensity_max': float(vessel_pixel['intensity_max']),
                            'confidence': float(vessel_pixel['confidence']),
                            'detection_time': datetime.now().isoformat(),
                            'image_source': str(sar_image_path)
                        }
                        
                        # Only include high-confidence detections
                        if vessel_data['confidence'] >= self.confidence_threshold:
                            detected_vessels.append(vessel_data)
                            
                    except Exception as e:
                        self.logger.warning(f"Error processing vessel detection: {e}")
                        continue
        
        except FileNotFoundError:
            raise FileNotFoundError(f"SAR image file not found: {sar_image_path}")
        except rasterio.errors.RasterioIOError as e:
            raise ValueError(f"Invalid SAR image format: {e}")
        except Exception as e:
            raise RuntimeError(f"SAR image processing failed: {e}")
            
        self.logger.info(f"Detected {len(detected_vessels)} vessels in SAR imagery")
        return detected_vessels
    
    def _detect_bright_objects(self, image: np.ndarray) -> List[Dict]:
        """
        Detect bright objects (potential vessels) in SAR image.
        
        Args:
            image (np.ndarray): Preprocessed SAR image
            
        Returns:
            List[Dict]: List of detected objects with properties
        """
        detected_objects = []
        
        # Apply CFAR (Constant False Alarm Rate) detector
        # For simplicity, using adaptive threshold
        
        # Apply Gaussian blur to reduce speckle noise
        blurred = cv2.GaussianBlur(image, (5, 5), 0)
        
        # Calculate adaptive threshold
        # Background estimation using larger kernel
        background = cv2.morphologyEx(blurred, cv2.MORPH_TOPHAT, 
                                    cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15)))
        
        # Apply threshold to find bright targets
        _, binary = cv2.threshold(background, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # Filter by size
            area = cv2.contourArea(contour)
            if area < self.size_threshold:
                continue
            
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Calculate centroid
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx, cy = x + w//2, y + h//2
            
            # Extract region for intensity analysis
            roi = image[y:y+h, x:x+w]
            
            # Calculate vessel properties
            vessel_props = {
                'centroid': (cx, cy),
                'bounding_box': (x, y, w, h),
                'area': area,
                'length_pixels': max(w, h),
                'width_pixels': min(w, h),
                'aspect_ratio': max(w, h) / min(w, h),
                'intensity_mean': np.mean(roi),
                'intensity_max': np.max(roi),
                'intensity_std': np.std(roi),
                'contour': contour
            }
            
            # Calculate confidence score
            confidence = self._calculate_vessel_confidence(vessel_props, image)
            vessel_props['confidence'] = confidence
            
            detected_objects.append(vessel_props)
        
        # Sort by confidence and return top detections
        detected_objects.sort(key=lambda x: x['confidence'], reverse=True)
        
        return detected_objects
    
    def _calculate_vessel_confidence(self, vessel_props: Dict, image: np.ndarray) -> float:
        """
        Calculate confidence score for vessel detection.
        
        Args:
            vessel_props (Dict): Vessel properties
            image (np.ndarray): Original image
            
        Returns:
            float: Confidence score (0-1)
        """
        # Factors contributing to confidence:
        # 1. Intensity contrast with background
        # 2. Shape (elongated objects more likely to be vessels)
        # 3. Size (reasonable vessel dimensions)
        # 4. Edge strength
        
        x, y, w, h = vessel_props['bounding_box']
        roi = image[y:y+h, x:x+w]
        
        # Background region (expanded around vessel)
        bg_margin = 10
        y1 = max(0, y - bg_margin)
        y2 = min(image.shape[0], y + h + bg_margin)
        x1 = max(0, x - bg_margin)
        x2 = min(image.shape[1], x + w + bg_margin)
        
        background_roi = image[y1:y2, x1:x2]
        background_mean = np.mean(background_roi)
        
        # Intensity contrast score
        contrast_ratio = vessel_props['intensity_mean'] / (background_mean + 1e-6)
        contrast_score = min(1.0, contrast_ratio / 3.0)  # Normalize
        
        # Shape score (elongated objects preferred)
        aspect_ratio = vessel_props['aspect_ratio']
        if 2 <= aspect_ratio <= 10:  # Typical vessel aspect ratios
            shape_score = 1.0
        elif aspect_ratio < 2:
            shape_score = aspect_ratio / 2.0
        else:
            shape_score = max(0.1, 10.0 / aspect_ratio)
        
        # Size score (reasonable vessel sizes)
        area = vessel_props['area']
        if 20 <= area <= 1000:  # Reasonable pixel area for vessels
            size_score = 1.0
        elif area < 20:
            size_score = area / 20.0
        else:
            size_score = max(0.1, 1000.0 / area)
        
        # Edge strength score
        edges = cv2.Canny(roi, 50, 150)
        edge_density = np.sum(edges > 0) / edges.size
        edge_score = min(1.0, edge_density * 10)  # Normalize
        
        # Combined confidence score
        confidence = (contrast_score * 0.4 + shape_score * 0.3 + 
                     size_score * 0.2 + edge_score * 0.1)
        
        return min(1.0, confidence)
    
    def find_dark_vessels(self, sar_detections: List[Dict], 
                         ais_data: List[Dict],
                         time_tolerance_minutes: int = 30) -> List[Dict]:
        """
        Compare SAR detections with AIS data to find dark vessels.
        
        Args:
            sar_detections (List[Dict]): Vessels detected in SAR imagery
            ais_data (List[Dict]): AIS broadcast data for the same area/time
            time_tolerance_minutes (int): Time tolerance for matching
            
        Returns:
            List[Dict]: Dark vessels (SAR detections without matching AIS)
            
        Raises:
            ValueError: If input data is invalid
            TypeError: If input types are incorrect
        """
        if not isinstance(sar_detections, list):
            raise TypeError(f"sar_detections must be a list, got {type(sar_detections)}")
        if not isinstance(ais_data, list):
            raise TypeError(f"ais_data must be a list, got {type(ais_data)}")
        if time_tolerance_minutes <= 0:
            raise ValueError(f"time_tolerance_minutes must be positive, got {time_tolerance_minutes}")
            
        # Validate SAR detection format
        for i, detection in enumerate(sar_detections):
            if not isinstance(detection, dict):
                raise TypeError(f"SAR detection {i} must be a dictionary")
            required_fields = ['detection_time', 'latitude', 'longitude']
            for field in required_fields:
                if field not in detection:
                    raise ValueError(f"SAR detection {i} missing required field: {field}")
                    
        # Validate AIS data format
        for i, ais in enumerate(ais_data):
            if not isinstance(ais, dict):
                raise TypeError(f"AIS message {i} must be a dictionary")
            required_fields = ['timestamp', 'latitude', 'longitude']
            for field in required_fields:
                if field not in ais:
                    raise ValueError(f"AIS message {i} missing required field: {field}")
        
        # Pre-process and validate AIS data for better performance
        valid_ais_data = []
        for i, ais in enumerate(ais_data):
            try:
                ais_time = datetime.fromisoformat(ais['timestamp'])
                ais_pos = (float(ais['latitude']), float(ais['longitude']))
                
                # Validate AIS coordinates
                if (-90 <= ais_pos[0] <= 90) and (-180 <= ais_pos[1] <= 180):
                    valid_ais_data.append({
                        'original': ais,
                        'time': ais_time,
                        'position': ais_pos
                    })
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Invalid AIS message {i}: {e}")
                continue
        
        self.logger.debug(f"Pre-processed {len(valid_ais_data)} valid AIS messages from {len(ais_data)} total")
        
        dark_vessels = []
        
        for sar_vessel in sar_detections:
            try:
                sar_time = datetime.fromisoformat(sar_vessel['detection_time'])
                sar_pos = (float(sar_vessel['latitude']), float(sar_vessel['longitude']))
                
                # Validate coordinates
                if not (-90 <= sar_pos[0] <= 90) or not (-180 <= sar_pos[1] <= 180):
                    self.logger.warning(f"Invalid SAR coordinates: {sar_pos}")
                    continue
                
            except (ValueError, KeyError) as e:
                self.logger.warning(f"Invalid SAR vessel data: {e}")
                continue
            
            # Look for matching AIS signals (optimized)
            matched = False
            closest_ais = None
            closest_distance = float('inf')
            
            for ais_data_item in valid_ais_data:
                # Check time tolerance first (fastest check)
                time_diff = abs((sar_time - ais_data_item['time']).total_seconds() / 60)
                if time_diff > time_tolerance_minutes:
                    continue
                
                # Calculate distance only if time tolerance is met
                distance = geodesic(sar_pos, ais_data_item['position']).meters
                
                if distance < self.matching_threshold:
                    matched = True
                    break
                elif distance < closest_distance:
                    closest_distance = distance
                    closest_ais = ais_data_item['original']
            
            if not matched:
                # This is a dark vessel
                dark_vessel = sar_vessel.copy()
                dark_vessel['status'] = 'dark_vessel'
                dark_vessel['closest_ais_distance'] = float(closest_distance) if closest_distance != float('inf') else None
                dark_vessel['closest_ais_vessel'] = closest_ais
                dark_vessel['analysis_time'] = datetime.now().isoformat()
                
                # Add risk assessment with error handling
                try:
                    dark_vessel['risk_score'] = self._assess_dark_vessel_risk(dark_vessel)
                except Exception as e:
                    self.logger.warning(f"Risk assessment failed for {dark_vessel.get('detection_id', 'unknown')}: {e}")
                    dark_vessel['risk_score'] = 5.0  # Default moderate risk
                
                dark_vessels.append(dark_vessel)
        
        self.logger.info(f"Found {len(dark_vessels)} dark vessels out of {len(sar_detections)} SAR detections")
        return dark_vessels
    
    def _assess_dark_vessel_risk(self, dark_vessel: Dict) -> float:
        """
        Assess risk level of a dark vessel.
        
        Args:
            dark_vessel (Dict): Dark vessel data
            
        Returns:
            float: Risk score (0-10)
        """
        risk_factors = []
        
        # Size factor - larger vessels more concerning
        estimated_length = dark_vessel.get('estimated_length', 0)
        if estimated_length > 100:  # Large vessel
            risk_factors.append(3)
        elif estimated_length > 50:  # Medium vessel
            risk_factors.append(2)
        else:  # Small vessel
            risk_factors.append(1)
        
        # Confidence factor - higher confidence = higher risk
        confidence = dark_vessel.get('confidence', 0)
        risk_factors.append(confidence * 3)
        
        # Proximity to nearest AIS vessel
        closest_distance = dark_vessel.get('closest_ais_distance', float('inf'))
        if closest_distance < 1000:  # Very close to AIS vessel
            risk_factors.append(2)  # Could be escort or formation
        elif closest_distance > 50000:  # Very isolated
            risk_factors.append(3)  # Suspicious isolation
        else:
            risk_factors.append(1)
        
        # Calculate weighted risk score
        base_risk = sum(risk_factors)
        
        # Normalize to 0-10 scale
        risk_score = min(10, base_risk)
        
        return risk_score
    
    def _pixel_to_geo(self, pixel_coords: Tuple[int, int], 
                     transform: rasterio.Affine) -> Tuple[float, float]:
        """Convert pixel coordinates to geographic coordinates."""
        x, y = pixel_coords
        lon, lat = rasterio.transform.xy(transform, y, x)
        return lat, lon
    
    def _get_pixel_size(self, transform: rasterio.Affine) -> float:
        """Get pixel size in meters (approximate)."""
        return abs(transform[0])  # Assumes square pixels
    
    def _point_in_bounds(self, lat: float, lon: float, 
                        bounds: Tuple[float, float, float, float]) -> bool:
        """Check if point is within geographic bounds."""
        min_lat, min_lon, max_lat, max_lon = bounds
        return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon
    
    def generate_detection_report(self, dark_vessels: List[Dict], 
                                 output_file: Optional[str] = None) -> Dict:
        """
        Generate a comprehensive detection report.
        
        Args:
            dark_vessels (List[Dict]): List of detected dark vessels
            output_file (str): Optional file path to save report
            
        Returns:
            Dict: Detection report
        """
        if not dark_vessels:
            report = {
                'summary': {
                    'total_dark_vessels': 0,
                    'high_risk_vessels': 0,
                    'analysis_time': datetime.now().isoformat()
                },
                'vessels': []
            }
        else:
            # Calculate statistics
            high_risk_count = sum(1 for v in dark_vessels if v.get('risk_score', 0) >= 7)
            avg_risk = np.mean([v.get('risk_score', 0) for v in dark_vessels])
            
            # Geographic bounds
            lats = [v['latitude'] for v in dark_vessels]
            lons = [v['longitude'] for v in dark_vessels]
            
            report = {
                'summary': {
                    'total_dark_vessels': len(dark_vessels),
                    'high_risk_vessels': high_risk_count,
                    'average_risk_score': float(avg_risk),
                    'geographic_bounds': {
                        'north': max(lats),
                        'south': min(lats),
                        'east': max(lons),
                        'west': min(lons)
                    },
                    'analysis_time': datetime.now().isoformat()
                },
                'vessels': dark_vessels
            }
        
        # Save report if requested
        if output_file:
            import json
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
        
        return report


class VesselTracker:
    """
    Track vessel movements over time to build behavioral patterns.
    """
    
    def __init__(self):
        self.vessel_tracks = {}
        self.logger = logging.getLogger(__name__)
    
    def update_vessel_track(self, vessel_id: str, position: Dict):
        """
        Update vessel track with new position.
        
        Args:
            vessel_id (str): Unique vessel identifier
            position (Dict): Position data with lat, lon, timestamp
        """
        if vessel_id not in self.vessel_tracks:
            self.vessel_tracks[vessel_id] = []
        
        self.vessel_tracks[vessel_id].append(position)
        
        # Keep only recent positions (last 30 days)
        cutoff_time = datetime.now() - timedelta(days=30)
        self.vessel_tracks[vessel_id] = [
            pos for pos in self.vessel_tracks[vessel_id]
            if datetime.fromisoformat(pos['timestamp']) > cutoff_time
        ]
    
    def get_vessel_track(self, vessel_id: str) -> List[Dict]:
        """Get track history for a vessel."""
        return self.vessel_tracks.get(vessel_id, [])
    
    def calculate_vessel_statistics(self, vessel_id: str) -> Dict:
        """
        Calculate movement statistics for a vessel.
        
        Args:
            vessel_id (str): Vessel identifier
            
        Returns:
            Dict: Movement statistics
        """
        track = self.get_vessel_track(vessel_id)
        
        if len(track) < 2:
            return {'error': 'Insufficient track data'}
        
        # Calculate speeds and distances
        speeds = []
        total_distance = 0
        
        for i in range(len(track) - 1):
            pos1 = track[i]
            pos2 = track[i + 1]
            
            distance = geodesic(
                (pos1['latitude'], pos1['longitude']),
                (pos2['latitude'], pos2['longitude'])
            ).meters
            
            time_diff = (datetime.fromisoformat(pos2['timestamp']) - 
                        datetime.fromisoformat(pos1['timestamp'])).total_seconds()
            
            if time_diff > 0:
                speed = distance / time_diff * 3.6  # Convert to km/h
                speeds.append(speed)
                total_distance += distance
        
        # Calculate area of operation
        lats = [pos['latitude'] for pos in track]
        lons = [pos['longitude'] for pos in track]
        
        statistics = {
            'total_positions': len(track),
            'total_distance_km': total_distance / 1000,
            'average_speed_kmh': np.mean(speeds) if speeds else 0,
            'max_speed_kmh': np.max(speeds) if speeds else 0,
            'operating_area': {
                'north': max(lats),
                'south': min(lats),
                'east': max(lons),
                'west': min(lons),
                'area_km2': self._calculate_bounding_box_area(lats, lons)
            },
            'track_duration_hours': (
                datetime.fromisoformat(track[-1]['timestamp']) - 
                datetime.fromisoformat(track[0]['timestamp'])
            ).total_seconds() / 3600
        }
        
        return statistics
    
    def _calculate_bounding_box_area(self, lats: List[float], lons: List[float]) -> float:
        """Calculate approximate area of bounding box in km²."""
        if len(lats) < 2 or len(lons) < 2:
            return 0
        
        # Approximate using great circle distances
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        
        # Convert lat range to km using geodesic calculation for Arctic accuracy
        # Calculate distance for latitude range at this longitude
        lat_min, lat_max = min(lats), max(lats)
        lon_min, lon_max = min(lons), max(lons)
        lat_km = geodesic((lat_min, lon_min), (lat_max, lon_min)).kilometers
        lon_km = lon_range * 111 * np.cos(np.radians(np.mean(lats)))  # Adjust for latitude
        
        return lat_km * lon_km


if __name__ == "__main__":
    # Example usage
    detector = DarkVesselDetector()
    
    # Example SAR detections
    sar_detections = [
        {
            'detection_id': 'SAR_001',
            'latitude': 70.5,
            'longitude': 31.2,
            'estimated_length': 80,
            'confidence': 0.85,
            'detection_time': '2024-11-15T10:30:00'
        }
    ]
    
    # Example AIS data (empty = no AIS signals)
    ais_data = []
    
    # Find dark vessels
    dark_vessels = detector.find_dark_vessels(sar_detections, ais_data)
    
    # Generate report
    report = detector.generate_detection_report(dark_vessels)
    
    print(f"Detection report: {report}")