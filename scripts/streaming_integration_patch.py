#!/usr/bin/env python3
"""
Enhanced Dark Vessel Detection Integration Patch
Integrates the enhanced dark vessel detection into the existing streaming system

This patch adds enhanced capabilities while maintaining full backward compatibility
with the existing arctic_shadow_tracker_stream.py system.

USAGE:
1. Import this module in arctic_shadow_tracker_stream.py
2. Replace the basic DarkVesselDetector with EnhancedDarkVesselDetectorProxy
3. All existing functionality remains the same, with added enhancements

ENHANCEMENTS ADDED:
- Pattern analysis for suspicious behavior
- Risk scoring for alert prioritization  
- Behavioral detection before going dark
- Cable proximity correlation
- Advanced alert generation
- Enhanced CSV output with risk assessment
"""

import sys
from pathlib import Path
from typing import List, Dict, Any
import logging
import pandas as pd
from datetime import datetime

# Import the enhanced detector
try:
    from enhanced_dark_vessel_detection import (
        EnhancedDarkVesselDetector, 
        integrate_with_streaming_system,
        get_dashboard_compatible_events
    )
    ENHANCED_DETECTION_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Enhanced dark vessel detection not available: {e}")
    ENHANCED_DETECTION_AVAILABLE = False

logger = logging.getLogger(__name__)

