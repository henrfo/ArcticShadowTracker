#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Visualization Module
Simple and effective visualizations for Arctic maritime surveillance.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Set style for better plots
plt.style.use('default')
sns.set_palette("husl")

class ArcticVisualizations:
    """
    Simple and practical visualizations for Arctic surveillance operations.
    Focus on clarity and operational utility.
    """
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8)):
        """
        Initialize visualization manager.
        
        Args:
            figsize: Default figure size for plots
        """
        self.figsize = figsize
        self.arctic_bounds = {
            'lat_min': 69.0, 'lat_max': 82.0,
            'lon_min': 5.0, 'lon_max': 35.0
        }
        
        # Arctic submarine cables (simplified)
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
        
        logger.info("ArcticVisualizations initialized")
    
    def plot_arctic_overview(self, 
                           ais_data: List[Dict] = None,
                           sar_detections: List[Dict] = None,
                           threats: List[Dict] = None,
                           title: str = "Arctic Maritime Surveillance Overview") -> plt.Figure:
        """
        Create comprehensive Arctic map with vessels, cables, and threats.
        
        Args:
            ais_data: List of AIS vessel records
            sar_detections: List of SAR detection records  
            threats: List of threat records
            title: Plot title
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Set Arctic bounds
        ax.set_xlim(self.arctic_bounds['lon_min'], self.arctic_bounds['lon_max'])
        ax.set_ylim(self.arctic_bounds['lat_min'], self.arctic_bounds['lat_max'])
        
        # Plot submarine cables
        self._plot_cables(ax)
        
        # Plot vessels
        if ais_data:
            self._plot_ais_vessels(ax, ais_data)
        
        if sar_detections:
            self._plot_sar_detections(ax, sar_detections)
        
        if threats:
            self._plot_threats(ax, threats)
        
        # Styling
        ax.set_xlabel('Longitude (°E)', fontsize=12)
        ax.set_ylabel('Latitude (°N)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Add legend
        self._add_legend(ax)
        
        # Add timestamp
        ax.text(0.02, 0.98, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}',
                transform=ax.transAxes, fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        logger.info(f"Generated Arctic overview plot")
        
        return fig
    
    def plot_threat_heatmap(self, 
                          threats: List[Dict],
                          grid_size: int = 20,
                          title: str = "Arctic Threat Density Heatmap") -> plt.Figure:
        """
        Create threat density heatmap for Arctic region.
        
        Args:
            threats: List of threat records
            grid_size: Grid resolution for heatmap
            title: Plot title
            
        Returns:
            Matplotlib figure
        """
        if not threats:
            logger.warning("No threat data for heatmap")
            fig, ax = plt.subplots(figsize=self.figsize)
            ax.text(0.5, 0.5, 'No Threat Data Available', 
                   transform=ax.transAxes, ha='center', va='center', fontsize=16)
            ax.set_title(title, fontsize=14, fontweight='bold')
            return fig
        
        fig, ax = plt.subplots(figsize=self.figsize)
        
        # Extract coordinates
        lats = [t['latitude'] for t in threats]
        lons = [t['longitude'] for t in threats]
        
        # Create threat weight based on level
        weights = []
        for t in threats:
            level = t.get('threat_level', 'LOW')
            weight_map = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
            weights.append(weight_map.get(level, 1))
        
        # Create 2D histogram
        lon_bins = np.linspace(self.arctic_bounds['lon_min'], self.arctic_bounds['lon_max'], grid_size)
        lat_bins = np.linspace(self.arctic_bounds['lat_min'], self.arctic_bounds['lat_max'], grid_size)
        
        H, lon_edges, lat_edges = np.histogram2d(lons, lats, bins=[lon_bins, lat_bins], weights=weights)
        
        # Plot heatmap
        im = ax.imshow(H.T, origin='lower', extent=[lon_edges[0], lon_edges[-1], lat_edges[0], lat_edges[-1]],
                      cmap='Reds', alpha=0.7, aspect='auto')
        
        # Plot cables for context
        self._plot_cables(ax)
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Threat Density', fontsize=12)
        
        # Styling
        ax.set_xlabel('Longitude (°E)', fontsize=12)
        ax.set_ylabel('Latitude (°N)', fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Add individual threat points
        for threat in threats:
            color_map = {'CRITICAL': 'red', 'HIGH': 'orange', 'MEDIUM': 'yellow', 'LOW': 'green'}
            color = color_map.get(threat.get('threat_level', 'LOW'), 'blue')
            ax.scatter(threat['longitude'], threat['latitude'], 
                      c=color, s=100, edgecolors='black', linewidth=1, alpha=0.8)
        
        plt.tight_layout()
        logger.info(f"Generated threat heatmap with {len(threats)} threats")
        
        return fig
    
    def plot_time_series(self, 
                        historical_data: pd.DataFrame,
                        metrics: List[str] = None,
                        title: str = "Arctic Surveillance Trends") -> plt.Figure:
        """
        Create time series plot of surveillance metrics.
        
        Args:
            historical_data: DataFrame with date and metric columns
            metrics: List of metric columns to plot
            title: Plot title
            
        Returns:
            Matplotlib figure
        """
        if historical_data.empty:
            logger.warning("No historical data for time series")
            fig, ax = plt.subplots(figsize=self.figsize)
            ax.text(0.5, 0.5, 'No Historical Data Available', 
                   transform=ax.transAxes, ha='center', va='center', fontsize=16)
            ax.set_title(title, fontsize=14, fontweight='bold')
            return fig
        
        if metrics is None:
            metrics = ['ais_vessels', 'sar_detections', 'threats_detected']
        
        fig, axes = plt.subplots(len(metrics), 1, figsize=(self.figsize[0], self.figsize[1] * 0.7 * len(metrics)))
        if len(metrics) == 1:
            axes = [axes]
        
        for i, metric in enumerate(metrics):
            if metric in historical_data.columns:
                axes[i].plot(historical_data['date'], historical_data[metric], 
                           marker='o', linewidth=2, markersize=6)
                axes[i].set_ylabel(metric.replace('_', ' ').title(), fontsize=11)
                axes[i].grid(True, alpha=0.3)
                
                # Add trend line if enough data
                if len(historical_data) > 2:
                    z = np.polyfit(range(len(historical_data)), historical_data[metric], 1)
                    p = np.poly1d(z)
                    axes[i].plot(historical_data['date'], p(range(len(historical_data))), 
                               "--", alpha=0.7, color='red', linewidth=1)
            else:
                axes[i].text(0.5, 0.5, f'No data for {metric}', 
                           transform=axes[i].transAxes, ha='center', va='center')
        
        # Format x-axis for dates
        for ax in axes:
            ax.tick_params(axis='x', rotation=45)
        
        plt.suptitle(title, fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        logger.info(f"Generated time series plot with {len(metrics)} metrics")
        return fig
    
    def plot_vessel_analysis(self, 
                           ais_data: List[Dict],
                           title: str = "Vessel Analysis Dashboard") -> plt.Figure:
        """
        Create vessel type and distribution analysis plots.
        
        Args:
            ais_data: List of AIS vessel records
            title: Plot title
            
        Returns:
            Matplotlib figure with subplots
        """
        if not ais_data:
            logger.warning("No AIS data for vessel analysis")
            fig, ax = plt.subplots(figsize=self.figsize)
            ax.text(0.5, 0.5, 'No AIS Data Available', 
                   transform=ax.transAxes, ha='center', va='center', fontsize=16)
            ax.set_title(title, fontsize=14, fontweight='bold')
            return fig
        
        fig = plt.figure(figsize=(15, 10))
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(ais_data)
        
        # 1. Vessel type distribution (pie chart)
        ax1 = plt.subplot(2, 3, 1)
        vessel_types = df['type'].value_counts()
        colors = plt.cm.Set3(np.linspace(0, 1, len(vessel_types)))
        wedges, texts, autotexts = ax1.pie(vessel_types.values, labels=vessel_types.index, 
                                          autopct='%1.1f%%', colors=colors)
        ax1.set_title('Vessel Types', fontsize=12, fontweight='bold')
        
        # 2. Speed distribution
        ax2 = plt.subplot(2, 3, 2)
        speeds = df['speed'].astype(float)
        ax2.hist(speeds, bins=15, alpha=0.7, color='skyblue', edgecolor='black')
        ax2.set_xlabel('Speed (knots)')
        ax2.set_ylabel('Count')
        ax2.set_title('Speed Distribution', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # 3. Geographic distribution
        ax3 = plt.subplot(2, 3, 3)
        lats = df['latitude'].astype(float)
        lons = df['longitude'].astype(float)
        scatter = ax3.scatter(lons, lats, c=speeds, cmap='viridis', alpha=0.7, s=60)
        ax3.set_xlabel('Longitude (°E)')
        ax3.set_ylabel('Latitude (°N)')
        ax3.set_title('Vessel Positions (colored by speed)', fontsize=12, fontweight='bold')
        plt.colorbar(scatter, ax=ax3, label='Speed (knots)')
        ax3.grid(True, alpha=0.3)
        
        # 4. Course distribution (polar plot)
        ax4 = plt.subplot(2, 3, 4, projection='polar')
        courses = df['course'].astype(float) * np.pi / 180  # Convert to radians
        ax4.hist(courses, bins=16, alpha=0.7, color='lightcoral')
        ax4.set_title('Course Distribution', fontsize=12, fontweight='bold', pad=20)
        ax4.set_theta_zero_location('N')
        ax4.set_theta_direction(-1)
        
        # 5. Vessel count by region
        ax5 = plt.subplot(2, 3, 5)
        lat_regions = []
        for lat in lats:
            if lat > 80:
                lat_regions.append('Far North (>80°)')
            elif lat > 75:
                lat_regions.append('North Arctic (75-80°)')
            else:
                lat_regions.append('South Arctic (<75°)')
        
        region_counts = pd.Series(lat_regions).value_counts()
        bars = ax5.bar(range(len(region_counts)), region_counts.values, 
                      color=['lightblue', 'lightgreen', 'lightcoral'])
        ax5.set_xticks(range(len(region_counts)))
        ax5.set_xticklabels(region_counts.index, rotation=45, ha='right')
        ax5.set_ylabel('Vessel Count')
        ax5.set_title('Vessels by Arctic Region', fontsize=12, fontweight='bold')
        ax5.grid(True, alpha=0.3)
        
        # 6. Summary statistics
        ax6 = plt.subplot(2, 3, 6)
        ax6.axis('off')
        
        stats_text = f"""
        VESSEL STATISTICS
        
        Total Vessels: {len(df)}
        
        Speed Stats:
        • Average: {speeds.mean():.1f} knots
        • Max: {speeds.max():.1f} knots
        • Min: {speeds.min():.1f} knots
        
        Geographic Spread:
        • Lat Range: {lats.min():.1f}° - {lats.max():.1f}°N
        • Lon Range: {lons.min():.1f}° - {lons.max():.1f}°E
        
        Most Common Type:
        {vessel_types.index[0]} ({vessel_types.iloc[0]} vessels)
        """
        
        ax6.text(0.1, 0.9, stats_text, transform=ax6.transAxes, fontsize=11, 
                verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
        
        plt.suptitle(title, fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        logger.info(f"Generated vessel analysis with {len(ais_data)} vessels")
        return fig
    
    def save_plot(self, fig: plt.Figure, filename: str, output_dir: str = None) -> str:
        """
        Save plot to file.
        
        Args:
            fig: Matplotlib figure
            filename: Output filename
            output_dir: Output directory (defaults to project outputs/visualizations)
            
        Returns:
            Path to saved file
        """
        if output_dir is None:
            from pathlib import Path
            output_dir = Path(__file__).parent.parent / 'outputs' / 'visualizations'
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp if not in filename
        if not any(char.isdigit() for char in filename):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, 'png')
            filename = f"{name}_{timestamp}.{ext}"
        
        filepath = output_path / filename
        fig.savefig(filepath, dpi=300, bbox_inches='tight')
        
        logger.info(f"Saved plot: {filepath}")
        return str(filepath)
    
    def _plot_cables(self, ax):
        """Plot submarine cables on map"""
        for cable in self.cables:
            points = cable['points']
            lats, lons = zip(*points)
            ax.plot(lons, lats, 'b-', linewidth=3, alpha=0.7, label='Submarine Cables' if cable == self.cables[0] else "")
            
            # Add cable protection zones (5km radius circles)
            for lon, lat in points:
                circle = patches.Circle((lon, lat), 0.045, linewidth=1, 
                                      edgecolor='blue', facecolor='blue', alpha=0.1)
                ax.add_patch(circle)
    
    def _plot_ais_vessels(self, ax, ais_data):
        """Plot AIS vessels on map"""
        lats = [v['latitude'] for v in ais_data]
        lons = [v['longitude'] for v in ais_data]
        ax.scatter(lons, lats, c='green', marker='o', s=60, alpha=0.8, 
                  label='AIS Vessels', edgecolors='black', linewidth=1)
    
    def _plot_sar_detections(self, ax, sar_detections):
        """Plot SAR detections on map"""
        lats = [d['lat'] for d in sar_detections]
        lons = [d['lon'] for d in sar_detections]
        ax.scatter(lons, lats, c='orange', marker='^', s=80, alpha=0.8,
                  label='SAR Detections', edgecolors='black', linewidth=1)
    
    def _plot_threats(self, ax, threats):
        """Plot threats on map with color coding"""
        threat_colors = {'CRITICAL': 'red', 'HIGH': 'orange', 'MEDIUM': 'yellow', 'LOW': 'green'}
        
        for level, color in threat_colors.items():
            level_threats = [t for t in threats if t.get('threat_level') == level]
            if level_threats:
                lats = [t['latitude'] for t in level_threats]
                lons = [t['longitude'] for t in level_threats]
                ax.scatter(lons, lats, c=color, marker='X', s=120, alpha=0.9,
                          label=f'{level} Threats', edgecolors='black', linewidth=1)
    
    def _add_legend(self, ax):
        """Add legend to plot"""
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, loc='upper right', bbox_to_anchor=(1, 1), 
                     framealpha=0.9, fontsize=10)