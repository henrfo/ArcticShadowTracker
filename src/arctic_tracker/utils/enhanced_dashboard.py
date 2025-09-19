#!/usr/bin/env python3
"""
Enhanced Arctic Dashboard with ALL Vessel Tracks

This module creates an enhanced version of the Arctic surveillance dashboard
that displays 24-hour vessel tracks for ALL vessels with priority styling:
- Russian ships (MMSI starting with 273) in red colors  
- Chinese ships (MMSI starting with 412, 413, 414) in orange colors
- All other vessels in blue/green colors
Each vessel shows as a dot with a line behind it showing movement history.
"""

import json
import folium
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging
import random

logger = logging.getLogger(__name__)

# Configuration
DATA_DIR = Path('arctic_intelligence')

# Arctic submarine cables (same as original system)
SUBMARINE_CABLES = {
    'svalbard_cable': {
        'name': 'Svalbard Undersea Cable System',
        'coordinates': [
            [78.9, 11.9],  # Longyearbyen
            [71.0, 25.8],  # Tromsø connection
        ],
        'status': 'CRITICAL',
        'alert_distance_km': 10
    },
    'lofoten_vesteralen': {
        'name': 'Lofoten-Vesterålen Cable',
        'coordinates': [
            [68.8, 13.6],  # Leknes
            [69.3, 16.0],  # Sortland
        ],
        'status': 'HIGH',
        'alert_distance_km': 5
    },
    'norway_uk': {
        'name': 'Norway-UK Cable (Arctic Section)',
        'coordinates': [
            [70.0, 23.0],  # Northern terminus
            [69.0, 18.0],  # Mid-point
        ],
        'status': 'HIGH',
        'alert_distance_km': 8
    }
}

# GEOPOLITICAL PRIORITY COLOR SCHEMES
# CRITICAL PRIORITY: Russian vessels (Deep dark red/maroon dominance)
RUSSIAN_VESSEL_COLORS = [
    '#800000',  # Maroon (primary - distinctly different)
    '#8B0000',  # DarkRed
    '#A0302E',  # Dark crimson
    '#722F37',  # Deep burgundy
    '#660000',  # Very dark red
    '#4B0000',  # Darkest red
    '#5D1A1A',  # Dark brick
    '#6B0000',  # Deep maroon
    '#7A0000',  # Dark wine
    '#2F0000',  # Almost black red
]

# CRITICAL PRIORITY: Chinese vessels (Bright orange-red prominence)
CHINESE_VESSEL_COLORS = [
    '#FF4500',  # OrangeRed (primary - distinctly different from Russian)
    '#FF6600',  # Bright orange
    '#FF5722',  # Deep orange
    '#FF7043',  # Light orange-red
    '#E65100',  # Dark orange
    '#FF3D00',  # Red-orange
    '#FF6347',  # Tomato
    '#FF4000',  # Vermillion
    '#D84315',  # Deep orange-red
    '#BF360C',  # Dark vermillion
]

# ALERT PRIORITY: Suspicious vessels (Orange warnings)
SUSPICIOUS_VESSEL_COLORS = [
    '#FF8C00',  # DarkOrange (primary)
    '#FF6600',  # Orange
    '#FF7F00',  # Bright orange
    '#FF9500',  # Orange variant
]

# BACKGROUND: Low priority vessels (Muted colors)
NORWEGIAN_VESSEL_COLORS = [
    '#A0A0A0',  # Light grey (primary)
    '#808080',  # Grey
    '#909090',  # Medium grey
    '#B0B0B0',  # Lighter grey
]

OTHER_VESSEL_COLORS = [
    '#228B22',  # Muted forest green (primary)
    '#2E8B57',  # Sea green
    '#3CB371',  # Medium sea green
    '#20B2AA',  # Light sea green
]