class EnhancedDarkVesselDetectorProxy:
    """
    Proxy class that integrates enhanced detection into the existing streaming system
    
    MAINTAINS COMPATIBILITY:
    - Same interface as original DarkVesselDetector
    - Same method signatures and return formats
    - Falls back to basic detection if enhanced module unavailable
    
    ADDS ENHANCEMENTS:
    - Risk scoring and pattern analysis when available
    - Enhanced logging with priority levels
    - Additional CSV outputs with risk assessment
    - Improved dashboard alerts
    """
    
    def __init__(self, config_obj=None):
        """Initialize enhanced detector with fallback to basic functionality"""
        self.config = config_obj
        
        # File paths - compatible with existing system
        data_dir = Path('data_stream')
        csv_dir = data_dir / 'csv'
        
        self.history_file = csv_dir / 'ais_history.csv'
        self.dark_vessels_file = csv_dir / 'dark_vessels.csv'
        
        # Initialize enhanced detector if available
        if ENHANCED_DETECTION_AVAILABLE:
            try:
                self.enhanced_detector = EnhancedDarkVesselDetector(data_dir)
                self.use_enhanced = True
                logger.info("✅ Enhanced dark vessel detection enabled")
            except Exception as e:
                logger.warning(f"Enhanced detector initialization failed: {e}")
                self.use_enhanced = False
        else:
            self.use_enhanced = False
            logger.info("📊 Using basic dark vessel detection")
        
        # Store last enhanced results for dashboard integration
        self.last_enhanced_results = None

    def load_vessel_history(self) -> pd.DataFrame:
        """Load historical AIS data - same interface as original"""
        if self.use_enhanced:
            return self.enhanced_detector.load_vessel_history()
        
        # Fallback to basic implementation
        if self.history_file.exists():
            try:
                df = pd.read_csv(self.history_file, parse_dates=['timestamp', 'collection_time'])
                # Keep only last 7 days for performance
                cutoff_date = datetime.now() - pd.Timedelta(days=7)
                return df[df['collection_time'] >= cutoff_date]
            except Exception as e:
                logger.error(f"Error loading history: {e}")
                return pd.DataFrame()
        return pd.DataFrame()

    def save_vessel_history(self, df: pd.DataFrame):
        """Save vessel history to CSV - same interface as original"""
        if self.use_enhanced:
            # Enhanced detector saves history automatically during detection
            return
        
        # Fallback to basic implementation
        try:
            df.to_csv(self.history_file, index=False)
        except Exception as e:
            logger.error(f"Error saving history: {e}")

    def update_history(self, current_vessels: List[Dict]) -> pd.DataFrame:
        """Update vessel history with current data - same interface as original"""
        # Load existing history
        history_df = self.load_vessel_history()
        
        # Convert current vessels to DataFrame
        if current_vessels:
            current_df = pd.DataFrame(current_vessels)
            current_df['timestamp'] = pd.to_datetime(current_df['timestamp'])
            current_df['collection_time'] = pd.to_datetime(current_df['collection_time'])
            
            # Append to history
            if not history_df.empty:
                history_df = pd.concat([history_df, current_df], ignore_index=True)
            else:
                history_df = current_df
            
            # Keep only recent data for performance
            cutoff_date = datetime.now() - pd.Timedelta(days=7 if not self.use_enhanced else 30)
            history_df = history_df[history_df['collection_time'] >= cutoff_date]
            
            # Save updated history
            self.save_vessel_history(history_df)
        
        return history_df

    def detect_dark_vessels(self, current_vessels: List[Dict], history_df: pd.DataFrame) -> List[Dict]:
        """
        Detect vessels that have gone dark - ENHANCED VERSION
        
        MAINTAINS COMPATIBILITY:
        - Same return format as original method
        - Basic dark vessel events always included
        
        ADDS ENHANCEMENTS:
        - Risk scoring and pattern analysis
        - Enhanced logging with priority
        - Additional data saved to enhanced CSV
        - Improved alert generation
        """
        if self.use_enhanced:
            try:
                # Use enhanced detection system
                enhanced_results = self.enhanced_detector.run_enhanced_detection(current_vessels)
                self.last_enhanced_results = enhanced_results
                
                # Convert to original format for backward compatibility
                compatible_events = get_dashboard_compatible_events(enhanced_results)
                
                # Log enhanced information
                if enhanced_results['statistics']['dark_vessels_found'] > 0:
                    stats = enhanced_results['statistics']
                    logger.warning(f"🚨 Enhanced detection found {stats['dark_vessels_found']} dark vessels")
                    logger.warning(f"🔴 High-risk events: {stats['high_risk_events']}")
                    logger.warning(f"🔌 Cable proximity events: {stats['cable_proximity_events']}")
                    
                    # Log top-priority events
                    sorted_events = sorted(enhanced_results['dark_vessel_events'], 
                                        key=lambda x: x['risk_score'], reverse=True)
                    
                    for event in sorted_events[:3]:  # Log top 3
                        risk_emoji = "🔴" if event['risk_level'] == "CRITICAL" else "🟡" if event['risk_level'] == "HIGH" else "🟢"
                        logger.warning(f"   {risk_emoji} {event['name']} (MMSI: {event['mmsi']}) - {event['risk_level']} risk ({event['risk_score']})")
                        
                        if event['suspicious_patterns']:
                            patterns = ', '.join(event['suspicious_patterns'])
                            logger.warning(f"      ⚠️  Suspicious patterns: {patterns}")
                
                return compatible_events
                
            except Exception as e:
                logger.error(f"Enhanced detection failed, falling back to basic: {e}")
                # Fall through to basic detection
        
        # Basic detection (original implementation)
        logger.info("🌑 Detecting dark vessels (basic mode)...")
        
        current_time = datetime.now()
        current_mmsis = {str(vessel['mmsi']) for vessel in current_vessels if vessel['mmsi']}
        
        dark_vessels = []
        
        if history_df.empty:
            logger.info("✅ No historical data for dark vessel detection")
            return dark_vessels
        
        # Basic detection parameters
        min_hours = 2
        max_hours = 48
        
        # Get vessels seen in last 48 hours
        recent_cutoff = current_time - pd.Timedelta(hours=max_hours)
        recent_vessels = history_df[history_df['collection_time'] >= recent_cutoff]
        
        # Group by MMSI to find last seen times
        for mmsi, vessel_group in recent_vessels.groupby('mmsi'):
            mmsi_str = str(mmsi)
            if mmsi_str not in current_mmsis:
                # Vessel not in current data - check if it went dark
                last_record = vessel_group.loc[vessel_group['collection_time'].idxmax()]
                last_seen = last_record['collection_time']
                hours_since_seen = (current_time - last_seen).total_seconds() / 3600
                
                # Check if within dark vessel detection window
                if min_hours <= hours_since_seen <= max_hours:
                    dark_vessel = {
                        'mmsi': mmsi,
                        'name': last_record['name'],
                        'last_seen': last_seen.isoformat(),
                        'hours_since_seen': round(hours_since_seen, 1),
                        'last_position': [last_record['latitude'], last_record['longitude']],
                        'detection_time': current_time.isoformat(),
                        'status': 'DARK_VESSEL_SUSPECTED',
                        # Basic compatibility fields
                        'last_latitude': last_record['latitude'],
                        'last_longitude': last_record['longitude'],
                        'last_speed': last_record['speed']
                    }
                    dark_vessels.append(dark_vessel)
        
        if dark_vessels:
            logger.warning(f"🚨 Found {len(dark_vessels)} suspected dark vessels!")
            for vessel in dark_vessels:
                logger.warning(f"   📍 {vessel['name']} (MMSI: {vessel['mmsi']}) - Dark for {vessel['hours_since_seen']}h")
            
            # Save dark vessels to CSV (basic format)
            dark_df = pd.DataFrame(dark_vessels)
            if self.dark_vessels_file.exists():
                existing_dark = pd.read_csv(self.dark_vessels_file)
                dark_df = pd.concat([existing_dark, dark_df], ignore_index=True)
            dark_df.to_csv(self.dark_vessels_file, index=False)
        else:
            logger.info("✅ No dark vessels detected")
        
        return dark_vessels

    def get_enhanced_alerts_for_dashboard(self) -> Dict:
        """Get enhanced alerts for dashboard integration"""
        if self.use_enhanced and self.last_enhanced_results:
            return self.last_enhanced_results.get('alerts', {})
        return {'alerts': [], 'summary': {'total': 0, 'critical': 0, 'high': 0}}

    def get_enhanced_statistics(self) -> Dict:
        """Get enhanced statistics for reporting"""
        if self.use_enhanced and self.last_enhanced_results:
            return self.last_enhanced_results.get('statistics', {})
        return {}


