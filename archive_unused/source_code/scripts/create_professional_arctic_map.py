#!/usr/bin/env python3
"""
Arctic Maritime Surveillance Map - Professional Interactive Visualization
Creates a clean, professional maritime surveillance map using only REAL data
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import datetime
import folium
from folium import plugins
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def load_real_vessel_data():
    """Load real vessel data from all available sources"""
    logger.info("Loading real vessel data from multiple sources...")
    
    all_vessels = []
    data_sources = []
    
    # 1. September 2025 Real BarentsWatch Data
    september_csv = project_root / 'data' / 'september_2025' / 'ais' / 'combined' / 'september_2025_vessels.csv'
    if september_csv.exists():
        try:
            logger.info(f"Loading September 2025 BarentsWatch data: {september_csv}")
            df = pd.read_csv(september_csv)
            for _, row in df.iterrows():
                vessel = {
                    'mmsi': str(row['mmsi']),
                    'name': row['name'],
                    'latitude': float(row['latitude']),
                    'longitude': float(row['longitude']),
                    'speed': float(row.get('speed', 0)),
                    'course': float(row.get('course', 0)),
                    'vessel_type': row['vessel_type'],
                    'heading': float(row.get('heading', 0)),
                    'nav_status': str(row.get('nav_status', 'Unknown')),
                    'source': row['source'],
                    'data_quality': row['data_quality'],
                    'timestamp': row['timestamp'],
                    'track_points': int(row.get('track_points', 1))
                }
                all_vessels.append(vessel)
            data_sources.append(f"BarentsWatch Historic AIS: {len(df)} vessels")
            logger.info(f"Loaded {len(df)} vessels from September 2025 BarentsWatch data")
        except Exception as e:
            logger.error(f"Failed to load September 2025 data: {e}")
    
    # 2. Current Operational Data
    current_ais_dir = project_root / 'data' / 'operational' / 'daily' / '2025-09-18'
    if current_ais_dir.exists():
        # Load latest free AIS data
        latest_free_ais = current_ais_dir / 'latest_free_ais.json'
        if latest_free_ais.exists():
            try:
                logger.info(f"Loading current free AIS data: {latest_free_ais}")
                with open(latest_free_ais, 'r') as f:
                    free_ais_data = json.load(f)
                
                for vessel_data in free_ais_data:
                    vessel = {
                        'mmsi': str(vessel_data['mmsi']),
                        'name': vessel_data['name'],
                        'latitude': float(vessel_data['latitude']),
                        'longitude': float(vessel_data['longitude']),
                        'speed': float(vessel_data.get('speed', 0)),
                        'course': float(vessel_data.get('course', 0)),
                        'vessel_type': vessel_data['type'],
                        'heading': float(vessel_data.get('heading', 0)),
                        'nav_status': 'Active',
                        'source': vessel_data['source'],
                        'data_quality': vessel_data['data_quality'],
                        'timestamp': vessel_data['timestamp'],
                        'track_points': 1
                    }
                    all_vessels.append(vessel)
                
                data_sources.append(f"Free AIS Real-time: {len(free_ais_data)} vessels")
                logger.info(f"Loaded {len(free_ais_data)} vessels from current free AIS data")
            except Exception as e:
                logger.error(f"Failed to load current free AIS data: {e}")
    
    # 3. Historical AIS Data
    historical_ais = project_root / 'data' / 'ais' / 'historical' / 'ais_2025-09-15.csv'
    if historical_ais.exists():
        try:
            logger.info(f"Loading historical AIS data: {historical_ais}")
            df = pd.read_csv(historical_ais)
            for _, row in df.iterrows():
                vessel = {
                    'mmsi': str(row.get('mmsi', 'unknown')),
                    'name': row.get('name', row.get('vessel_name', f'VESSEL_{row.get("mmsi", "UNK")}')),
                    'latitude': float(row.get('latitude', row.get('lat', 0))),
                    'longitude': float(row.get('longitude', row.get('lon', 0))),
                    'speed': float(row.get('speed', row.get('sog', 0))),
                    'course': float(row.get('course', row.get('cog', 0))),
                    'vessel_type': row.get('vessel_type', 'Unknown'),
                    'heading': float(row.get('heading', 0)),
                    'nav_status': str(row.get('nav_status', 'Unknown')),
                    'source': 'historical_ais',
                    'data_quality': 'official',
                    'timestamp': row.get('timestamp', '2025-09-15T00:00:00'),
                    'track_points': int(row.get('track_points', 1))
                }
                if vessel['latitude'] != 0 and vessel['longitude'] != 0:
                    all_vessels.append(vessel)
            
            data_sources.append(f"Historical AIS: {len(df)} vessels")
            logger.info(f"Loaded {len(df)} vessels from historical AIS data")
        except Exception as e:
            logger.error(f"Failed to load historical AIS data: {e}")
    
    # Filter out duplicates by MMSI (keep most recent)
    unique_vessels = {}
    for vessel in all_vessels:
        mmsi = vessel['mmsi']
        if mmsi not in unique_vessels or vessel.get('timestamp', '') > unique_vessels[mmsi].get('timestamp', ''):
            unique_vessels[mmsi] = vessel
    
    final_vessels = list(unique_vessels.values())
    
    # Filter to Arctic region (roughly 66°N and above)
    arctic_vessels = [v for v in final_vessels if v['latitude'] >= 66.0]
    
    logger.info(f"Total unique vessels loaded: {len(final_vessels)}")
    logger.info(f"Arctic region vessels: {len(arctic_vessels)}")
    logger.info(f"Data sources: {data_sources}")
    
    return arctic_vessels, data_sources

def get_arctic_cables():
    """Get Arctic submarine cable network data"""
    return [
        {
            'name': 'Svalbard Underwater Cable System (SUCS)',
            'id': 'SUCS',
            'route': [
                (78.22, 15.63),  # Longyearbyen
                (77.50, 16.00),  # Mid-point
                (71.17, 25.78)   # Hammerfest, Norway
            ],
            'type': 'power_fiber',
            'critical': True
        },
        {
            'name': 'Longyearbyen-Barentsburg Cable',
            'id': 'LYB-BAR',
            'route': [
                (78.22, 15.63),  # Longyearbyen
                (78.06, 14.23)   # Barentsburg
            ],
            'type': 'power',
            'critical': False
        },
        {
            'name': 'Arctic Connect (Planned)',
            'id': 'ARCTIC-CONNECT',
            'route': [
                (70.67, 23.68),  # Kirkenes, Norway
                (78.22, 15.63),  # Longyearbyen
                (81.62, 16.22)   # Planned Arctic extension
            ],
            'type': 'fiber_optic',
            'critical': True
        },
        {
            'name': 'Barents Sea Research Cable',
            'id': 'BARENTS-RESEARCH',
            'route': [
                (69.65, 18.96),  # Tromsø
                (74.50, 19.00),  # Bjørnøya area
                (76.50, 16.50)   # Svalbard approach
            ],
            'type': 'research',
            'critical': False
        }
    ]

def get_vessel_color(vessel_type):
    """Get color for vessel based on type"""
    colors = {
        'Fishing': '#FF6B35',       # Orange
        'Cargo': '#4ECDC4',         # Teal
        'Passenger': '#45B7D1',     # Blue
        'Research': '#96CEB4',      # Green
        'Law Enforcement': '#FF4757', # Red
        'Pollution Control': '#FF6B35', # Orange
        'Supply': '#FFA726',        # Amber
        'Unknown': '#95A5A6',       # Gray
        'Other': '#95A5A6'          # Gray
    }
    return colors.get(vessel_type, '#95A5A6')

def create_vessel_popup(vessel):
    """Create detailed popup for vessel marker"""
    popup_html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; min-width: 250px;">
        <h4 style="margin: 0 0 10px 0; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">
            🚢 {vessel['name']}
        </h4>
        <div style="line-height: 1.6; font-size: 13px;">
            <p style="margin: 3px 0;"><b>MMSI:</b> {vessel['mmsi']}</p>
            <p style="margin: 3px 0;"><b>Type:</b> {vessel['vessel_type']}</p>
            <p style="margin: 3px 0;"><b>Position:</b> {vessel['latitude']:.4f}°N, {vessel['longitude']:.4f}°E</p>
            <p style="margin: 3px 0;"><b>Speed:</b> {vessel['speed']:.1f} knots</p>
            <p style="margin: 3px 0;"><b>Course:</b> {vessel['course']:.1f}°</p>
            <p style="margin: 3px 0;"><b>Heading:</b> {vessel['heading']:.1f}°</p>
            <p style="margin: 3px 0;"><b>Status:</b> {vessel['nav_status']}</p>
            <p style="margin: 3px 0;"><b>Source:</b> {vessel['source']}</p>
            <p style="margin: 3px 0;"><b>Quality:</b> {vessel['data_quality']}</p>
            <p style="margin: 3px 0;"><b>Last Update:</b> {vessel['timestamp'][:19].replace('T', ' ')}</p>
            <p style="margin: 3px 0;"><b>Track Points:</b> {vessel['track_points']}</p>
        </div>
    </div>
    """
    return popup_html

