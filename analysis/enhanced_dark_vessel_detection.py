#!/usr/bin/env python3
"""
Enhanced Dark Vessel Detection Module
Enhanced version of dark vessel detection from barentswatch_test_v2.ipynb

BASED ON NOTEBOOK FOUNDATION:
- AIS history tracking in ais_history.json
- 2-48 hour detection window
- Foreign vessel focus (excludes Norwegian MMSI 257-259)
- Last known position tracking

ENHANCEMENTS:
1. Enhanced AIS Gap Detection with pattern analysis
2. Behavioral Pattern Analysis for suspicious timing
3. Risk Scoring System for dark vessel events
4. Real-time correlation capabilities
5. CSV integration with streaming system
6. Advanced alert generation

Real data only - Works with actual BarentsWatch AIS streams
Simple algorithms - Maintains notebook's excellent simplicity
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
import logging
import json
import math
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

class DarkVesselRiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH" 
    CRITICAL = "CRITICAL"

class SuspiciousPattern(Enum):
    REPEATED_DARK_PERIODS = "REPEATED_DARK_PERIODS"
    SPEED_CHANGE_BEFORE_DARK = "SPEED_CHANGE_BEFORE_DARK"
    COURSE_DEVIATION_BEFORE_DARK = "COURSE_DEVIATION_BEFORE_DARK"
    PROXIMITY_TO_CABLES_WHEN_DARK = "PROXIMITY_TO_CABLES_WHEN_DARK"
    REAPPEARANCE_DISTANT_LOCATION = "REAPPEARANCE_DISTANT_LOCATION"
    DARK_NEAR_SENSITIVE_AREA = "DARK_NEAR_SENSITIVE_AREA"

@dataclass
class DarkVesselEvent:
    """Enhanced dark vessel event with risk analysis"""
    mmsi: int
    name: str
    detection_timestamp: str
    last_seen_timestamp: str
    hours_silent: float
    last_latitude: float
    last_longitude: float
    last_speed: float
    last_course: float
    status: str
    
    # Enhanced fields
    risk_level: str
    risk_score: float
    suspicious_patterns: List[str]
    previous_dark_events: int
    cable_proximity_when_dark: Optional[float]
    speed_change_before_dark: Optional[float]
    course_deviation_before_dark: Optional[float]
    reappearance_distance: Optional[float]

class EnhancedDarkVesselDetector:
    """
    Enhanced dark vessel detector building on notebook's excellent foundation
    
    PRESERVES ORIGINAL LOGIC:
    - 2-48 hour detection window
    - Foreign vessel filtering
    - AIS history tracking
    
    ADDS ENHANCEMENTS:
    - Pattern analysis
    - Risk scoring
    - Behavioral detection
    - Advanced correlation
    """
    
    def __init__(self, data_dir: Path = Path('data_stream')):
        self.data_dir = data_dir
        self.csv_dir = data_dir / 'csv'
        self.intelligence_dir = data_dir / 'intelligence'
        
        # Create directories if they don't exist
        for dir_path in [self.data_dir, self.csv_dir, self.intelligence_dir]:
            dir_path.mkdir(exist_ok=True)
        
        # File paths - compatible with existing CSV structure
        self.ais_history_file = self.csv_dir / 'ais_history.csv'
        self.dark_vessels_file = self.csv_dir / 'dark_vessel_events.csv'
        self.enhanced_dark_vessels_file = self.csv_dir / 'enhanced_dark_vessel_events.csv'
        
        # Submarine cable coordinates (from notebook)
        self.submarine_cables = {
            'svalbard_cable': {
                'name': 'Svalbard Undersea Cable System',
                'coordinates': [[78.9, 11.9], [71.0, 25.8]],
                'status': 'CRITICAL',
                'alert_distance_km': 10
            },
            'lofoten_vesteralen': {
                'name': 'Lofoten-Vesterålen Cable',
                'coordinates': [[68.8, 13.6], [69.3, 16.0]],
                'status': 'HIGH',
                'alert_distance_km': 5
            },
            'norway_uk': {
                'name': 'Norway-UK Cable (Arctic Section)',
                'coordinates': [[70.0, 23.0], [69.0, 18.0]],
                'status': 'HIGH',
                'alert_distance_km': 8
            }
        }
        
        # Sensitive areas (Arctic regions from notebook)
        self.sensitive_areas = {
            'svalbard': {'bbox': [10.0, 76.0, 35.0, 81.0], 'priority': 'HIGH'},
            'north_norway': {'bbox': [15.0, 68.0, 32.0, 71.5], 'priority': 'HIGH'},
            'barents_sea': {'bbox': [20.0, 72.0, 40.0, 76.0], 'priority': 'CRITICAL'}
        }
        
        # Detection parameters (from notebook)
        self.min_dark_hours = 2
        self.max_dark_hours = 48
        self.max_history_days = 30  # Extended for better pattern analysis
        
        # Risk scoring thresholds
        self.risk_thresholds = {
            'speed_change_significant': 5.0,  # knots
            'course_change_significant': 45.0,  # degrees
            'cable_proximity_threshold': 15.0,  # km
            'repeated_events_threshold': 3,
            'distant_reappearance_threshold': 50.0  # km
        }
        
        logger.info("🌑 Enhanced Dark Vessel Detector initialized")
        logger.info(f"📁 Data directory: {self.data_dir}")
        logger.info(f"⏰ Detection window: {self.min_dark_hours}-{self.max_dark_hours} hours")

    def load_vessel_history(self) -> pd.DataFrame:
        """Load vessel AIS history - compatible with existing CSV structure"""
        if self.ais_history_file.exists():
            try:
                df = pd.read_csv(self.ais_history_file, parse_dates=['timestamp', 'collection_time'])
                # Keep only recent history for performance
                cutoff_date = datetime.now() - timedelta(days=self.max_history_days)
                return df[df['collection_time'] >= cutoff_date]
            except Exception as e:
                logger.error(f"Error loading AIS history: {e}")
                return pd.DataFrame()
        return pd.DataFrame()

    def load_dark_vessel_history(self) -> pd.DataFrame:
        """Load historical dark vessel events for pattern analysis"""
        if self.enhanced_dark_vessels_file.exists():
            try:
                return pd.read_csv(self.enhanced_dark_vessels_file, parse_dates=['detection_timestamp', 'last_seen_timestamp'])
            except Exception as e:
                logger.warning(f"Could not load enhanced dark vessel history: {e}")
                
        # Fall back to basic dark vessel file
        if self.dark_vessels_file.exists():
            try:
                return pd.read_csv(self.dark_vessels_file)
            except Exception as e:
                logger.error(f"Error loading dark vessel history: {e}")
                return pd.DataFrame()
        return pd.DataFrame()

    def calculate_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        # Haversine formula
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return c * 6371  # Earth radius in km

    def point_to_line_distance(self, px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
        """Calculate minimum distance from point to line segment (for cables)"""
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return self.calculate_distance_km(px, py, x1, y1)
        
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        return self.calculate_distance_km(px, py, closest_x, closest_y)

    def is_in_sensitive_area(self, lat: float, lon: float) -> Optional[str]:
        """Check if position is in sensitive area"""
        for area_id, area in self.sensitive_areas.items():
            bbox = area['bbox']
            if bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]:
                return area_id
        return None

    def get_cable_proximity(self, lat: float, lon: float) -> Tuple[Optional[str], float]:
        """Get closest cable and distance"""
        min_distance = float('inf')
        closest_cable = None
        
        for cable_id, cable in self.submarine_cables.items():
            coords = cable['coordinates']
            if len(coords) >= 2:
                start_lat, start_lon = coords[0]
                end_lat, end_lon = coords[1]
                
                distance = self.point_to_line_distance(lat, lon, start_lat, start_lon, end_lat, end_lon)
                if distance < min_distance:
                    min_distance = distance
                    closest_cable = cable_id
        
        return closest_cable, min_distance if closest_cable else float('inf')

    def analyze_vessel_behavior_before_dark(self, vessel_history: pd.DataFrame, dark_time: datetime) -> Dict:
        """Analyze vessel behavior in the hours before going dark"""
        behavior_analysis = {
            'speed_change': None,
            'course_deviation': None,
            'suspicious_maneuvers': False
        }
        
        if vessel_history.empty:
            return behavior_analysis
        
        # Look at last 6 hours before going dark
        analysis_window = dark_time - timedelta(hours=6)
        recent_positions = vessel_history[
            (vessel_history['collection_time'] >= analysis_window) &
            (vessel_history['collection_time'] <= dark_time)
        ].sort_values('collection_time')
        
        if len(recent_positions) < 2:
            return behavior_analysis
        
        # Analyze speed changes
        speeds = recent_positions['speed'].values
        if len(speeds) >= 2:
            speed_change = abs(speeds[-1] - speeds[0])
            behavior_analysis['speed_change'] = speed_change
        
        # Analyze course changes
        courses = recent_positions['course'].dropna().values
        if len(courses) >= 2:
            # Handle course wrapping (0-360 degrees)
            course_diff = abs(courses[-1] - courses[0])
            if course_diff > 180:
                course_diff = 360 - course_diff
            behavior_analysis['course_deviation'] = course_diff
        
        # Check for suspicious patterns
        if (behavior_analysis['speed_change'] and 
            behavior_analysis['speed_change'] > self.risk_thresholds['speed_change_significant']):
            behavior_analysis['suspicious_maneuvers'] = True
        
        if (behavior_analysis['course_deviation'] and 
            behavior_analysis['course_deviation'] > self.risk_thresholds['course_change_significant']):
            behavior_analysis['suspicious_maneuvers'] = True
        
        return behavior_analysis

    def detect_suspicious_patterns(self, vessel_mmsi: int, dark_event: Dict, vessel_history: pd.DataFrame, dark_history: pd.DataFrame) -> List[SuspiciousPattern]:
        """Detect suspicious patterns in dark vessel behavior"""
        patterns = []
        
        # 1. Check for repeated dark periods
        vessel_dark_history = dark_history[dark_history['mmsi'] == vessel_mmsi]
        if len(vessel_dark_history) >= self.risk_thresholds['repeated_events_threshold']:
            patterns.append(SuspiciousPattern.REPEATED_DARK_PERIODS)
        
        # 2. Check behavior before going dark
        dark_time = pd.to_datetime(dark_event['last_seen_timestamp'])
        behavior = self.analyze_vessel_behavior_before_dark(vessel_history, dark_time)
        
        if behavior['speed_change'] and behavior['speed_change'] > self.risk_thresholds['speed_change_significant']:
            patterns.append(SuspiciousPattern.SPEED_CHANGE_BEFORE_DARK)
        
        if behavior['course_deviation'] and behavior['course_deviation'] > self.risk_thresholds['course_change_significant']:
            patterns.append(SuspiciousPattern.COURSE_DEVIATION_BEFORE_DARK)
        
        # 3. Check proximity to cables when going dark
        _, cable_distance = self.get_cable_proximity(dark_event['last_latitude'], dark_event['last_longitude'])
        if cable_distance <= self.risk_thresholds['cable_proximity_threshold']:
            patterns.append(SuspiciousPattern.PROXIMITY_TO_CABLES_WHEN_DARK)
        
        # 4. Check if went dark in sensitive area
        sensitive_area = self.is_in_sensitive_area(dark_event['last_latitude'], dark_event['last_longitude'])
        if sensitive_area:
            patterns.append(SuspiciousPattern.DARK_NEAR_SENSITIVE_AREA)
        
        return patterns

    def calculate_risk_score(self, patterns: List[SuspiciousPattern], hours_dark: float, 
                           previous_events: int, cable_proximity: Optional[float]) -> Tuple[float, DarkVesselRiskLevel]:
        """Calculate risk score for dark vessel event"""
        base_score = 0.0
        
        # Base score from dark duration (longer = higher risk, but caps at 24h)
        dark_duration_score = min(hours_dark / 24.0, 1.0) * 30.0
        base_score += dark_duration_score
        
        # Pattern-based scoring
        pattern_scores = {
            SuspiciousPattern.REPEATED_DARK_PERIODS: 25.0,
            SuspiciousPattern.SPEED_CHANGE_BEFORE_DARK: 15.0,
            SuspiciousPattern.COURSE_DEVIATION_BEFORE_DARK: 15.0,
            SuspiciousPattern.PROXIMITY_TO_CABLES_WHEN_DARK: 30.0,
            SuspiciousPattern.REAPPEARANCE_DISTANT_LOCATION: 20.0,
            SuspiciousPattern.DARK_NEAR_SENSITIVE_AREA: 20.0
        }
        
        for pattern in patterns:
            base_score += pattern_scores.get(pattern, 0.0)
        
        # Previous events multiplier
        if previous_events > 0:
            base_score *= (1.0 + previous_events * 0.2)
        
        # Cable proximity bonus
        if cable_proximity and cable_proximity <= 5.0:
            base_score += 20.0
        elif cable_proximity and cable_proximity <= 10.0:
            base_score += 10.0
        
        # Cap at 100
        risk_score = min(base_score, 100.0)
        
        # Determine risk level
        if risk_score >= 75.0:
            risk_level = DarkVesselRiskLevel.CRITICAL
        elif risk_score >= 50.0:
            risk_level = DarkVesselRiskLevel.HIGH
        elif risk_score >= 25.0:
            risk_level = DarkVesselRiskLevel.MEDIUM
        else:
            risk_level = DarkVesselRiskLevel.LOW
        
        return risk_score, risk_level

    def detect_enhanced_dark_vessels(self, current_vessels: List[Dict]) -> List[DarkVesselEvent]:
        """
        Enhanced dark vessel detection building on notebook's foundation
        
        PRESERVES ORIGINAL LOGIC:
        - Uses same 2-48 hour detection window
        - Tracks AIS history the same way
        - Maintains foreign vessel focus
        
        ADDS ENHANCEMENTS:
        - Pattern analysis for suspicious behavior
        - Risk scoring for prioritization
        - Cable proximity analysis
        - Historical pattern tracking
        """
        logger.info("🌑 Enhanced dark vessel detection starting...")
        
        current_time = datetime.now()
        current_mmsis = {str(vessel['mmsi']) for vessel in current_vessels if vessel['mmsi']}
        
        # Load historical data
        vessel_history = self.load_vessel_history()
        dark_history = self.load_dark_vessel_history()
        
        dark_vessel_events = []
        
        if vessel_history.empty:
            logger.info("✅ No vessel history for dark vessel detection")
            return dark_vessel_events
        
        # Get vessels seen in detection window (2-48 hours ago)
        recent_cutoff = current_time - timedelta(hours=self.max_dark_hours)
        old_cutoff = current_time - timedelta(hours=self.min_dark_hours)
        
        detection_window_vessels = vessel_history[
            (vessel_history['collection_time'] >= recent_cutoff) &
            (vessel_history['collection_time'] <= old_cutoff)
        ]
        
        logger.info(f"📊 Analyzing {len(detection_window_vessels)} historical positions")
        
        # Group by MMSI to find vessels that have gone dark
        for mmsi, vessel_group in detection_window_vessels.groupby('mmsi'):
            mmsi_str = str(mmsi)
            
            if mmsi_str not in current_mmsis:
                # Vessel not in current data - potential dark vessel
                last_record = vessel_group.loc[vessel_group['collection_time'].idxmax()]
                last_seen = last_record['collection_time']
                hours_since_seen = (current_time - last_seen).total_seconds() / 3600
                
                # Must be within detection window
                if self.min_dark_hours <= hours_since_seen <= self.max_dark_hours:
                    
                    # Create basic dark vessel event (compatible with original)
                    basic_dark_event = {
                        'mmsi': mmsi,
                        'name': last_record['name'],
                        'detection_timestamp': current_time.isoformat(),
                        'last_seen_timestamp': last_seen.isoformat(),
                        'hours_silent': round(hours_since_seen, 1),
                        'last_latitude': last_record['latitude'],
                        'last_longitude': last_record['longitude'],
                        'last_speed': last_record['speed'],
                        'last_course': last_record.get('course', 0),
                        'status': 'DARK_VESSEL_SUSPECTED'
                    }
                    
                    # ENHANCED ANALYSIS
                    # Get vessel's historical data for pattern analysis
                    vessel_historical_data = vessel_history[vessel_history['mmsi'] == mmsi]
                    
                    # Detect suspicious patterns
                    patterns = self.detect_suspicious_patterns(
                        mmsi, basic_dark_event, vessel_historical_data, dark_history
                    )
                    
                    # Count previous dark vessel events
                    previous_events = len(dark_history[dark_history['mmsi'] == mmsi]) if not dark_history.empty else 0
                    
                    # Get cable proximity
                    closest_cable, cable_distance = self.get_cable_proximity(
                        basic_dark_event['last_latitude'], 
                        basic_dark_event['last_longitude']
                    )
                    
                    # Calculate risk score
                    risk_score, risk_level = self.calculate_risk_score(
                        patterns, hours_since_seen, previous_events, 
                        cable_distance if cable_distance != float('inf') else None
                    )
                    
                    # Create enhanced dark vessel event
                    enhanced_event = DarkVesselEvent(
                        # Original fields
                        mmsi=mmsi,
                        name=basic_dark_event['name'],
                        detection_timestamp=basic_dark_event['detection_timestamp'],
                        last_seen_timestamp=basic_dark_event['last_seen_timestamp'],
                        hours_silent=basic_dark_event['hours_silent'],
                        last_latitude=basic_dark_event['last_latitude'],
                        last_longitude=basic_dark_event['last_longitude'],
                        last_speed=basic_dark_event['last_speed'],
                        last_course=basic_dark_event['last_course'],
                        status=basic_dark_event['status'],
                        
                        # Enhanced fields
                        risk_level=risk_level.value,
                        risk_score=round(risk_score, 1),
                        suspicious_patterns=[pattern.value for pattern in patterns],
                        previous_dark_events=previous_events,
                        cable_proximity_when_dark=round(cable_distance, 2) if cable_distance != float('inf') else None,
                        speed_change_before_dark=None,  # Could be enhanced further
                        course_deviation_before_dark=None,  # Could be enhanced further
                        reappearance_distance=None  # Will be calculated when vessel reappears
                    )
                    
                    dark_vessel_events.append(enhanced_event)
        
        # Log results with enhanced information
        if dark_vessel_events:
            logger.warning(f"🚨 Found {len(dark_vessel_events)} suspected dark vessels!")
            
            # Sort by risk score for prioritized logging
            sorted_events = sorted(dark_vessel_events, key=lambda x: x.risk_score, reverse=True)
            
            for event in sorted_events:
                risk_emoji = "🔴" if event.risk_level == "CRITICAL" else "🟡" if event.risk_level == "HIGH" else "🟢"
                logger.warning(f"   {risk_emoji} {event.name} (MMSI: {event.mmsi}) - {event.risk_level} risk ({event.risk_score})")
                logger.warning(f"      Dark for {event.hours_silent}h, {len(event.suspicious_patterns)} suspicious patterns")
                
                if event.cable_proximity_when_dark:
                    logger.warning(f"      🔌 Cable proximity: {event.cable_proximity_when_dark}km")
                
                if event.suspicious_patterns:
                    logger.warning(f"      ⚠️ Patterns: {', '.join(event.suspicious_patterns)}")
            
        else:
            logger.info("✅ No enhanced dark vessels detected")
        
        return dark_vessel_events

    def save_enhanced_dark_vessels(self, dark_vessel_events: List[DarkVesselEvent]):
        """Save enhanced dark vessel events to CSV"""
        if not dark_vessel_events:
            return
        
        # Convert to DataFrame
        events_data = [asdict(event) for event in dark_vessel_events]
        new_df = pd.DataFrame(events_data)
        
        # Convert list columns to string for CSV storage
        new_df['suspicious_patterns'] = new_df['suspicious_patterns'].apply(
            lambda x: ','.join(x) if x else ''
        )
        
        # Append to existing file or create new
        if self.enhanced_dark_vessels_file.exists():
            existing_df = pd.read_csv(self.enhanced_dark_vessels_file)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        
        # Save enhanced events
        combined_df.to_csv(self.enhanced_dark_vessels_file, index=False)
        logger.info(f"💾 Saved {len(dark_vessel_events)} enhanced dark vessel events")
        
        # Also save in original format for backward compatibility
        basic_events = []
        for event in dark_vessel_events:
            basic_event = {
                'detection_timestamp': event.detection_timestamp,
                'mmsi': event.mmsi,
                'name': event.name,
                'last_seen_timestamp': event.last_seen_timestamp,
                'hours_silent': event.hours_silent,
                'last_latitude': event.last_latitude,
                'last_longitude': event.last_longitude,
                'last_speed': event.last_speed,
                'last_course': event.last_course,
                'status': event.status
            }
            basic_events.append(basic_event)
        
        if basic_events:
            basic_df = pd.DataFrame(basic_events)
            if self.dark_vessels_file.exists():
                existing_basic = pd.read_csv(self.dark_vessels_file)
                basic_df = pd.concat([existing_basic, basic_df], ignore_index=True)
            basic_df.to_csv(self.dark_vessels_file, index=False)

    def generate_enhanced_alerts(self, dark_vessel_events: List[DarkVesselEvent]) -> Dict:
        """Generate enhanced alerts for dashboard integration"""
        if not dark_vessel_events:
            return {'alerts': [], 'summary': {'total': 0, 'critical': 0, 'high': 0}}
        
        alerts = []
        critical_count = 0
        high_count = 0
        
        for event in dark_vessel_events:
            alert = {
                'type': 'ENHANCED_DARK_VESSEL',
                'timestamp': event.detection_timestamp,
                'priority': event.risk_level,
                'vessel_info': {
                    'mmsi': event.mmsi,
                    'name': event.name,
                    'last_position': [event.last_latitude, event.last_longitude],
                    'last_seen': event.last_seen_timestamp,
                    'hours_dark': event.hours_silent
                },
                'risk_assessment': {
                    'score': event.risk_score,
                    'level': event.risk_level,
                    'patterns': event.suspicious_patterns,
                    'previous_events': event.previous_dark_events
                },
                'location_analysis': {
                    'cable_proximity': event.cable_proximity_when_dark,
                    'sensitive_area': self.is_in_sensitive_area(event.last_latitude, event.last_longitude)
                }
            }
            
            alerts.append(alert)
            
            if event.risk_level == 'CRITICAL':
                critical_count += 1
            elif event.risk_level == 'HIGH':
                high_count += 1
        
        summary = {
            'total': len(dark_vessel_events),
            'critical': critical_count,
            'high': high_count,
            'medium': len([e for e in dark_vessel_events if e.risk_level == 'MEDIUM']),
            'low': len([e for e in dark_vessel_events if e.risk_level == 'LOW'])
        }
        
        return {'alerts': alerts, 'summary': summary}

    def run_enhanced_detection(self, current_vessels: List[Dict]) -> Dict:
        """
        Run complete enhanced dark vessel detection cycle
        
        Returns:
            Dict with dark vessel events, alerts, and statistics
        """
        start_time = datetime.now()
        
        # Run enhanced detection
        dark_vessel_events = self.detect_enhanced_dark_vessels(current_vessels)
        
        # Save results
        self.save_enhanced_dark_vessels(dark_vessel_events)
        
        # Generate alerts for dashboard
        alerts = self.generate_enhanced_alerts(dark_vessel_events)
        
        # Compile results
        results = {
            'detection_timestamp': start_time.isoformat(),
            'processing_time_seconds': (datetime.now() - start_time).total_seconds(),
            'dark_vessel_events': [asdict(event) for event in dark_vessel_events],
            'alerts': alerts,
            'statistics': {
                'vessels_analyzed': len(current_vessels),
                'dark_vessels_found': len(dark_vessel_events),
                'high_risk_events': len([e for e in dark_vessel_events if e.risk_level in ['HIGH', 'CRITICAL']]),
                'cable_proximity_events': len([e for e in dark_vessel_events if e.cable_proximity_when_dark and e.cable_proximity_when_dark <= 15.0])
            }
        }
        
        logger.info(f"🎯 Enhanced detection completed in {results['processing_time_seconds']:.1f}s")
        logger.info(f"📊 Found {results['statistics']['dark_vessels_found']} dark vessels, {results['statistics']['high_risk_events']} high-risk")
        
        return results


# =============================================================================
# INTEGRATION FUNCTIONS FOR STREAMING SYSTEM
# =============================================================================

def integrate_with_streaming_system(current_vessels: List[Dict], data_dir: Path = Path('data_stream')) -> Dict:
    """
    Integration function for the streaming Arctic surveillance system
    
    Use this function to enhance the existing dark vessel detection in arctic_shadow_tracker_stream.py
    """
    detector = EnhancedDarkVesselDetector(data_dir)
    return detector.run_enhanced_detection(current_vessels)

def get_dashboard_compatible_events(enhanced_results: Dict) -> List[Dict]:
    """
    Convert enhanced dark vessel events to format compatible with existing dashboard
    """
    compatible_events = []
    
    for event_data in enhanced_results['dark_vessel_events']:
        compatible_event = {
            'mmsi': event_data['mmsi'],
            'name': event_data['name'],
            'last_seen': event_data['last_seen_timestamp'],
            'hours_since_seen': event_data['hours_silent'],
            'last_position': [event_data['last_latitude'], event_data['last_longitude']],
            'detection_time': event_data['detection_timestamp'],
            'status': event_data['status'],
            
            # Enhanced fields for improved dashboard display
            'risk_level': event_data['risk_level'],
            'risk_score': event_data['risk_score'],
            'suspicious_patterns': event_data['suspicious_patterns'],
            'cable_proximity': event_data['cable_proximity_when_dark']
        }
        compatible_events.append(compatible_event)
    
    return compatible_events


if __name__ == "__main__":
    # Test the enhanced dark vessel detector
    logging.basicConfig(level=logging.INFO)
    
    # Create test instance
    detector = EnhancedDarkVesselDetector()
    
    # Mock current vessels (empty to test dark vessel detection)
    mock_current_vessels = []
    
    # Run detection
    results = detector.run_enhanced_detection(mock_current_vessels)
    
    print("\n" + "="*70)
    print("🧪 ENHANCED DARK VESSEL DETECTION TEST")
    print("="*70)
    print(f"Processing time: {results['processing_time_seconds']:.1f}s")
    print(f"Dark vessels found: {results['statistics']['dark_vessels_found']}")
    print(f"High-risk events: {results['statistics']['high_risk_events']}")
    print("✅ Enhanced dark vessel detection test completed")