class EnhancedDashboardGenerator:
    """Enhanced dashboard generator with risk-based visualization"""
    
    def __init__(self, enhanced_detector_proxy=None):
        self.enhanced_proxy = enhanced_detector_proxy
        self.dashboard_file = Path('data_stream') / 'dashboard' / 'arctic_surveillance_dashboard.html'
    
    def create_enhanced_dashboard(self, vessels: List[Dict], dark_vessels: List[Dict], cable_alerts: List[Dict]) -> str:
        """Create enhanced dashboard with risk-based coloring and alerts"""
        import folium
        
        logger.info("🗺️ Creating enhanced surveillance dashboard...")
        
        # Center map on Arctic Norway
        m = folium.Map(location=[72.0, 25.0], zoom_start=4)
        
        # Add submarine cables
        submarine_cables = {
            'svalbard_cable': {
                'name': 'Svalbard Undersea Cable System',
                'coordinates': [[78.9, 11.9], [71.0, 25.8]],
                'status': 'CRITICAL'
            },
            'lofoten_vesteralen': {
                'name': 'Lofoten-Vesterålen Cable',
                'coordinates': [[68.8, 13.6], [69.3, 16.0]],
                'status': 'HIGH'
            },
            'norway_uk': {
                'name': 'Norway-UK Cable (Arctic Section)',
                'coordinates': [[70.0, 23.0], [69.0, 18.0]],
                'status': 'HIGH'
            }
        }
        
        for cable_id, cable in submarine_cables.items():
            coords = cable['coordinates']
            if len(coords) >= 2:
                folium.PolyLine(
                    locations=coords,
                    color='red',
                    weight=3,
                    opacity=0.8,
                    popup=f"🔌 {cable['name']} ({cable['status']})"
                ).add_to(m)
        
        # Add current vessels (sample for performance)
        vessel_sample = vessels[:100] if len(vessels) > 100 else vessels
        for vessel in vessel_sample:
            color = 'blue'
            if any(alert['vessel_mmsi'] == vessel['mmsi'] for alert in cable_alerts):
                color = 'orange'  # Near cable
            
            folium.CircleMarker(
                location=[vessel['latitude'], vessel['longitude']],
                radius=5,
                color=color,
                fillColor='lightblue' if color == 'blue' else 'orange',
                fillOpacity=0.7,
                popup=f"🚢 {vessel['name']}<br>MMSI: {vessel['mmsi']}<br>Speed: {vessel['speed']} knots"
            ).add_to(m)
        
        # Add dark vessels with enhanced risk-based coloring
        for vessel in dark_vessels:
            # Get risk level for coloring (if available)
            risk_level = vessel.get('risk_level', 'LOW')
            risk_score = vessel.get('risk_score', 0)
            
            if risk_level == 'CRITICAL':
                color = 'darkred'
                fillColor = 'red'
                radius = 12
            elif risk_level == 'HIGH':
                color = 'red'
                fillColor = 'orange'
                radius = 10
            else:
                color = 'red'
                fillColor = 'yellow'
                radius = 8
            
            # Enhanced popup with risk information
            popup_text = f"🌑 DARK VESSEL<br>{vessel['name']}<br>Missing: {vessel['hours_since_seen']}h"
            
            if risk_score:
                popup_text += f"<br>Risk Score: {risk_score}"
            if vessel.get('suspicious_patterns'):
                patterns = vessel['suspicious_patterns']
                if isinstance(patterns, list):
                    popup_text += f"<br>Patterns: {len(patterns)}"
            if vessel.get('cable_proximity'):
                popup_text += f"<br>Cable: {vessel['cable_proximity']}km"
            
            folium.CircleMarker(
                location=vessel['last_position'],
                radius=radius,
                color=color,
                fillColor=fillColor,
                fillOpacity=0.9,
                popup=popup_text
            ).add_to(m)
        
        # Enhanced statistics overlay
        enhanced_stats = ""
        if self.enhanced_proxy:
            enhanced_alerts = self.enhanced_proxy.get_enhanced_alerts_for_dashboard()
            if enhanced_alerts['summary']['total'] > 0:
                enhanced_stats = f"""
                <p>🔴 Critical: {enhanced_alerts['summary']['critical']}</p>
                <p>🟡 High Risk: {enhanced_alerts['summary']['high']}</p>
                """
        
        stats_html = f"""
        <div style='position: fixed; 
                    top: 10px; left: 50px; width: 220px; height: 160px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px'>
        <h4>🛰️ Enhanced Arctic Surveillance</h4>
        <p>🚢 Vessels: {len(vessels)}</p>
        <p>🌑 Dark Vessels: {len(dark_vessels)}</p>
        <p>⚠️ Cable Alerts: {len(cable_alerts)}</p>
        {enhanced_stats}
        <p>🕐 {datetime.now().strftime('%H:%M:%S')}</p>
        </div>
        """
        m.get_root().html.add_child(folium.Element(stats_html))
        
        # Save dashboard
        m.save(str(self.dashboard_file))
        logger.info(f"✅ Enhanced dashboard saved: {self.dashboard_file}")
        return str(self.dashboard_file)


