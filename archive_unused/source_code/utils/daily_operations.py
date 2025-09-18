#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Daily Operations Module
Automated daily surveillance routines and cumulative analysis.
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.data_persistence import DataPersistence
from utils.visualizations import ArcticVisualizations
from detection.vessel_detector import VesselDetector
from detection.cable_monitor import CableMonitor

logger = logging.getLogger(__name__)

class DailyOperations:
    """
    Automated daily surveillance operations with data collection and analysis.
    """
    
    def __init__(self):
        """Initialize daily operations manager."""
        self.data_persistence = DataPersistence()
        self.visualizations = ArcticVisualizations()
        
        # Initialize detection systems
        self.vessel_detector = VesselDetector(
            matching_threshold_meters=1000,
            enable_ml_filtering=True,
            confidence_threshold=0.6
        )
        
        self.cable_monitor = CableMonitor(
            proximity_threshold_km=5.0
        )
        
        logger.info("DailyOperations initialized")
    
    def run_daily_surveillance(self, date_str: str = None) -> Dict[str, Any]:
        """
        Execute complete daily surveillance routine.
        
        Args:
            date_str: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Dictionary with operation results and file paths
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        
        start_time = datetime.now()
        logger.info(f"Starting daily surveillance for {date_str}")
        
        operation_results = {
            'date': date_str,
            'start_time': start_time.isoformat(),
            'status': 'IN_PROGRESS',
            'data_collected': {},
            'files_generated': {},
            'summary': {}
        }
        
        try:
            # Step 1: Collect AIS data with timing
            step_start = time.time()
            ais_data = self._collect_ais_data()
            ais_duration = time.time() - step_start
            operation_results['data_collected']['ais_vessels'] = len(ais_data)
            operation_results['performance'] = {'ais_collection_seconds': round(ais_duration, 2)}
            
            # Step 2: Process satellite data with timing
            step_start = time.time()
            sar_detections = self._process_satellite_data()
            sar_duration = time.time() - step_start
            operation_results['data_collected']['sar_detections'] = len(sar_detections)
            operation_results['performance']['sar_processing_seconds'] = round(sar_duration, 2)
            
            # Step 3: Execute threat detection with timing
            step_start = time.time()
            mission_result = self._execute_threat_detection(ais_data, sar_detections)
            threat_duration = time.time() - step_start
            operation_results['data_collected']['threats'] = len(mission_result.get('threats', []))
            operation_results['performance']['threat_detection_seconds'] = round(threat_duration, 2)
            
            # Step 4: Save data with persistence
            saved_files = self.data_persistence.save_daily_data(
                ais_data=ais_data,
                sar_detections=sar_detections,
                threats=mission_result.get('threats', []),
                mission_summary=mission_result,
                date_str=date_str
            )
            operation_results['files_generated'].update(saved_files)
            
            # Step 5: Generate visualizations
            viz_files = self._generate_daily_visualizations(
                ais_data, sar_detections, mission_result.get('threats', []), date_str
            )
            operation_results['files_generated'].update(viz_files)
            
            # Step 6: Create daily summary report
            daily_summary = self.data_persistence.generate_daily_summary_report(date_str)
            operation_results['summary'] = daily_summary
            
            # Step 7: Update cumulative datasets
            self._update_cumulative_datasets()
            
            # Final status
            end_time = datetime.now()
            operation_results.update({
                'status': 'SUCCESS',
                'end_time': end_time.isoformat(),
                'duration_seconds': (end_time - start_time).total_seconds(),
                'mission_status': mission_result.get('status', 'UNKNOWN')
            })
            
            logger.info(f"Daily surveillance completed successfully for {date_str}")
            logger.info(f"Duration: {operation_results['duration_seconds']:.1f} seconds")
            logger.info(f"Collected: {operation_results['data_collected']}")
            
        except Exception as e:
            logger.error(f"Daily surveillance failed: {e}")
            operation_results.update({
                'status': 'FAILED',
                'error': str(e),
                'end_time': datetime.now().isoformat()
            })
        
        return operation_results
    
    def generate_weekly_report(self, weeks_back: int = 1) -> Dict[str, Any]:
        """
        Generate comprehensive weekly surveillance report.
        
        Args:
            weeks_back: Number of weeks to include in report
            
        Returns:
            Weekly analysis report
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks_back)
        
        logger.info(f"Generating weekly report: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Get historical data
        historical_df = self.data_persistence.get_historical_summary(days_back=weeks_back * 7)
        
        if historical_df.empty:
            return {
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'status': 'NO_DATA',
                'message': 'No surveillance data available for the specified period'
            }
        
        # Calculate weekly statistics
        total_threats = historical_df['threats_detected'].sum()
        total_vessels = historical_df['ais_vessels'].sum()
        total_detections = historical_df['sar_detections'].sum()
        avg_daily_threats = historical_df['threats_detected'].mean()
        
        # Identify peak activity days
        peak_threat_day = historical_df.loc[historical_df['threats_detected'].idxmax()]
        peak_vessel_day = historical_df.loc[historical_df['ais_vessels'].idxmax()]
        
        # Trend analysis
        threat_trend = 'INCREASING' if historical_df['threats_detected'].iloc[-1] > historical_df['threats_detected'].iloc[0] else 'DECREASING'
        vessel_trend = 'INCREASING' if historical_df['ais_vessels'].iloc[-1] > historical_df['ais_vessels'].iloc[0] else 'DECREASING'
        
        weekly_report = {
            'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'generated': datetime.now().isoformat(),
            'status': 'SUCCESS',
            'summary_statistics': {
                'total_surveillance_days': len(historical_df),
                'total_threats_detected': int(total_threats),
                'total_vessels_monitored': int(total_vessels),
                'total_sar_detections': int(total_detections),
                'average_daily_threats': round(avg_daily_threats, 1),
                'average_daily_vessels': round(historical_df['ais_vessels'].mean(), 1)
            },
            'peak_activity': {
                'highest_threat_day': {
                    'date': peak_threat_day['date'].strftime('%Y-%m-%d'),
                    'threats': int(peak_threat_day['threats_detected'])
                },
                'highest_vessel_day': {
                    'date': peak_vessel_day['date'].strftime('%Y-%m-%d'),
                    'vessels': int(peak_vessel_day['ais_vessels'])
                }
            },
            'trends': {
                'threat_trend': threat_trend,
                'vessel_activity_trend': vessel_trend,
                'surveillance_quality': self._assess_surveillance_quality(historical_df)
            }
        }
        
        # Generate weekly visualizations
        try:
            fig = self.visualizations.plot_time_series(
                historical_df, 
                metrics=['ais_vessels', 'sar_detections', 'threats_detected'],
                title=f"Weekly Arctic Surveillance Trends ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})"
            )
            
            viz_path = self.visualizations.save_plot(
                fig, f"weekly_trends_{end_date.strftime('%Y%m%d')}.png"
            )
            weekly_report['visualization'] = viz_path
            
        except Exception as e:
            logger.error(f"Failed to generate weekly visualization: {e}")
            weekly_report['visualization_error'] = str(e)
        
        logger.info(f"Generated weekly report: {total_threats} threats, {total_vessels} vessels monitored")
        return weekly_report
    
    def create_operational_dashboard_data(self) -> Dict[str, Any]:
        """
        Create data package for operational dashboard.
        
        Returns:
            Dictionary with current operational data
        """
        # Get today's data
        today = datetime.now().strftime('%Y-%m-%d')
        daily_data = self.data_persistence.load_daily_data(today)
        
        # Get recent historical context
        historical_df = self.data_persistence.get_historical_summary(days_back=7)
        
        # Get cumulative threat data for analysis
        cumulative_threats = self.data_persistence.create_cumulative_dataset('threats', days_back=30)
        
        dashboard_data = {
            'current_date': today,
            'generated': datetime.now().isoformat(),
            'today_data': daily_data,
            'recent_trends': historical_df.to_dict('records') if not historical_df.empty else [],
            'threat_patterns': self._analyze_threat_patterns(cumulative_threats) if not cumulative_threats.empty else {},
            'surveillance_status': self._get_surveillance_status(daily_data, historical_df)
        }
        
        return dashboard_data
    
    def _collect_ais_data(self) -> List[Dict]:
        """Collect AIS data with improved error handling and caching"""
        import requests
        import json
        
        ais_vessels = []
        
        try:
            # Try live AIS feed with improved timeout and error handling
            url = "http://data.aishub.net/ws.php?username=DH_DEMO&format=1&output=json&compress=0&latmin=69&latmax=82&lonmin=5&lonmax=35"
            response = requests.get(url, timeout=10)  # Reduced timeout
            
            if response.status_code == 200:
                data = response.json()
                vessels_data = data.get('VESSELS', []) if isinstance(data, dict) else []
                
                for vessel in vessels_data[:20]:
                    try:
                        ais_record = {
                            'mmsi': str(vessel.get('MMSI', 'unknown')),
                            'latitude': float(vessel.get('LATITUDE', 0)),
                            'longitude': float(vessel.get('LONGITUDE', 0)),
                            'speed': float(vessel.get('SOG', 0)),
                            'course': float(vessel.get('COG', 0)),
                            'timestamp': datetime.now().isoformat(),
                            'name': vessel.get('SHIPNAME', f'VESSEL_{vessel.get("MMSI", "UNK")}'),
                            'type': vessel.get('SHIP_TYPE', 'Unknown'),
                            'source': 'AIS_LIVE'
                        }
                        if ais_record['latitude'] != 0 and ais_record['longitude'] != 0:
                            ais_vessels.append(ais_record)
                    except (ValueError, TypeError):
                        continue
                
                if ais_vessels:
                    logger.info(f"Collected {len(ais_vessels)} live AIS signals")
                    return ais_vessels
        
        except Exception as e:
            logger.warning(f"Live AIS collection failed: {e}")
        
        # Fallback to local data
        try:
            latest_file = project_root / 'data' / 'ais' / 'latest.json'
            if latest_file.exists():
                with open(latest_file, 'r') as f:
                    ais_vessels = json.load(f)
                logger.info(f"Loaded {len(ais_vessels)} AIS records from cache")
                return ais_vessels
        except Exception as e:
            logger.warning(f"Cache load failed: {e}")
        
        # Final fallback to CSV sample data
        try:
            csv_files = list((project_root / 'data' / 'ais').glob('*.csv'))
            if csv_files:
                import pandas as pd
                df = pd.read_csv(csv_files[0])
                for _, row in df.head(10).iterrows():
                    ais_record = {
                        'mmsi': str(row.get('mmsi', 'unknown')),
                        'latitude': float(row.get('latitude', row.get('lat', 0))),
                        'longitude': float(row.get('longitude', row.get('lon', 0))),
                        'speed': float(row.get('speed', row.get('sog', 0))),
                        'course': float(row.get('course', row.get('cog', 0))),
                        'timestamp': row.get('timestamp', datetime.now().isoformat()),
                        'name': row.get('vessel_name', f'VESSEL_{row.get("mmsi", "UNK")}'),
                        'type': row.get('vessel_type', 'Unknown'),
                        'source': 'FILE_LOCAL'
                    }
                    ais_vessels.append(ais_record)
                
                logger.info(f"Loaded {len(ais_vessels)} AIS records from CSV")
                return ais_vessels
        except Exception as e:
            logger.error(f"CSV fallback failed: {e}")
        
        logger.warning("No AIS data available")
        return []
    
    def _process_satellite_data(self) -> List[Dict]:
        """Process satellite data using vessel detector"""
        satellite_dir = project_root / 'data' / 'satellite'
        sar_files = list(satellite_dir.glob('*.placeholder')) + list(satellite_dir.glob('*.SAFE*'))
        
        all_detections = []
        
        for sar_file in sar_files[:2]:  # Process up to 2 files
            try:
                detections = self.vessel_detector.detect_vessels_in_sar(str(sar_file))
                all_detections.extend(detections)
            except Exception as e:
                logger.error(f"SAR processing failed for {sar_file}: {e}")
        
        logger.info(f"Processed satellite data: {len(all_detections)} detections")
        return all_detections
    
    def _execute_threat_detection(self, ais_data: List[Dict], sar_detections: List[Dict]) -> Dict[str, Any]:
        """Execute threat detection mission"""
        # Find dark vessels
        dark_vessels = []
        if sar_detections:
            dark_vessels = self.vessel_detector.find_dark_vessels(
                sar_detections=sar_detections,
                ais_data=ais_data,
                time_tolerance_minutes=30
            )
        
        # Prepare all vessels for cable proximity check
        all_vessels = []
        
        # Add AIS vessels
        for vessel in ais_data:
            vessel_entry = {
                'vessel_id': vessel['mmsi'],
                'latitude': vessel['latitude'],
                'longitude': vessel['longitude'],
                'timestamp': vessel['timestamp'],
                'vessel_name': vessel['name'],
                'vessel_type': vessel['type'],
                'source': 'AIS',
                'has_ais': True,
                'speed': vessel['speed']
            }
            all_vessels.append(vessel_entry)
        
        # Add dark vessels
        for dark_vessel in dark_vessels:
            vessel_entry = {
                'vessel_id': dark_vessel['detection_id'],
                'latitude': dark_vessel['lat'],
                'longitude': dark_vessel['lon'],
                'timestamp': dark_vessel['detection_time'],
                'vessel_name': 'DARK_VESSEL',
                'vessel_type': 'Unknown',
                'source': 'SAR_DARK',
                'has_ais': False,
                'confidence': dark_vessel['confidence']
            }
            all_vessels.append(vessel_entry)
        
        # Check cable proximity
        vessels_with_cable_info = self.cable_monitor.check_vessel_cable_proximity(all_vessels)
        
        # Generate threats
        threats = []
        for vessel in vessels_with_cable_info:
            if vessel.get('near_cable', False):
                distance = vessel.get('distance_to_cable_km', 999)
                is_dark = not vessel.get('has_ais', True)
                
                if distance < 1 and is_dark:
                    threat_level = 'CRITICAL'
                elif distance < 2 or is_dark:
                    threat_level = 'HIGH'
                else:
                    threat_level = 'MEDIUM'
                
                threat = {
                    'vessel_id': vessel['vessel_id'],
                    'vessel_name': vessel.get('vessel_name', 'Unknown'),
                    'threat_level': threat_level,
                    'distance_to_cable_km': distance,
                    'closest_cable': vessel.get('closest_cable', 'Unknown'),
                    'has_ais': vessel.get('has_ais', True),
                    'latitude': vessel['latitude'],
                    'longitude': vessel['longitude'],
                    'timestamp': vessel['timestamp']
                }
                threats.append(threat)
        
        # Calculate summary
        critical_count = len([t for t in threats if t['threat_level'] == 'CRITICAL'])
        high_count = len([t for t in threats if t['threat_level'] == 'HIGH'])
        dark_count = len([t for t in threats if not t['has_ais']])
        
        if critical_count > 0:
            status = 'CRITICAL_THREATS_DETECTED'
        elif high_count > 0:
            status = 'HIGH_THREATS_DETECTED'
        elif threats:
            status = 'THREATS_DETECTED'
        else:
            status = 'ALL_CLEAR'
        
        return {
            'status': status,
            'threats': threats,
            'summary': {
                'total_threats': len(threats),
                'critical_threats': critical_count,
                'high_threats': high_count,
                'dark_vessels': dark_count,
                'vessels_monitored': len(all_vessels)
            }
        }
    
    def _generate_daily_visualizations(self, ais_data, sar_detections, threats, date_str):
        """Generate daily visualization files"""
        viz_files = {}
        
        try:
            # Arctic overview map
            fig1 = self.visualizations.plot_arctic_overview(
                ais_data=ais_data,
                sar_detections=sar_detections,
                threats=threats,
                title=f"Arctic Surveillance Overview - {date_str}"
            )
            viz_files['overview_map'] = self.visualizations.save_plot(
                fig1, f"arctic_overview_{date_str.replace('-', '')}.png"
            )
            
            # Threat heatmap (if threats exist)
            if threats:
                fig2 = self.visualizations.plot_threat_heatmap(
                    threats=threats,
                    title=f"Threat Density - {date_str}"
                )
                viz_files['threat_heatmap'] = self.visualizations.save_plot(
                    fig2, f"threat_heatmap_{date_str.replace('-', '')}.png"
                )
            
            # Vessel analysis (if AIS data exists)
            if ais_data:
                fig3 = self.visualizations.plot_vessel_analysis(
                    ais_data=ais_data,
                    title=f"Vessel Analysis - {date_str}"
                )
                viz_files['vessel_analysis'] = self.visualizations.save_plot(
                    fig3, f"vessel_analysis_{date_str.replace('-', '')}.png"
                )
            
        except Exception as e:
            logger.error(f"Visualization generation failed: {e}")
            viz_files['error'] = str(e)
        
        return viz_files
    
    def _update_cumulative_datasets(self):
        """Update cumulative datasets for long-term analysis"""
        try:
            # Create 30-day cumulative datasets
            threats_df = self.data_persistence.create_cumulative_dataset('threats', days_back=30)
            ais_df = self.data_persistence.create_cumulative_dataset('ais', days_back=30)
            
            # Save cumulative files
            cumulative_dir = project_root / 'data' / 'operational' / 'cumulative'
            cumulative_dir.mkdir(parents=True, exist_ok=True)
            
            if not threats_df.empty:
                threats_df.to_csv(cumulative_dir / 'threats_30day.csv', index=False)
            
            if not ais_df.empty:
                ais_df.to_csv(cumulative_dir / 'ais_30day.csv', index=False)
            
            logger.info("Updated cumulative datasets")
            
        except Exception as e:
            logger.error(f"Cumulative dataset update failed: {e}")
    
    def _analyze_threat_patterns(self, cumulative_threats) -> Dict:
        """Analyze patterns in cumulative threat data"""
        if cumulative_threats.empty:
            return {}
        
        try:
            patterns = {
                'most_common_threat_level': cumulative_threats['threat_level'].mode()[0],
                'threat_level_distribution': cumulative_threats['threat_level'].value_counts().to_dict(),
                'average_threats_per_day': len(cumulative_threats) / 30,
                'most_threatened_cable': cumulative_threats['closest_cable'].mode()[0] if 'closest_cable' in cumulative_threats.columns else 'Unknown'
            }
            
            return patterns
            
        except Exception as e:
            logger.error(f"Threat pattern analysis failed: {e}")
            return {}
    
    def _assess_surveillance_quality(self, historical_df) -> str:
        """Assess overall surveillance quality from historical data"""
        if historical_df.empty:
            return 'NO_DATA'
        
        # Simple quality assessment based on data availability
        avg_vessels = historical_df['ais_vessels'].mean()
        avg_detections = historical_df['sar_detections'].mean()
        
        if avg_vessels > 10 and avg_detections > 5:
            return 'EXCELLENT'
        elif avg_vessels > 5 and avg_detections > 2:
            return 'GOOD'
        elif avg_vessels > 2 or avg_detections > 1:
            return 'FAIR'
        else:
            return 'LIMITED'
    
    def _get_surveillance_status(self, daily_data, historical_df) -> Dict:
        """Get current surveillance system status"""
        status = {
            'overall': 'OPERATIONAL',
            'ais_status': 'ONLINE' if daily_data.get('ais_data') else 'LIMITED',
            'sar_status': 'ONLINE' if daily_data.get('sar_detections') else 'LIMITED',
            'threat_detection': 'ACTIVE' if daily_data.get('threats') else 'MONITORING',
            'data_quality': self._assess_surveillance_quality(historical_df)
        }
        
        return status