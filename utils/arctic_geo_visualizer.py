#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Interactive Geo Visualization
Simple, focused Arctic intelligence mapping for maritime surveillance.
"""

import folium
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ArcticGeoVisualizer:
    """
    Simple Arctic geo-visualization system for maritime intelligence.
    Creates interactive maps for vessel tracking and threat analysis.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize Arctic geo visualizer."""
        self.output_dir = Path(output_dir) if output_dir else Path("outputs/interactive_maps")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Arctic region boundaries
        self.arctic_bounds = {
            'south': 69.0,
            'north': 82.0, 
            'west': 5.0,
            'east': 35.0
        }
        
        # Arctic submarine cables (real data)
        self.arctic_cables = [
            {
                'name': 'Svalbard Underwater Cable System (SUCS)',
                'route': [(78.22, 15.63), (77.50, 16.00), (71.17, 25.78)],
                'critical': True
            },
            {
                'name': 'Longyearbyen-Barentsburg Cable', 
                'route': [(78.22, 15.63), (78.065, 14.233)],
                'critical': False
            },
            {
                'name': 'Arctic Connect (Planned)',
                'route': [(71.17, 25.78), (74.0, 30.0), (78.22, 15.63), (81.0, 20.0)],
                'critical': True
            },
            {
                'name': 'Murmansk-Svalbard Research Link',
                'route': [(68.97, 33.08), (74.5, 35.0), (78.22, 15.63)],
                'critical': False
            }
        ]
        
        logger.info("ArcticGeoVisualizer initialized")
    
    def create_arctic_intelligence_map(self, data: Dict, title: str = "Arctic Intelligence", 
                                     show_cables: bool = True, show_threat_zones: bool = True,
                                     show_protection_zones: bool = True) -> folium.Map:
        """
        Create comprehensive Arctic intelligence map.
        
        Args:
            data: Dictionary containing ais_data, sar_detections, threats, dark_vessels
            title: Map title
            show_cables: Show submarine cables
            show_threat_zones: Show threat zones
            show_protection_zones: Show cable protection zones
            
        Returns:
            Folium map object
        """
        # Center map on Arctic region
        center_lat = (self.arctic_bounds['south'] + self.arctic_bounds['north']) / 2
        center_lon = (self.arctic_bounds['west'] + self.arctic_bounds['east']) / 2
        
        # Create base map
        arctic_map = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=4,
            tiles='OpenStreetMap'
        )
        
        # Add title
        title_html = f'''
        <h3 align="center" style="font-size:16px; color:darkblue; margin-top:0;">
        <b>{title}</b>
        </h3>
        '''
        arctic_map.get_root().html.add_child(folium.Element(title_html))
        
        # Add alternative tile layers (using simple, reliable sources)
        folium.TileLayer(
            tiles='CartoDB positron',
            name='Light Theme',
            attr='© CartoDB, © OpenStreetMap contributors'
        ).add_to(arctic_map)
        
        folium.TileLayer(
            tiles='CartoDB dark_matter',
            name='Dark Theme',
            attr='© CartoDB, © OpenStreetMap contributors'
        ).add_to(arctic_map)
        
        # Add submarine cables
        if show_cables:
            self._add_submarine_cables(arctic_map, show_protection_zones)
        
        # Add threat zones
        if show_threat_zones:
            self._add_threat_zones(arctic_map)
        
        # Add AIS vessels
        ais_data = data.get('ais_data', [])
        if ais_data:
            self._add_ais_vessels(arctic_map, ais_data)
        
        # Add SAR detections
        sar_detections = data.get('sar_detections', [])
        if sar_detections:
            self._add_sar_detections(arctic_map, sar_detections)
        
        # Add threats
        threats = data.get('threats', [])
        if threats:
            self._add_threat_markers(arctic_map, threats)
        
        # Add layer control
        folium.LayerControl().add_to(arctic_map)
        
        # Add measurement tool
        from folium.plugins import MeasureControl
        arctic_map.add_child(MeasureControl())
        
        # Add coordinate display
        from folium.plugins import MousePosition
        MousePosition().add_to(arctic_map)
        
        logger.info(f"Created Arctic intelligence map with {len(ais_data)} AIS vessels, {len(sar_detections)} SAR detections, {len(threats)} threats")
        
        return arctic_map
    
    def _add_submarine_cables(self, map_obj: folium.Map, show_protection_zones: bool):
        """Add submarine cables to map."""
        cable_group = folium.FeatureGroup(name="Submarine Cables")
        
        for cable in self.arctic_cables:
            # Cable route
            color = 'red' if cable['critical'] else 'orange'
            
            folium.PolyLine(
                locations=cable['route'],
                color=color,
                weight=3,
                opacity=0.8,
                popup=f"<b>{cable['name']}</b><br>Critical: {cable['critical']}"
            ).add_to(cable_group)
            
            # Protection zones (5km radius around cable endpoints)
            if show_protection_zones:
                for point in [cable['route'][0], cable['route'][-1]]:
                    folium.Circle(
                        location=point,
                        radius=5000,  # 5km
                        color=color,
                        fillColor=color,
                        fillOpacity=0.1,
                        popup=f"Protection Zone: {cable['name']}"
                    ).add_to(cable_group)
        
        cable_group.add_to(map_obj)
    
    def _add_threat_zones(self, map_obj: folium.Map):
        """Add known threat zones to map."""
        threat_group = folium.FeatureGroup(name="Threat Zones")
        
        # Define threat zones
        zones = [
            {'name': 'Kola Peninsula', 'center': [69.0, 33.0], 'radius': 50000, 'level': 'HIGH'},
            {'name': 'Svalbard Waters', 'center': [78.5, 16.0], 'radius': 75000, 'level': 'MEDIUM'},
            {'name': 'Barents Sea Central', 'center': [74.0, 30.0], 'radius': 100000, 'level': 'MEDIUM'},
            {'name': 'Franz Josef Land', 'center': [80.5, 55.0], 'radius': 60000, 'level': 'HIGH'}
        ]
        
        for zone in zones:
            color = 'red' if zone['level'] == 'HIGH' else 'yellow'
            folium.Circle(
                location=zone['center'],
                radius=zone['radius'],
                color=color,
                fillColor=color,
                fillOpacity=0.05,
                popup=f"<b>{zone['name']}</b><br>Threat Level: {zone['level']}"
            ).add_to(threat_group)
        
        threat_group.add_to(map_obj)
    
    def _add_ais_vessels(self, map_obj: folium.Map, ais_data: List[Dict]):
        """Add AIS vessels to map."""
        ais_group = folium.FeatureGroup(name="AIS Vessels")
        
        for vessel in ais_data:
            try:
                lat = float(vessel['latitude'])
                lon = float(vessel['longitude'])
                
                # Vessel icon based on type
                vessel_type = vessel.get('type', 'Unknown').lower()
                if 'fish' in vessel_type:
                    icon_color = 'blue'
                    icon = 'ship'
                elif 'cargo' in vessel_type:
                    icon_color = 'green' 
                    icon = 'ship'
                elif 'research' in vessel_type:
                    icon_color = 'purple'
                    icon = 'star'
                else:
                    icon_color = 'gray'
                    icon = 'ship'
                
                # Create popup with vessel info
                popup_html = f"""
                <b>{vessel.get('name', 'Unknown')}</b><br>
                MMSI: {vessel.get('mmsi', 'Unknown')}<br>
                Type: {vessel.get('type', 'Unknown')}<br>
                Speed: {vessel.get('speed', 0):.1f} knots<br>
                Course: {vessel.get('course', 0):.0f}°<br>
                Position: {lat:.3f}°N, {lon:.3f}°E<br>
                Time: {vessel.get('timestamp', 'Unknown')}
                """
                
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=300),
                    icon=folium.Icon(color=icon_color, icon=icon)
                ).add_to(ais_group)
                
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping malformed AIS vessel: {e}")
                continue
        
        ais_group.add_to(map_obj)
    
    def _add_sar_detections(self, map_obj: folium.Map, sar_detections: List[Dict]):
        """Add SAR detections to map."""
        sar_group = folium.FeatureGroup(name="SAR Detections")
        
        for detection in sar_detections:
            try:
                lat = float(detection['lat'])
                lon = float(detection['lon'])
                confidence = detection.get('confidence', 0.5)
                
                # Color based on confidence
                if confidence > 0.8:
                    color = 'red'
                elif confidence > 0.6:
                    color = 'orange'
                else:
                    color = 'yellow'
                
                popup_html = f"""
                <b>SAR Detection</b><br>
                ID: {detection.get('detection_id', 'Unknown')}<br>
                Confidence: {confidence:.2f}<br>
                Position: {lat:.3f}°N, {lon:.3f}°E<br>
                Time: {detection.get('detection_time', 'Unknown')}<br>
                Source: {detection.get('source_file', 'Unknown')}
                """
                
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=8,
                    color=color,
                    fillColor=color,
                    fillOpacity=0.6,
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(sar_group)
                
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping malformed SAR detection: {e}")
                continue
        
        sar_group.add_to(map_obj)
    
    def _add_threat_markers(self, map_obj: folium.Map, threats: List[Dict]):
        """Add threat markers to map."""
        threat_group = folium.FeatureGroup(name="Active Threats")
        
        for threat in threats:
            try:
                lat = float(threat['latitude'])
                lon = float(threat['longitude'])
                level = threat.get('threat_level', 'MEDIUM')
                
                # Threat level styling
                if level == 'CRITICAL':
                    color = 'darkred'
                    icon = 'exclamation-triangle'
                elif level == 'HIGH':
                    color = 'red'
                    icon = 'warning'
                else:
                    color = 'orange'
                    icon = 'info'
                
                popup_html = f"""
                <b>🚨 THREAT ALERT</b><br>
                Level: <b>{level}</b><br>
                Vessel: {threat.get('vessel_name', 'Unknown')}<br>
                ID: {threat.get('vessel_id', 'Unknown')}<br>
                Cable: {threat.get('closest_cable', 'Unknown')}<br>
                Distance: {threat.get('distance_to_cable_km', 0):.1f} km<br>
                AIS Status: {"✅ Active" if threat.get('has_ais', True) else "❌ Dark"}<br>
                Time: {threat.get('timestamp', 'Unknown')}
                """
                
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=300),
                    icon=folium.Icon(color=color, icon=icon)
                ).add_to(threat_group)
                
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping malformed threat: {e}")
                continue
        
        threat_group.add_to(map_obj)
    
    def save_map(self, map_obj: folium.Map, filename: str) -> str:
        """Save map to HTML file."""
        file_path = self.output_dir / filename
        map_obj.save(str(file_path))
        logger.info(f"Map saved to {file_path}")
        return str(file_path)