def patch_streaming_system():
    """
    Apply the enhanced dark vessel detection patch to the streaming system
    
    This function modifies the existing ArcticSurveillanceSystem to use enhanced detection
    while maintaining full backward compatibility.
    """
    try:
        # Import the existing streaming system
        import arctic_shadow_tracker_stream as streaming_system
        
        # Replace the DarkVesselDetector class with our enhanced proxy
        streaming_system.DarkVesselDetector = EnhancedDarkVesselDetectorProxy
        
        # Enhance the dashboard generator if desired
        streaming_system.DashboardGenerator = EnhancedDashboardGenerator
        
        logger.info("✅ Enhanced dark vessel detection patch applied to streaming system")
        return True
        
    except ImportError as e:
        logger.error(f"Could not patch streaming system: {e}")
        return False
    except Exception as e:
        logger.error(f"Error applying patch: {e}")
        return False


# =============================================================================
# STANDALONE ENHANCED STREAMING INTEGRATION
# =============================================================================

def run_enhanced_surveillance_cycle(vessels: List[Dict]) -> Dict:
    """
    Standalone function to run enhanced surveillance cycle
    
    Use this as a drop-in replacement for basic dark vessel detection
    in any streaming system.
    """
    if not ENHANCED_DETECTION_AVAILABLE:
        logger.warning("Enhanced detection not available, using basic detection")
        return {'dark_vessels': [], 'enhanced_results': None}
    
    try:
        # Run enhanced detection
        enhanced_results = integrate_with_streaming_system(vessels)
        
        # Convert to compatible format
        compatible_events = get_dashboard_compatible_events(enhanced_results)
        
        return {
            'dark_vessels': compatible_events,
            'enhanced_results': enhanced_results,
            'alerts': enhanced_results.get('alerts', {}),
            'statistics': enhanced_results.get('statistics', {})
        }
        
    except Exception as e:
        logger.error(f"Enhanced surveillance cycle failed: {e}")
        return {'dark_vessels': [], 'enhanced_results': None, 'error': str(e)}


if __name__ == "__main__":
    """Test the integration patch"""
    logging.basicConfig(level=logging.INFO)
    
    # Test enhanced detector proxy
    logger.info("🧪 Testing enhanced dark vessel detection integration...")
    
    # Create proxy instance
    enhanced_proxy = EnhancedDarkVesselDetectorProxy()
    
    # Test with empty vessel list (to trigger dark vessel detection)
    test_vessels = []
    history_df = enhanced_proxy.load_vessel_history()
    dark_vessels = enhanced_proxy.detect_dark_vessels(test_vessels, history_df)
    
    print("\n" + "="*70)
    print("🧪 ENHANCED INTEGRATION TEST")
    print("="*70)
    print(f"Enhanced detection available: {ENHANCED_DETECTION_AVAILABLE}")
    print(f"Proxy using enhanced mode: {enhanced_proxy.use_enhanced}")
    print(f"Dark vessels found: {len(dark_vessels)}")
    
    if enhanced_proxy.use_enhanced:
        enhanced_alerts = enhanced_proxy.get_enhanced_alerts_for_dashboard()
        print(f"Enhanced alerts available: {len(enhanced_alerts.get('alerts', []))}")
    
    print("✅ Enhanced integration test completed")