def load_vessel_history():
    """Load vessel history from JSON file"""
    history_file = DATA_DIR / 'vessel_history.json'
    if history_file.exists():
        try:
            with open(history_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading vessel history: {e}")
            return {}
    else:
        logger.warning("Vessel history file not found")
        return {}

def load_vessel_positions():
    """Load current vessel positions from CSV with deduplication"""
    positions_file = DATA_DIR / 'vessel_positions.csv'
    if positions_file.exists():
        try:
            df = pd.read_csv(positions_file)
            # Deduplicate by MMSI, keep latest entry
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp').drop_duplicates(subset=['mmsi'], keep='last')
                # Keep only last 24 hours
                cutoff_time = pd.Timestamp.now() - pd.Timedelta(hours=24)
                df = df[df['timestamp'] > cutoff_time]
            else:
                # Fallback deduplication without timestamp
                df = df.drop_duplicates(subset=['mmsi'], keep='last')
            logger.info(f"Loaded {len(df)} deduplicated vessel positions")
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error loading vessel positions: {e}")
            return []
    else:
        logger.warning("Vessel positions file not found")
        return []

def load_dark_vessels():
    """Load dark vessel data from CSV"""
    dark_vessels_file = DATA_DIR / 'dark_vessels.csv'
    if dark_vessels_file.exists():
        try:
            df = pd.read_csv(dark_vessels_file)
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error loading dark vessels: {e}")
            return []
    else:
        return []

def load_cable_alerts():
    """Load cable alert data from CSV"""
    cable_alerts_file = DATA_DIR / 'cable_alerts.csv'
    if cable_alerts_file.exists():
        try:
            df = pd.read_csv(cable_alerts_file)
            return df.to_dict('records')
        except Exception as e:
            logger.error(f"Error loading cable alerts: {e}")
            return []
    else:
        return []

def filter_priority_vessels(vessel_history):
    """Process ALL vessels with priority styling (Russian and Chinese get priority colors)"""
    all_vessels = {}
    russian_count = 0
    chinese_count = 0
    other_count = 0
    
    for mmsi, vessel_data in vessel_history.items():
        # Filter out buoys and platforms (improved pattern matching)
        vessel_name = vessel_data.get('name', '').upper()
        buoy_keywords = [
            'BUOY', 'BOUY', 'BØYE', 'BEACON', 'PLATFORM', 'STATION', 'BUSINKA',
            'TENDER', 'ANCHOR', 'ANKR', 'LORAN', 'MARKER', 'NET MARKER',
            'FISHING NET', 'ANCHOR NET', 'FAERDER', 'BEACON', 'LIGHT'
        ]
        
        # Also check for patterns like "GK BUOY 53", "TRYGVE B BOUY 2", "SAGA BJOERG BU 48", etc.
        is_buoy = (any(keyword in vessel_name for keyword in buoy_keywords) or
                  ' BUOY ' in vessel_name or ' BOUY ' in vessel_name or
                  vessel_name.endswith(' BUOY') or vessel_name.endswith(' BOUY') or
                  vessel_name.startswith('BUOY ') or vessel_name.startswith('BOUY ') or
                  ' BU ' in vessel_name)  # Norwegian buoy pattern
        
        if is_buoy:
            continue  # Skip buoys
            
        all_vessels[mmsi] = vessel_data
        
        if mmsi.startswith('273'):  # Russian vessels
            all_vessels[mmsi]['country'] = 'Russia'
            all_vessels[mmsi]['priority'] = 1
            russian_count += 1
        elif mmsi.startswith(('412', '413', '414')):  # Chinese vessels
            all_vessels[mmsi]['country'] = 'China'
            all_vessels[mmsi]['priority'] = 1
            chinese_count += 1
        elif mmsi.startswith(('257', '258', '259')):  # Norwegian vessels
            all_vessels[mmsi]['country'] = 'Norway'
            all_vessels[mmsi]['priority'] = 3
            other_count += 1
        else:  # Other foreign vessels
            all_vessels[mmsi]['country'] = 'Other'
            all_vessels[mmsi]['priority'] = 2
            other_count += 1
    
    logger.info(f"Processing tracks for {len(all_vessels)} total vessels: {russian_count} Russian, {chinese_count} Chinese, {other_count} others")
    return all_vessels

def filter_recent_positions(positions, hours_back=24):
    """Filter positions to last N hours"""
    cutoff_time = datetime.now() - timedelta(hours=hours_back)
    recent_positions = []
    
    for pos in positions:
        try:
            pos_time = datetime.fromisoformat(pos['timestamp'])
            if pos_time >= cutoff_time:
                recent_positions.append(pos)
        except:
            continue
    
    return recent_positions

def create_vessel_track(vessel_mmsi, vessel_data, map_obj, color):
    """Create track lines for a single vessel"""
    positions = vessel_data.get('positions', [])
    vessel_name = vessel_data.get('name', f'MMSI-{vessel_mmsi}')
    country = vessel_data.get('country', 'Unknown')
    
    # REFINED GEOPOLITICAL PRIORITY SIZING - dot with tail visualization
    if country == 'Russia':
        marker_radius = 4   # Smaller priority dots
    elif country == 'China':
        marker_radius = 3.5 # Smaller priority dots
    elif country == 'Norway':
        marker_radius = 3   # Bigger Norwegian dots
    else:
        marker_radius = 3   # Standard size
    
    # Filter to last 24 hours
    recent_positions = filter_recent_positions(positions, hours_back=24)
    
    if len(recent_positions) < 2:
        return  # Need at least 2 points for a track
    
    # Sort positions by timestamp
    recent_positions.sort(key=lambda x: x['timestamp'])
    
    # Create track coordinates
    track_coords = []
    for pos in recent_positions:
        track_coords.append([pos['latitude'], pos['longitude']])
    
    # Set flag emoji based on country
    flag_emoji = '🇷🇺' if country == 'Russia' else '🇨🇳' if country == 'China' else '🌍'
    
    # GEOPOLITICAL PRIORITY TRACK STYLING
    if len(track_coords) >= 2:
        # Determine line styling based on geopolitical priority
        if country == 'Russia':
            line_weight = 3      # Prominent tracks
            line_opacity = 0.9   # High visibility
            line_dash = None     # Solid line
        elif country == 'China':
            line_weight = 2.5    # Prominent tracks
            line_opacity = 0.85  # High visibility
            line_dash = None     # Solid line
        elif country == 'Norway':
            line_weight = 1.5    # Visible tracks
            line_opacity = 0.6   # Visible but muted
            line_dash = None     # Solid line
        else:
            line_weight = 1.5    # Visible tracks
            line_opacity = 0.7   # Visible visibility
            line_dash = None     # Solid line
            
        folium.PolyLine(
            locations=track_coords,
            color=color,
            weight=line_weight,
            opacity=line_opacity,
            dash_array=line_dash,
            popup=f"{flag_emoji} {vessel_name}<br>📍 MMSI: {vessel_mmsi}<br>🌍 Country: {country}<br>📊 {len(recent_positions)} positions (24h)<br>⏰ Track: {recent_positions[0]['timestamp'][:10]} to {recent_positions[-1]['timestamp'][:10]}",
            tooltip=f"Track: {vessel_name}"
        ).add_to(map_obj)
    
    # Add only current position marker (no start/end markers, no direction arrows)
    if recent_positions:
        # Current position with GEOPOLITICAL PRIORITY STYLING
        current_pos = recent_positions[-1]
        
        # Priority-based styling with transparency for overlapping vessels
        if country == 'Russia':
            fill_opacity = 0.85    # High visibility but with transparency
            stroke_width = 2       # Visible border
            stroke_color = '#000000'  # Black border for contrast
        elif country == 'China':
            fill_opacity = 0.8     # High visibility but with transparency
            stroke_width = 2       # Visible border
            stroke_color = '#000000'  # Black border for contrast
        elif country == 'Norway':
            fill_opacity = 0.4     # Background transparency
            stroke_width = 1       # Minimal border
            stroke_color = color   # Same color border
        else:
            fill_opacity = 0.6     # Medium transparency
            stroke_width = 1       # Minimal border
            stroke_color = color   # Same color border
        
        # Create country label for critical priority vessels
        country_label = f"🇷🇺 RUSSIA" if country == 'Russia' else f"🇨🇳 CHINA" if country == 'China' else ""
        priority_prefix = "⚠️ PRIORITY: " if country in ['Russia', 'China'] else ""
            
        folium.CircleMarker(
            location=[current_pos['latitude'], current_pos['longitude']],
            radius=marker_radius,
            color=stroke_color,
            fillColor=color,
            fillOpacity=fill_opacity,
            weight=stroke_width,
            popup=f"{priority_prefix}{country_label}<br><b>{vessel_name}</b><br>📍 MMSI: {vessel_mmsi}<br>🌍 Country: {country}<br>⏰ {current_pos['timestamp']}<br>⚡ Speed: {current_pos.get('speed', 0)} knots<br>🧭 Course: {current_pos.get('course', 0)}°<br>📊 Track: {len(recent_positions)} positions (24h)",
            tooltip=f"{country_label} {vessel_name}" if country_label else f"{vessel_name}"
        ).add_to(map_obj)

def create_enhanced_dashboard():
    """Create enhanced dashboard with ALL vessel tracks - Main entry point"""
    return create_enhanced_dashboard_with_tracks()

def detect_static_vessels(vessel_history):
    """Detect vessels broadcasting static positions (suspicious AIS) - excluding buoys"""
    static_vessels = []
    
    for mmsi, vessel_data in vessel_history.items():
        positions = vessel_data.get('positions', [])
        if len(positions) < 5:
            continue
            
        # FIRST: Check if this is a buoy or platform (improved filtering)
        vessel_name = vessel_data.get('name', 'Unknown').upper()
        
        # Comprehensive buoy detection patterns
        buoy_keywords = [
            'BUOY', 'BOUY', 'BØYE', 'BEACON', 'PLATFORM', 'STATION', 'BUSINKA',
            'TENDER', 'ANCHOR', 'ANKR', 'LORAN', 'MARKER', 'NET MARKER',
            'FISHING NET', 'ANCHOR NET', 'FAERDER', 'BEACON', 'LIGHT',
            'WEATHER', 'METEO', 'MONITORING', 'RESEARCH PLATFORM',
            'LANBY', 'FAIRWAY', 'CARDINAL', 'LATERAL', 'SAFE WATER', 'SPECIAL MARK',
            'LIGHTHOUSE', 'LIGHTSHIP', 'TOWER', 'PILE', 'SPAR', 'CAN', 'CONICAL',
            'SPHERICAL', 'PILLAR', 'FLOAT', 'MOORING', 'WRECK', 'OBSTRUCTION',
            'DRILLING', 'PRODUCTION', 'FPSO', 'FSO', 'FLNG', 'SEMI-SUB', 'JACK-UP'
        ]
        
        # Enhanced buoy pattern matching
        is_buoy = (
            any(keyword in vessel_name for keyword in buoy_keywords) or
            ' BUOY ' in vessel_name or ' BOUY ' in vessel_name or
            vessel_name.endswith(' BUOY') or vessel_name.endswith(' BOUY') or
            vessel_name.startswith('BUOY ') or vessel_name.startswith('BOUY ') or
            ' BU ' in vessel_name or  # Norwegian buoy pattern
            vessel_name.endswith(' BU') or vessel_name.startswith('BU ') or
            # Pattern like "TRYGVE B BOUY 90 S" - contains BOUY/BUOY anywhere
            'BOUY' in vessel_name or 'BUOY' in vessel_name or
            # Letter + number patterns for buoys
            (len(vessel_name) <= 10 and any(char.isdigit() for char in vessel_name) and 
             any(pattern in vessel_name for pattern in ['MARKER', 'LIGHT', 'BEACON']))
        )
        
        if is_buoy:
            continue  # Skip all buoys from suspicious detection
            
        # Check for multiple suspicious behaviors
        recent_positions = filter_recent_positions(positions, hours_back=6)  # Last 6 hours
        if len(recent_positions) < 3:
            continue
            
        # Check if positions are identical (static broadcasting)
        unique_positions = set()
        for pos in recent_positions:
            lat_rounded = round(pos.get('latitude', 0), 4)  # Round to ~10m precision
            lon_rounded = round(pos.get('longitude', 0), 4)
            unique_positions.add((lat_rounded, lon_rounded))
        
        # Check for extremely low movement (< 100m over multiple hours)
        is_static = len(unique_positions) <= 2 and len(recent_positions) >= 5
        
        # Check for repetitive speed/course (possible spoofing)
        speeds = [pos.get('speed', 0) for pos in recent_positions]
        courses = [pos.get('course', 0) for pos in recent_positions]
        repetitive_data = (len(set(speeds)) <= 2 and len(set(courses)) <= 2 and 
                          len(recent_positions) >= 5)
        
        if is_static or repetitive_data:
            country = 'Unknown'
            if mmsi.startswith('273'):
                country = 'Russia'
            elif mmsi.startswith(('412', '413', '414')):
                country = 'China'
            elif mmsi.startswith(('257', '258', '259')):
                country = 'Norway'
                # Only flag Norwegian vessels if they are clearly NOT buoys and show truly suspicious behavior
                if not is_static:  # Don't flag Norwegian static vessels (likely legitimate platforms)
                    continue
            
            # Only flag actual suspicious vessels (not buoys, not legitimate static infrastructure)
            if country in ['Russia', 'China'] or (country != 'Norway' and not mmsi.startswith(('257', '258', '259'))):
                static_vessels.append({
                    'mmsi': mmsi,
                    'name': vessel_name,
                    'country': country,
                    'position_count': len(recent_positions),
                    'latitude': recent_positions[0]['latitude'],
                    'longitude': recent_positions[0]['longitude'],
                    'behavior': 'Static position' if is_static else 'Repetitive data'
                })
    
    return static_vessels

def create_enhanced_dashboard_with_tracks():
    """Create enhanced Arctic surveillance dashboard with vessel tracks and AIS monitoring"""
    logger.info("Creating enhanced Arctic dashboard with vessel tracks and AIS monitoring...")
    
    # Load all data
    vessel_history = load_vessel_history()
    current_vessels = load_vessel_positions()
    dark_vessels = load_dark_vessels()
    cable_alerts = load_cable_alerts()
    
    # Detect suspicious static vessels
    static_vessels = detect_static_vessels(vessel_history)
    
    # Filter for priority vessels (Russian and Chinese)
    priority_vessels = filter_priority_vessels(vessel_history)
    
    # Create base map
    m = folium.Map(location=[72.0, 25.0], zoom_start=4)
    
    # Add submarine cables
    for cable in SUBMARINE_CABLES.values():
        coords = cable['coordinates']
        if len(coords) >= 2:
            folium.PolyLine(
                locations=coords,
                color='purple',
                weight=4,
                opacity=0.8,
                popup=f"🔌 {cable['name']}<br>Status: {cable['status']}<br>Alert Distance: {cable['alert_distance_km']}km",
                tooltip=f"Cable: {cable['name']}"
            ).add_to(m)
    
    # Add ALL vessel tracks with priority styling
    color_index = 0
    tracked_mmsis = set()  # Track which vessels get tracks
    
    for mmsi, vessel_data in priority_vessels.items():
        country = vessel_data.get('country', 'Unknown')
        priority = vessel_data.get('priority', 2)
        
        # GEOPOLITICAL PRIORITY COLOR ASSIGNMENT
        if country == 'Russia':
            color = RUSSIAN_VESSEL_COLORS[color_index % len(RUSSIAN_VESSEL_COLORS)]
        elif country == 'China':
            color = CHINESE_VESSEL_COLORS[color_index % len(CHINESE_VESSEL_COLORS)]
        elif country == 'Norway':
            color = NORWEGIAN_VESSEL_COLORS[color_index % len(NORWEGIAN_VESSEL_COLORS)]
        else:
            color = OTHER_VESSEL_COLORS[color_index % len(OTHER_VESSEL_COLORS)]
        
        create_vessel_track(mmsi, vessel_data, m, color)
        tracked_mmsis.add(mmsi)
        color_index += 1
    
    # Add any current vessels that don't have tracks (fallback markers)
    for vessel in current_vessels:
        vessel_mmsi = str(vessel.get('mmsi', ''))
        
        # Skip vessels that already have tracks
        if vessel_mmsi in tracked_mmsis:
            continue
            
        country = vessel.get('country', 'Unknown')
        
        # REFINED GEOPOLITICAL PRIORITY for vessels without tracks
        if vessel_mmsi.startswith('273'):  # Russian - CRITICAL PRIORITY
            color = RUSSIAN_VESSEL_COLORS[0]
            fillColor = RUSSIAN_VESSEL_COLORS[0]
            flag_emoji = '🇷🇺'
            marker_radius = 4   # Smaller priority dots
            stroke_width = 0    # No border
            fill_opacity = 0.85
        elif vessel_mmsi.startswith(('412', '413', '414')):  # Chinese - CRITICAL PRIORITY
            color = CHINESE_VESSEL_COLORS[0]
            fillColor = CHINESE_VESSEL_COLORS[0]
            flag_emoji = '🇨🇳'
            marker_radius = 3.5 # Smaller priority dots
            stroke_width = 0    # No border
            fill_opacity = 0.8
        elif vessel_mmsi.startswith(('257', '258', '259')):  # Norwegian - BACKGROUND
            color = NORWEGIAN_VESSEL_COLORS[0]
            fillColor = NORWEGIAN_VESSEL_COLORS[0]
            flag_emoji = '🇳🇴'
            marker_radius = 3   # Bigger Norwegian dots
            stroke_width = 0    # No border
            fill_opacity = 0.4
        else:  # Other foreign - BACKGROUND
            color = OTHER_VESSEL_COLORS[0]
            fillColor = OTHER_VESSEL_COLORS[0]
            flag_emoji = '🌍'
            marker_radius = 3   # Standard size
            stroke_width = 0    # No border
            fill_opacity = 0.6
        
        folium.CircleMarker(
            location=[vessel['latitude'], vessel['longitude']],
            radius=marker_radius,
            color=color,  # Single color, no borders
            fillColor=fillColor,
            fillOpacity=fill_opacity,
            weight=stroke_width,
            popup=f"{flag_emoji} {vessel['name']}<br>🌍 Country: {country}<br>📍 MMSI: {vessel['mmsi']}<br>⚡ Speed: {vessel.get('speed', 0)} knots",
            tooltip=f"{vessel['name']}"
        ).add_to(m)
    
    # Add dark vessels
    for vessel in dark_vessels:
        folium.CircleMarker(
            location=[vessel.get('last_latitude', 0), vessel.get('last_longitude', 0)],
            radius=10,
            color='black',
            fillColor='darkred',
            fillOpacity=0.9,
            popup=f"🌑 DARK VESSEL<br>{vessel.get('name', 'Unknown')}<br>MMSI: {vessel.get('mmsi', 'Unknown')}<br>Dark for: {vessel.get('hours_dark', 0)}h",
            tooltip="Dark Vessel"
        ).add_to(m)
    
    # ALERT PRIORITY: Suspicious static vessels (2.5x larger, orange warning)
    for vessel in static_vessels:
        # Determine flag emoji and priority
        if vessel['country'] == 'Russia':
            flag_emoji = '🇷🇺'
            alert_color = SUSPICIOUS_VESSEL_COLORS[0]  # Orange warning
            priority_text = "SUSPICIOUS AIS - RUSSIAN"
        elif vessel['country'] == 'China':
            flag_emoji = '🇨🇳'
            alert_color = SUSPICIOUS_VESSEL_COLORS[1]  # Orange variant
            priority_text = "SUSPICIOUS AIS - CHINESE"
        else:
            flag_emoji = '⚠️'
            alert_color = SUSPICIOUS_VESSEL_COLORS[2]  # Standard orange
            priority_text = "⚠️ SUSPICIOUS AIS"
        
        # Create animated/blinking marker with warning triangle
        suspicious_html = f'''
        <div style="
            width: 30px; height: 30px; 
            background: {alert_color};
            border: 4px solid #FF0000;
            border-radius: 50%;
            animation: blink 1.5s infinite;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
        ">⚠️</div>
        <style>
        @keyframes blink {{
            0%, 50% {{ opacity: 1; }}
            51%, 100% {{ opacity: 0.3; }}
        }}
        </style>
        '''
        
        folium.CircleMarker(
            location=[vessel['latitude'], vessel['longitude']],
            radius=4,   # Smaller alert dots
            color=alert_color,  # Single color, no border
            fillColor=alert_color,
            fillOpacity=0.9,
            weight=0,  # No border
            popup=f"{priority_text}<br><b>{flag_emoji} {vessel['name']}</b><br>MMSI: {vessel['mmsi']}<br>📍 {vessel['behavior']}: {vessel['position_count']} positions<br>Static/repetitive broadcasting detected<br>🕐 Last 6 hours",
            tooltip=f"⚠️ SUSPICIOUS: {vessel['name']}"
        ).add_to(m)
    
    # Count vessels with tracks by country
    russian_count = len([mmsi for mmsi, data in priority_vessels.items() 
                        if data.get('country') == 'Russia' and len(filter_recent_positions(data.get('positions', []), 24)) > 0])
    chinese_count = len([mmsi for mmsi, data in priority_vessels.items() 
                        if data.get('country') == 'China' and len(filter_recent_positions(data.get('positions', []), 24)) > 0])
    norwegian_count = len([mmsi for mmsi, data in priority_vessels.items() 
                          if data.get('country') == 'Norway' and len(filter_recent_positions(data.get('positions', []), 24)) > 0])
    other_count = len([mmsi for mmsi, data in priority_vessels.items() 
                      if data.get('country') == 'Other' and len(filter_recent_positions(data.get('positions', []), 24)) > 0])
    total_tracks = len([mmsi for mmsi, data in priority_vessels.items() 
                       if len(filter_recent_positions(data.get('positions', []), 24)) > 0])
    
    # Count suspicious vessels by country
    suspicious_russian = len([v for v in static_vessels if v['country'] == 'Russia'])
    suspicious_chinese = len([v for v in static_vessels if v['country'] == 'China'])
    total_suspicious = len(static_vessels)
    
    # Add enhanced information panel
    info_text = f"""
    <div style='position: fixed; top: 10px; right: 10px; background: rgba(255,255,255,0.95); padding: 15px; border: 3px solid #FF0000; border-radius: 8px; z-index: 9999; font-family: Arial; box-shadow: 0 4px 8px rgba(0,0,0,0.3);'>
    <h3 style='margin: 0 0 10px 0; color: #FF0000;'>🌍 Arctic Intelligence</h3>
    <p style='margin: 5px 0;'><b>🚢 Total Vessels:</b> {len(current_vessels)}</p>
    <p style='margin: 5px 0;'><b>📈 Total Tracks:</b> {total_tracks}</p>
    <p style='margin: 5px 0;'><b>🇷🇺 Russian Tracks:</b> {russian_count}</p>
    <p style='margin: 5px 0;'><b>🇨🇳 Chinese Tracks:</b> {chinese_count}</p>
    <p style='margin: 5px 0;'><b>🇳🇴 Norwegian Tracks:</b> {norwegian_count}</p>
    <p style='margin: 5px 0;'><b>🌍 Other Tracks:</b> {other_count}</p>
    <p style='margin: 5px 0;'><b>🌑 Dark Vessels:</b> {len(dark_vessels)}</p>
    <p style='margin: 5px 0;'><b>🚨 Suspicious AIS:</b> {total_suspicious}</p>
    <p style='margin: 5px 0;'><b>⚠️ Cable Alerts:</b> {len(cable_alerts)}</p>
    <p style='margin: 5px 0;'><b>🕐 Updated:</b> {datetime.now().strftime('%H:%M:%S')}</p>
    <hr style='margin: 10px 0;'>
    <p style='margin: 5px 0; font-size: 12px;'><b>Legend (24h tracks):</b></p>
    <p style='margin: 2px 0; font-size: 11px;'><b>🔴 THICK lines/BIG dots:</b> Russian vessels</p>
    <p style='margin: 2px 0; font-size: 11px;'><b>🟠 THICK lines/BIG dots:</b> Chinese vessels</p>
    <p style='margin: 2px 0; font-size: 11px;'>🔵 Medium lines/dots: Other foreign vessels</p>
    <p style='margin: 2px 0; font-size: 11px;'>⚫ Thin lines/small dots: Norwegian vessels</p>
    <p style='margin: 2px 0; font-size: 11px;'>🔴 HUGE dots with red border: Suspicious AIS</p>
    <p style='margin: 2px 0; font-size: 11px;'>🟣 Lines: Submarine cables</p>
    <p style='margin: 2px 0; font-size: 11px;'><b>All tracks show 24h movement history</b></p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(info_text))
    
    # Add legend for vessel tracks
    legend_html = """
    <div style='position: fixed; bottom: 10px; left: 10px; background: rgba(255,255,255,0.9); padding: 10px; border: 2px solid #333; border-radius: 5px; z-index: 9999; font-family: Arial;'>
    <h4 style='margin: 0 0 8px 0;'>🌍 Priority Vessel Tracking</h4>
    <p style='margin: 3px 0; font-size: 12px;'><span style='color: #FF0000;'>●━</span> Russian vessels</p>
    <p style='margin: 3px 0; font-size: 12px;'><span style='color: #FF8C00;'>●━</span> Chinese vessels</p>
    <p style='margin: 3px 0; font-size: 12px;'>● Current position with 24h track</p>
    <p style='margin: 3px 0; font-size: 12px;'>Click markers for details</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Save enhanced dashboard
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    enhanced_map_file = DATA_DIR / f"arctic_dashboard_with_tracks_{timestamp}.html"
    m.save(str(enhanced_map_file))
    
    # Also save as latest
    latest_enhanced_map = DATA_DIR / "arctic_dashboard_with_tracks_latest.html"
    m.save(str(latest_enhanced_map))
    
    logger.info(f"Enhanced dashboard saved: {enhanced_map_file}")
    logger.info(f"Latest enhanced dashboard: {latest_enhanced_map}")
    
    return enhanced_map_file, latest_enhanced_map

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_enhanced_dashboard_with_tracks()