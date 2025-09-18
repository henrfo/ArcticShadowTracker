#!/usr/bin/env python3
"""
Arctic Vessel Visualization System
Simple visualization of vessels on satellite imagery for Arctic maritime surveillance.

This script creates PNG visualizations showing vessel positions overlaid on
Arctic projections with satellite imagery backgrounds where available.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from datetime import datetime
import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Import utility modules
from utils.visualizations import ArcticVisualizations

class ArcticVesselMapper:
    """
    Simple vessel mapping system for Arctic maritime surveillance.
    Creates static PNG visualizations with vessel positions on Arctic projections.
    """
    
    def __init__(self, output_dir: str = None):
        """
        Initialize the Arctic vessel mapper.
        
        Args:
            output_dir: Directory to save visualization outputs
        """
        self.output_dir = output_dir or str(project_root / "outputs" / "visualizations")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Arctic projection bounds (focused on Barents Sea and Svalbard)
        self.arctic_bounds = {
            'lat_min': 69.0, 'lat_max': 82.0,
            'lon_min': 5.0, 'lon_max': 35.0
        }
        
        # Vessel type color mapping for operational clarity
        self.vessel_colors = {
            'Cargo': '#FF6B35',          # Orange - Commercial traffic
            'Tanker': '#F7931E',         # Dark orange - Fuel/chemical transport
            'Fishing': '#4CAF50',        # Green - Fishing vessels
            'Military': '#F44336',       # Red - Military vessels
            'Research': '#2196F3',       # Blue - Research vessels
            'Passenger': '#9C27B0',      # Purple - Passenger transport
            'Pleasure Craft': '#795548', # Brown - Recreational
            'Pilot Vessel': '#607D8B',   # Blue-grey - Pilot services
            'Tug': '#FF9800',           # Amber - Tug boats
            'Supply': '#3F51B5',        # Indigo - Supply vessels
            'Pollution Control': '#009688', # Teal - Environmental
            'Law Enforcement': '#E91E63',   # Pink - Coast guard/police
            'Unknown': '#9E9E9E',       # Grey - Unidentified
            'Dark Vessel': '#000000'     # Black - Unmatched SAR detections
        }
        
        # Critical infrastructure (submarine cables)
        self.cables = [
            {'name': 'Svalbard Underwater Cable System (SUCS)', 
             'points': [(78.2, 15.6), (78.9, 11.9)]},
            {'name': 'Arctic Connect (Planned)',
             'points': [(74.0, 30.0), (76.5, 25.0)]},
            {'name': 'Barents Sea Cable',
             'points': [(71.0, 25.8), (72.5, 28.0)]},
            {'name': 'Norway-Svalbard Link',
             'points': [(71.0, 8.0), (78.2, 15.6)]}
        ]
        
        print(f"Arctic Vessel Mapper initialized")
        print(f"Output directory: {self.output_dir}")
        print(f"Arctic bounds: {self.arctic_bounds}")
    
    def load_vessel_data(self, vessel_file: str) -> pd.DataFrame:
        """
        Load vessel AIS data from CSV file.
        
        Args:
            vessel_file: Path to vessel data CSV file
            
        Returns:
            DataFrame with vessel position data
        """
        try:
            df = pd.read_csv(vessel_file)
            
            # Filter to Arctic region
            arctic_vessels = df[
                (df['latitude'] >= self.arctic_bounds['lat_min']) &
                (df['latitude'] <= self.arctic_bounds['lat_max']) &
                (df['longitude'] >= self.arctic_bounds['lon_min']) &
                (df['longitude'] <= self.arctic_bounds['lon_max'])
            ].copy()
            
            print(f"Loaded {len(df)} total vessels, {len(arctic_vessels)} in Arctic region")
            
            # Ensure required columns exist
            required_columns = ['latitude', 'longitude', 'mmsi']
            for col in required_columns:
                if col not in arctic_vessels.columns:
                    raise ValueError(f"Required column '{col}' not found in vessel data")
            
            # Add vessel type if missing
            if 'vessel_type' not in arctic_vessels.columns:
                arctic_vessels['vessel_type'] = 'Unknown'
            
            # Add name if missing
            if 'name' not in arctic_vessels.columns:
                arctic_vessels['name'] = arctic_vessels['mmsi'].astype(str)
            
            return arctic_vessels
            
        except Exception as e:
            print(f"Error loading vessel data from {vessel_file}: {e}")
            return pd.DataFrame()
    
    def load_satellite_data(self, satellite_file: str) -> pd.DataFrame:
        """
        Load satellite detection data from CSV file.
        
        Args:
            satellite_file: Path to satellite detection CSV file
            
        Returns:
            DataFrame with satellite detection data
        """
        try:
            df = pd.read_csv(satellite_file)
            
            # Filter to Arctic region
            arctic_detections = df[
                (df['latitude'] >= self.arctic_bounds['lat_min']) &
                (df['latitude'] <= self.arctic_bounds['lat_max']) &
                (df['longitude'] >= self.arctic_bounds['lon_min']) &
                (df['longitude'] <= self.arctic_bounds['lon_max'])
            ].copy()
            
            print(f"Loaded {len(df)} total SAR detections, {len(arctic_detections)} in Arctic region")
            return arctic_detections
            
        except Exception as e:
            print(f"Error loading satellite data from {satellite_file}: {e}")
            return pd.DataFrame()
    
    def create_arctic_visualization(self, 
                                  vessels_df: pd.DataFrame, 
                                  satellite_df: pd.DataFrame = None,
                                  title: str = "Arctic Maritime Surveillance") -> str:
        """
        Create Arctic vessel visualization with optional satellite overlay.
        
        Args:
            vessels_df: DataFrame with vessel position data
            satellite_df: Optional DataFrame with satellite detection data
            title: Title for the visualization
            
        Returns:
            Path to saved PNG file
        """
        # Create figure with Arctic-appropriate aspect ratio
        fig, ax = plt.subplots(figsize=(16, 12))
        
        # Set Arctic projection limits
        ax.set_xlim(self.arctic_bounds['lon_min'], self.arctic_bounds['lon_max'])
        ax.set_ylim(self.arctic_bounds['lat_min'], self.arctic_bounds['lat_max'])
        
        # Add coordinate grid
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_xlabel('Longitude (°E)', fontsize=12)
        ax.set_ylabel('Latitude (°N)', fontsize=12)
        
        # Draw submarine cables (critical infrastructure)
        for cable in self.cables:
            points = cable['points']
            if len(points) >= 2:
                lons, lats = zip(*points)
                ax.plot(lons, lats, 'r-', linewidth=2, alpha=0.7, 
                       label='Submarine Cables' if cable == self.cables[0] else "")
        
        # Plot satellite detections if available
        if satellite_df is not None and not satellite_df.empty:
            # Plot matched SAR detections
            matched_sar = satellite_df[satellite_df['dark_vessel'] == False]
            if not matched_sar.empty:
                ax.scatter(matched_sar['longitude'], matched_sar['latitude'],
                          c='yellow', s=50, marker='s', alpha=0.8, 
                          label=f'SAR Detections ({len(matched_sar)})', 
                          edgecolors='orange', linewidths=1)
            
            # Plot dark vessels (unmatched SAR detections)
            dark_vessels = satellite_df[satellite_df['dark_vessel'] == True]
            if not dark_vessels.empty:
                ax.scatter(dark_vessels['longitude'], dark_vessels['latitude'],
                          c='black', s=80, marker='X', alpha=0.9,
                          label=f'Dark Vessels ({len(dark_vessels)})',
                          edgecolors='red', linewidths=2)
        
        # Plot vessels by type
        vessel_counts = {}
        for vessel_type in vessels_df['vessel_type'].unique():
            type_vessels = vessels_df[vessels_df['vessel_type'] == vessel_type]
            vessel_counts[vessel_type] = len(type_vessels)
            
            color = self.vessel_colors.get(vessel_type, self.vessel_colors['Unknown'])
            
            # Plot vessel positions
            scatter = ax.scatter(type_vessels['longitude'], type_vessels['latitude'],
                               c=color, s=60, alpha=0.8, 
                               label=f'{vessel_type} ({len(type_vessels)})',
                               edgecolors='white', linewidths=0.5)
            
            # Add MMSI labels for vessels (limit to avoid overcrowding)
            for idx, vessel in type_vessels.head(20).iterrows():  # Show max 20 labels per type
                ax.annotate(str(vessel['mmsi']), 
                           (vessel['longitude'], vessel['latitude']),
                           xytext=(3, 3), textcoords='offset points',
                           fontsize=8, alpha=0.7, 
                           bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))
        
        # Add geographic landmarks for reference
        landmarks = [
            {'name': 'Svalbard', 'lat': 78.2, 'lon': 15.6},
            {'name': 'Tromsø', 'lat': 69.6, 'lon': 18.9},
            {'name': 'Hammerfest', 'lat': 70.7, 'lon': 23.7},
            {'name': 'Murmansk', 'lat': 68.9, 'lon': 33.1}
        ]
        
        for landmark in landmarks:
            if (self.arctic_bounds['lat_min'] <= landmark['lat'] <= self.arctic_bounds['lat_max'] and
                self.arctic_bounds['lon_min'] <= landmark['lon'] <= self.arctic_bounds['lon_max']):
                ax.scatter(landmark['lon'], landmark['lat'], 
                          c='red', s=100, marker='^', 
                          edgecolors='black', linewidths=1)
                ax.annotate(landmark['name'], 
                           (landmark['lon'], landmark['lat']),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=10, fontweight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8))
        
        # Customize legend
        legend = ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', 
                          fontsize=10, framealpha=0.9)
        legend.set_title("Maritime Elements", prop={'size': 12, 'weight': 'bold'})
        
        # Add title and metadata
        plt.title(f"{title}\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}", 
                 fontsize=16, fontweight='bold', pad=20)
        
        # Add statistics text box
        total_vessels = len(vessels_df)
        stats_text = f"Total Vessels: {total_vessels}\n"
        stats_text += f"Coordinate Range: {self.arctic_bounds['lat_min']:.1f}°N - {self.arctic_bounds['lat_max']:.1f}°N\n"
        stats_text += f"                 {self.arctic_bounds['lon_min']:.1f}°E - {self.arctic_bounds['lon_max']:.1f}°E"
        
        if satellite_df is not None and not satellite_df.empty:
            stats_text += f"\nSAR Detections: {len(satellite_df)}"
            dark_count = len(satellite_df[satellite_df['dark_vessel'] == True])
            if dark_count > 0:
                stats_text += f"\nDark Vessels: {dark_count}"
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
               fontsize=10, verticalalignment='top',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.8))
        
        # Add data source attribution
        attribution = "Data Sources: BarentsWatch AIS, Sentinel-1 SAR\nArctic Shadow Tracker System"
        ax.text(0.98, 0.02, attribution, transform=ax.transAxes, 
               fontsize=9, horizontalalignment='right', verticalalignment='bottom',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        
        # Adjust layout and save
        plt.tight_layout()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"arctic_maritime_surveillance_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        
        plt.savefig(filepath, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        print(f"Visualization saved: {filepath}")
        print(f"Image dimensions: 4800x3600 pixels (300 DPI)")
        print(f"Vessels plotted: {total_vessels}")
        print(f"Coordinate ranges: {self.arctic_bounds}")
        
        return filepath


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Arctic Vessel Visualization System")
    parser.add_argument("--vessel-data", required=True, 
                       help="Path to vessel CSV data file")
    parser.add_argument("--satellite-data", 
                       help="Path to satellite detection CSV file (optional)")
    parser.add_argument("--output-dir", 
                       help="Output directory for visualizations")
    parser.add_argument("--title", default="Arctic Maritime Surveillance",
                       help="Title for the visualization")
    
    args = parser.parse_args()
    
    # Initialize mapper
    mapper = ArcticVesselMapper(output_dir=args.output_dir)
    
    # Load data
    print("Loading vessel data...")
    vessels_df = mapper.load_vessel_data(args.vessel_data)
    
    if vessels_df.empty:
        print("Error: No valid vessel data loaded. Exiting.")
        return 1
    
    satellite_df = None
    if args.satellite_data:
        print("Loading satellite data...")
        satellite_df = mapper.load_satellite_data(args.satellite_data)
    
    # Create visualization
    print("Creating Arctic visualization...")
    output_file = mapper.create_arctic_visualization(
        vessels_df, satellite_df, args.title
    )
    
    print(f"\nVisualization complete!")
    print(f"Output file: {output_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())