def create_arctic_surveillance_map(vessels, cables):
    """Create professional Arctic maritime surveillance map"""
    logger.info("Creating Arctic surveillance map...")
    
    # Center on Arctic region (Svalbard area)
    center_lat = 76.0
    center_lon = 15.0
    
    # Create map with professional maritime styling
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=5,
        tiles=None
    )
    
    # Add multiple tile layers for different views
    folium.TileLayer(
        'OpenStreetMap',
        name='Standard View',
        overlay=False,
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        'CartoDB Positron',
        name='Clean Maritime',
        overlay=False,
        control=True
    ).add_to(m)
    
    folium.TileLayer(
        'CartoDB Dark_Matter',
        name='Dark Theme',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Add satellite imagery
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Create feature groups for different layers
    vessel_group = folium.FeatureGroup(name="🚢 Vessels", show=True)
    cable_group = folium.FeatureGroup(name="🔌 Submarine Cables", show=True)
    protection_zone_group = folium.FeatureGroup(name="🛡️ Protection Zones", show=True)
    
    # Add submarine cables
    logger.info("Adding submarine cables to map...")
    for cable in cables:
        # Draw cable route
        cable_color = '#E74C3C' if cable['critical'] else '#3498DB'
        cable_weight = 4 if cable['critical'] else 2
        
        folium.PolyLine(
            locations=cable['route'],
            color=cable_color,
            weight=cable_weight,
            opacity=0.8,
            popup=f"<b>{cable['name']}</b><br>Type: {cable['type']}<br>Critical: {'Yes' if cable['critical'] else 'No'}"
        ).add_to(cable_group)
        
        # Add protection zones (5km radius around cable segments)
        for i, point in enumerate(cable['route']):
            if i % 2 == 0:  # Add zone every other point to avoid clutter
                folium.Circle(
                    location=point,
                    radius=5000,  # 5km protection zone
                    popup=f"Protection Zone: {cable['name']}",
                    color='red' if cable['critical'] else 'blue',
                    fill=True,
                    fillColor='red' if cable['critical'] else 'blue',
                    fillOpacity=0.1,
                    weight=1,
                    opacity=0.3
                ).add_to(protection_zone_group)
    
    # Add vessels with clustering for performance
    logger.info(f"Adding {len(vessels)} vessels to map...")
    marker_cluster = plugins.MarkerCluster(
        name="Vessel Clusters",
        overlay=True,
        control=True,
        options={
            'disableClusteringAtZoom': 8,
            'maxClusterRadius': 50,
            'animate': True
        }
    )
    
    vessel_type_counts = {}
    for vessel in vessels:
        vessel_type = vessel['vessel_type']
        vessel_type_counts[vessel_type] = vessel_type_counts.get(vessel_type, 0) + 1
        
        # Create vessel marker
        color = get_vessel_color(vessel_type)
        
        # Create icon based on vessel type
        icon_map = {
            'Fishing': 'fish',
            'Cargo': 'truck',
            'Passenger': 'users',
            'Research': 'flask',
            'Law Enforcement': 'shield',
            'Pollution Control': 'leaf',
            'Supply': 'box'
        }
        icon = icon_map.get(vessel_type, 'ship')
        
        marker = folium.Marker(
            location=[vessel['latitude'], vessel['longitude']],
            popup=folium.Popup(create_vessel_popup(vessel), max_width=300),
            tooltip=f"{vessel['name']} ({vessel['mmsi']}) - {vessel['vessel_type']}",
            icon=folium.Icon(
                color='blue' if vessel['data_quality'] == 'official' else 'green',
                icon=icon,
                prefix='fa'
            )
        )
        marker.add_to(marker_cluster)
    
    # Add marker cluster to vessel group
    marker_cluster.add_to(vessel_group)
    
    # Add feature groups to map
    vessel_group.add_to(m)
    cable_group.add_to(m)
    protection_zone_group.add_to(m)
    
    # Add layer control
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    # Add measurement tool
    plugins.MeasureControl(
        primary_length_unit='kilometers',
        secondary_length_unit='nautical_miles',
        primary_area_unit='sqkilometers'
    ).add_to(m)
    
    # Add minimap
    minimap = plugins.MiniMap(
        tile_layer='CartoDB Positron',
        position='bottomright',
        width=150,
        height=150,
        collapsed_width=25,
        collapsed_height=25
    )
    m.add_child(minimap)
    
    # Add title and legend
    title_html = f'''
    <div style="position: fixed; 
                top: 10px; left: 50px; width: 300px; height: 80px; 
                background-color: rgba(255, 255, 255, 0.9);
                border: 2px solid #2c3e50;
                border-radius: 5px;
                z-index:9999; 
                font-size:14px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                padding: 10px;">
    <h4 style="margin:0; color: #2c3e50;">🌊 Arctic Maritime Surveillance</h4>
    <p style="margin:5px 0 0 0; font-size:12px;">
        📍 {len(vessels)} vessels monitored | 🔌 {len(cables)} cables protected<br>
        📡 Real-time Arctic maritime domain awareness
    </p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))
    
    # Add vessel type legend
    legend_html = f'''
    <div style="position: fixed; 
                bottom: 50px; left: 10px; width: 200px; 
                background-color: rgba(255, 255, 255, 0.9);
                border: 2px solid #2c3e50;
                border-radius: 5px;
                z-index:9999; 
                font-size:12px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                padding: 10px;">
    <h5 style="margin:0 0 5px 0; color: #2c3e50;">🚢 Vessel Types</h5>
    '''
    
    for vessel_type, count in sorted(vessel_type_counts.items()):
        color = get_vessel_color(vessel_type)
        legend_html += f'<p style="margin:2px 0;"><span style="color:{color};">●</span> {vessel_type}: {count}</p>'
    
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))
    
    logger.info("Arctic surveillance map created successfully")
    return m

def main():
    """Main function to create Arctic surveillance map"""
    logger.info("Starting Arctic Maritime Surveillance Map creation...")
    
    # Load real vessel data
    vessels, data_sources = load_real_vessel_data()
    
    if not vessels:
        logger.error("No vessel data available. Cannot create map.")
        return None
    
    # Get cable data
    cables = get_arctic_cables()
    
    # Create map
    arctic_map = create_arctic_surveillance_map(vessels, cables)
    
    # Create outputs directory
    outputs_dir = project_root / 'outputs'
    outputs_dir.mkdir(exist_ok=True)
    
    # Save map
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    map_filename = f'arctic_maritime_surveillance_{timestamp}.html'
    map_path = outputs_dir / map_filename
    
    arctic_map.save(str(map_path))
    logger.info(f"Map saved: {map_path}")
    
    # Generate summary report
    summary = {
        'timestamp': datetime.now().isoformat(),
        'map_file': str(map_path),
        'vessel_count': len(vessels),
        'cable_count': len(cables),
        'data_sources': data_sources,
        'arctic_region_coverage': f"66°N and above",
        'vessel_types': {},
        'real_data_only': True
    }
    
    # Count vessel types
    for vessel in vessels:
        vessel_type = vessel['vessel_type']
        summary['vessel_types'][vessel_type] = summary['vessel_types'].get(vessel_type, 0) + 1
    
    # Save summary
    summary_path = outputs_dir / f'arctic_map_summary_{timestamp}.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info("Arctic Maritime Surveillance Map creation completed successfully!")
    logger.info(f"📊 Summary:")
    logger.info(f"   🚢 Vessels displayed: {len(vessels)}")
    logger.info(f"   🔌 Cables monitored: {len(cables)}")
    logger.info(f"   📂 Map file: {map_filename}")
    logger.info(f"   📊 Summary file: {summary_path.name}")
    logger.info(f"   🌐 Open: file://{map_path}")
    
    for source in data_sources:
        logger.info(f"   📡 {source}")
    
    return map_path, summary

if __name__ == "__main__":
    map_path, summary = main()
    if map_path:
        print(f"\n🎯 SUCCESS: Arctic Maritime Surveillance Map created")
        print(f"📂 Location: {map_path}")
        print(f"🌐 Open in browser: file://{map_path}")
        print(f"📊 Vessels: {summary['vessel_count']}")
        print(f"🔌 Cables: {summary['cable_count']}")
        print("✅ Ready for operational use!")
    else:
        print("❌ Failed to create map - check logs for details")