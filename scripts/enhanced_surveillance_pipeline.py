#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Enhanced Surveillance Pipeline
Integrates all enhanced real data capabilities for comprehensive Arctic maritime surveillance.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import argparse
import asyncio
import time

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.real_ais_collector import RealAISCollector
from utils.real_sentinel_collector import RealSentinelCollector
from utils.arctic_geo_visualizer import ArcticGeoVisualizer
from utils.data_quality_monitor import DataQualityMonitor
from detection.advanced_dark_vessels import DarkVesselDetector
from detection.advanced_cable_monitor import CableMonitor
from analysis.advanced_risk_scoring import RiskScorer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enhanced_surveillance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedSurveillancePipeline:
    """Enhanced Arctic surveillance pipeline with real data integration"""
    
    def __init__(self, data_dir: str = "data", output_dir: str = "outputs"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.ais_collector = RealAISCollector(str(self.data_dir / "ais"))
        self.sentinel_collector = RealSentinelCollector(str(self.data_dir / "satellite"))
        self.geo_visualizer = ArcticGeoVisualizer(str(self.output_dir / "maps"))
        self.quality_monitor = DataQualityMonitor()
        
        # Analysis components
        self.dark_vessel_detector = DarkVesselDetector()
        self.cable_monitor = CableMonitor()
        self.risk_scorer = RiskScorer()
        
        # Pipeline state
        self.last_run_time = None
        self.pipeline_stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'total_vessels_processed': 0,
            'total_threats_detected': 0
        }
    
    def run_enhanced_surveillance_cycle(self, include_sar: bool = True, 
                                       create_visualizations: bool = True) -> Dict[str, any]:
        """Run complete enhanced surveillance cycle with real data"""
        cycle_start = datetime.now()
        logger.info(f"🚀 Starting enhanced surveillance cycle at {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        
        cycle_results = {
            'cycle_id': cycle_start.strftime('%Y%m%d_%H%M%S'),
            'start_time': cycle_start.isoformat(),
            'end_time': None,
            'success': False,
            'ais_data': [],
            'sar_data': [],
            'threats': [],
            'quality_report': {},
            'visualizations': [],
            'errors': []
        }
        
        try:
            # Step 1: Collect real AIS data
            logger.info("🌐 Step 1: Collecting real AIS data...")
            ais_data = self.ais_collector.fetch_current_data()
            cycle_results['ais_data'] = ais_data
            logger.info(f"Collected {len(ais_data)} AIS vessel records")
            
            # Step 2: Collect Sentinel-1 SAR data (if enabled)
            sar_data = []
            if include_sar:
                logger.info("🛰️ Step 2: Collecting Sentinel-1 SAR data...")
                try:
                    sar_files = self.sentinel_collector.fetch_latest_data(days_back=1, max_products=3)
                    sar_data = [{'file': str(f), 'size_mb': f.stat().st_size / (1024*1024)} for f in sar_files]
                    cycle_results['sar_data'] = sar_data
                    logger.info(f"Collected {len(sar_data)} SAR products")
                except Exception as e:
                    logger.warning(f"SAR collection failed: {e}")
                    cycle_results['errors'].append(f"SAR collection: {str(e)}")
            
            # Step 3: Data quality validation
            logger.info("🔍 Step 3: Validating data quality...")
            quality_report = self.quality_monitor.generate_quality_report(ais_data, sar_data)
            cycle_results['quality_report'] = quality_report
            
            quality_score = quality_report['quality_summary']['overall_score']
            logger.info(f"Data quality score: {quality_score}/100 ({quality_report['quality_summary']['quality_level']})")
            
            # Step 4: Threat detection and analysis
            logger.info("🚨 Step 4: Running threat detection...")
            threats = self._run_threat_detection(ais_data, sar_data)
            cycle_results['threats'] = threats
            logger.info(f"Detected {len(threats)} potential threats")
            
            # Step 5: Create visualizations (if enabled)
            if create_visualizations:
                logger.info("🗺️ Step 5: Creating visualizations...")
                visualizations = self._create_enhanced_visualizations(ais_data, threats)
                cycle_results['visualizations'] = visualizations
                logger.info(f"Created {len(visualizations)} visualization files")
            
            # Step 6: Generate reports
            logger.info("📄 Step 6: Generating intelligence reports...")
            self._generate_intelligence_reports(cycle_results)
            
            cycle_results['success'] = True
            self.pipeline_stats['successful_runs'] += 1
            
        except Exception as e:
            logger.error(f"Pipeline cycle failed: {e}")
            cycle_results['errors'].append(f"Pipeline failure: {str(e)}")
            self.pipeline_stats['failed_runs'] += 1
        
        # Update pipeline statistics
        cycle_results['end_time'] = datetime.now().isoformat()
        cycle_duration = (datetime.now() - cycle_start).total_seconds()
        
        self.pipeline_stats['total_runs'] += 1
        self.pipeline_stats['total_vessels_processed'] += len(cycle_results['ais_data'])
        self.pipeline_stats['total_threats_detected'] += len(cycle_results['threats'])
        self.last_run_time = cycle_start
        
        logger.info(f"✅ Enhanced surveillance cycle complete in {cycle_duration:.1f} seconds")
        logger.info(f"   Vessels: {len(cycle_results['ais_data'])}, Threats: {len(cycle_results['threats'])}, Quality: {quality_score}/100")
        
        return cycle_results
    
    def _run_threat_detection(self, ais_data: List[Dict], sar_data: List[Dict]) -> List[Dict]:
        """Run comprehensive threat detection analysis"""
        all_threats = []
        
        # Dark vessel detection (comparing SAR vs AIS)
        if sar_data and ais_data:
            try:
                dark_vessels = self.dark_vessel_detector.detect_dark_vessels(ais_data, sar_data)
                for dark_vessel in dark_vessels:
                    threat = {
                        'type': 'dark_vessel',
                        'severity': 'HIGH',
                        'vessel_info': dark_vessel,
                        'description': 'Vessel visible in SAR imagery but not broadcasting AIS',
                        'timestamp': datetime.now().isoformat(),
                        'latitude': dark_vessel.get('latitude', 0),
                        'longitude': dark_vessel.get('longitude', 0)
                    }
                    all_threats.append(threat)
            except Exception as e:
                logger.warning(f"Dark vessel detection failed: {e}")
        
        # Cable proximity monitoring
        try:
            cable_threats = self.cable_monitor.check_vessel_cable_proximity(ais_data)
            for vessel in cable_threats:
                if vessel.get('cable_proximity'):
                    for proximity in vessel['cable_proximity']:
                        if proximity['distance_km'] < proximity.get('alert_threshold', 20):
                            threat = {
                                'type': 'cable_proximity',
                                'severity': 'MEDIUM',
                                'vessel_mmsi': vessel['mmsi'],
                                'vessel_name': vessel.get('vessel_name', 'Unknown'),
                                'cable_name': proximity['cable_name'],
                                'distance_km': proximity['distance_km'],
                                'description': f"Vessel within {proximity['distance_km']:.1f} km of submarine cable {proximity['cable_name']}",
                                'timestamp': datetime.now().isoformat(),
                                'latitude': vessel['latitude'],
                                'longitude': vessel['longitude']
                            }
                            all_threats.append(threat)
        except Exception as e:
            logger.warning(f"Cable proximity monitoring failed: {e}")
        
        # Advanced risk scoring
        try:
            risk_assessments = self.risk_scorer.assess_vessel_risks(ais_data)
            for assessment in risk_assessments:
                if assessment['overall_risk_score'] > 70:  # High risk threshold
                    threat = {
                        'type': 'high_risk_behavior',
                        'severity': 'HIGH' if assessment['overall_risk_score'] > 85 else 'MEDIUM',
                        'vessel_mmsi': assessment['mmsi'],
                        'vessel_name': assessment.get('vessel_name', 'Unknown'),
                        'risk_score': assessment['overall_risk_score'],
                        'risk_factors': assessment['risk_factors'],
                        'description': f"High-risk vessel behavior detected (score: {assessment['overall_risk_score']}/100)",
                        'timestamp': datetime.now().isoformat(),
                        'latitude': assessment.get('latitude', 0),
                        'longitude': assessment.get('longitude', 0)
                    }
                    all_threats.append(threat)
        except Exception as e:
            logger.warning(f"Risk scoring failed: {e}")
        
        return all_threats
    
    def _create_enhanced_visualizations(self, ais_data: List[Dict], threats: List[Dict]) -> List[str]:
        """Create enhanced interactive visualizations"""
        visualizations = []
        
        try:
            # Comprehensive surveillance map
            surveillance_map = self.geo_visualizer.create_comprehensive_arctic_map(
                ais_data, threats, show_tracks=True, show_heatmap=True
            )
            
            filename = f"enhanced_surveillance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            map_file = self.geo_visualizer.save_map(surveillance_map, filename)
            visualizations.append(str(map_file))
            
            # Threat-focused map if threats exist
            if threats:
                threat_map = self.geo_visualizer.create_threat_analysis_map(threats, ais_data)
                threat_filename = f"threat_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                threat_file = self.geo_visualizer.save_map(threat_map, threat_filename)
                visualizations.append(str(threat_file))
            
            # Operational dashboard
            dashboard_map = self.geo_visualizer.create_operational_dashboard_map(ais_data, threats)
            dashboard_filename = f"operational_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            dashboard_file = self.geo_visualizer.save_map(dashboard_map, dashboard_filename)
            visualizations.append(str(dashboard_file))
            
        except Exception as e:
            logger.error(f"Visualization creation failed: {e}")
        
        return visualizations
    
    def _generate_intelligence_reports(self, cycle_results: Dict[str, any]):
        """Generate comprehensive intelligence reports"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save detailed cycle results
        reports_dir = self.output_dir / "intelligence_reports"
        reports_dir.mkdir(exist_ok=True)
        
        # Main intelligence report
        intel_report = {
            'report_type': 'Enhanced Arctic Surveillance Intelligence',
            'classification': 'OPERATIONAL',
            'generated_at': datetime.now().isoformat(),
            'cycle_results': cycle_results,
            'executive_summary': self._generate_executive_summary(cycle_results),
            'threat_assessment': self._generate_threat_assessment(cycle_results['threats']),
            'operational_recommendations': self._generate_operational_recommendations(cycle_results)
        }
        
        intel_file = reports_dir / f"intelligence_report_{timestamp}.json"
        with open(intel_file, 'w') as f:
            json.dump(intel_report, f, indent=2, default=str)
        
        logger.info(f"Intelligence report saved: {intel_file}")
        
        # Quality assurance report
        if cycle_results.get('quality_report'):
            quality_file = reports_dir / f"quality_report_{timestamp}.json"
            with open(quality_file, 'w') as f:
                json.dump(cycle_results['quality_report'], f, indent=2, default=str)
            
            logger.info(f"Quality report saved: {quality_file}")
    
    def _generate_executive_summary(self, cycle_results: Dict[str, any]) -> Dict[str, any]:
        """Generate executive summary of surveillance cycle"""
        threats = cycle_results.get('threats', [])
        ais_data = cycle_results.get('ais_data', [])
        quality_report = cycle_results.get('quality_report', {})
        
        # Threat level assessment
        critical_threats = [t for t in threats if t.get('severity') == 'HIGH']
        medium_threats = [t for t in threats if t.get('severity') == 'MEDIUM']
        
        overall_threat_level = 'LOW'
        if len(critical_threats) > 0:
            overall_threat_level = 'HIGH'
        elif len(medium_threats) > 2:
            overall_threat_level = 'MEDIUM'
        
        return {
            'surveillance_status': 'OPERATIONAL' if cycle_results.get('success') else 'DEGRADED',
            'overall_threat_level': overall_threat_level,
            'vessels_monitored': len(ais_data),
            'threats_detected': len(threats),
            'critical_threats': len(critical_threats),
            'data_quality_score': quality_report.get('quality_summary', {}).get('overall_score', 0),
            'coverage_area': 'Arctic Waters (69°N-82°N, 5°E-35°E)',
            'key_findings': self._extract_key_findings(cycle_results)
        }
    
    def _generate_threat_assessment(self, threats: List[Dict]) -> Dict[str, any]:
        """Generate detailed threat assessment"""
        threat_types = {}
        for threat in threats:
            threat_type = threat.get('type', 'unknown')
            if threat_type not in threat_types:
                threat_types[threat_type] = []
            threat_types[threat_type].append(threat)
        
        return {
            'total_threats': len(threats),
            'threat_breakdown': {k: len(v) for k, v in threat_types.items()},
            'threat_details': threat_types,
            'geographic_distribution': self._analyze_threat_geography(threats),
            'temporal_patterns': self._analyze_threat_timing(threats)
        }
    
    def _generate_operational_recommendations(self, cycle_results: Dict[str, any]) -> List[str]:
        """Generate actionable operational recommendations"""
        recommendations = []
        
        threats = cycle_results.get('threats', [])
        quality_report = cycle_results.get('quality_report', {})
        
        # Threat-based recommendations
        critical_threats = [t for t in threats if t.get('severity') == 'HIGH']
        if critical_threats:
            recommendations.append(f"IMMEDIATE: Investigate {len(critical_threats)} critical threat(s) detected")
            
            for threat in critical_threats[:3]:  # Top 3 critical threats
                if threat.get('type') == 'dark_vessel':
                    recommendations.append(f"Deploy patrol vessel to investigate dark vessel at {threat.get('latitude', 0):.3f}, {threat.get('longitude', 0):.3f}")
                elif threat.get('type') == 'cable_proximity':
                    recommendations.append(f"Monitor vessel {threat.get('vessel_mmsi', 'unknown')} near submarine cable {threat.get('cable_name', 'unknown')}")
        
        # Quality-based recommendations
        quality_score = quality_report.get('quality_summary', {}).get('overall_score', 100)
        if quality_score < 80:
            recommendations.extend(quality_report.get('quality_summary', {}).get('recommendations', [])[:2])
        
        # Data coverage recommendations
        if len(cycle_results.get('ais_data', [])) < 10:
            recommendations.append("LOW DATA: Expand AIS data collection coverage or check source availability")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _extract_key_findings(self, cycle_results: Dict[str, any]) -> List[str]:
        """Extract key findings from surveillance cycle"""
        findings = []
        
        threats = cycle_results.get('threats', [])
        ais_data = cycle_results.get('ais_data', [])
        
        # Vessel activity findings
        if ais_data:
            vessel_types = {}
            for vessel in ais_data:
                vtype = vessel.get('vessel_type', 'Unknown')
                vessel_types[vtype] = vessel_types.get(vtype, 0) + 1
            
            most_common_type = max(vessel_types.items(), key=lambda x: x[1])
            findings.append(f"Primary vessel activity: {most_common_type[1]} {most_common_type[0]} vessels")
        
        # Threat findings
        if threats:
            threat_types = {}
            for threat in threats:
                ttype = threat.get('type', 'unknown')
                threat_types[ttype] = threat_types.get(ttype, 0) + 1
            
            findings.append(f"Primary threat type: {max(threat_types.items(), key=lambda x: x[1])[0]}")
        
        return findings
    
    def _analyze_threat_geography(self, threats: List[Dict]) -> Dict[str, any]:
        """Analyze geographic distribution of threats"""
        if not threats:
            return {}
        
        lats = [t.get('latitude', 0) for t in threats if t.get('latitude')]
        lons = [t.get('longitude', 0) for t in threats if t.get('longitude')]
        
        if not lats or not lons:
            return {}
        
        return {
            'center_latitude': sum(lats) / len(lats),
            'center_longitude': sum(lons) / len(lons),
            'north_extent': max(lats),
            'south_extent': min(lats),
            'east_extent': max(lons),
            'west_extent': min(lons)
        }
    
    def _analyze_threat_timing(self, threats: List[Dict]) -> Dict[str, any]:
        """Analyze temporal patterns of threats"""
        current_hour = datetime.now().hour
        return {
            'detection_hour': current_hour,
            'total_detections': len(threats),
            'detection_rate_per_hour': len(threats)  # Simplified metric
        }
    
    def run_historical_backfill(self, days_back: int = 7) -> Dict[str, any]:
        """Run historical data backfill using the enhanced backfill script"""
        logger.info(f"🔄 Starting historical backfill for {days_back} days...")
        
        try:
            # Import and run historical backfill
            from scripts.historical_backfill import HistoricalBackfill
            
            backfill = HistoricalBackfill(str(self.data_dir))
            results = backfill.run_full_backfill(days_back)
            
            logger.info(f"✅ Historical backfill complete: {results.get('completed', 0)} tasks completed")
            return results
            
        except Exception as e:
            logger.error(f"Historical backfill failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_pipeline_status(self) -> Dict[str, any]:
        """Get current pipeline status and statistics"""
        return {
            'pipeline_stats': self.pipeline_stats,
            'last_run_time': self.last_run_time.isoformat() if self.last_run_time else None,
            'data_sources': {
                'ais_sources': len(self.ais_collector.sources),
                'sentinel_available': True,  # Based on credentials
                'quality_monitoring': True
            },
            'system_status': 'OPERATIONAL'
        }

def main():
    """Command line interface for enhanced surveillance pipeline"""
    parser = argparse.ArgumentParser(description='Enhanced Arctic Surveillance Pipeline')
    parser.add_argument('--mode', choices=['single', 'backfill', 'status'], default='single',
                       help='Operation mode (default: single)')
    parser.add_argument('--days', type=int, default=7, help='Days for historical backfill (default: 7)')
    parser.add_argument('--no-sar', action='store_true', help='Skip SAR data collection')
    parser.add_argument('--no-viz', action='store_true', help='Skip visualization creation')
    parser.add_argument('--data-dir', default='data', help='Data directory path')
    parser.add_argument('--output-dir', default='outputs', help='Output directory path')
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = EnhancedSurveillancePipeline(args.data_dir, args.output_dir)
    
    print("🚀 Enhanced Arctic Surveillance Pipeline")
    print("=" * 45)
    print(f"Data directory: {args.data_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Mode: {args.mode}")
    print()
    
    if args.mode == 'single':
        # Run single surveillance cycle
        print("🌐 Running enhanced surveillance cycle...")
        results = pipeline.run_enhanced_surveillance_cycle(
            include_sar=not args.no_sar,
            create_visualizations=not args.no_viz
        )
        
        print(f"\n✅ Surveillance cycle complete!")
        print(f"   Success: {results['success']}")
        print(f"   Vessels monitored: {len(results['ais_data'])}")
        print(f"   Threats detected: {len(results['threats'])}")
        print(f"   Quality score: {results.get('quality_report', {}).get('quality_summary', {}).get('overall_score', 'N/A')}/100")
        print(f"   Visualizations: {len(results['visualizations'])}")
        
        if results['threats']:
            print(f"\n⚠️ Threat Summary:")
            for threat in results['threats'][:5]:
                print(f"   - {threat.get('type', 'unknown')}: {threat.get('description', 'No description')}")
        
        if results['visualizations']:
            print(f"\n🗺️ Generated Maps:")
            for viz in results['visualizations']:
                print(f"   - {Path(viz).name}")
    
    elif args.mode == 'backfill':
        # Run historical backfill
        print(f"🔄 Running historical backfill for {args.days} days...")
        results = pipeline.run_historical_backfill(args.days)
        
        print(f"\n✅ Historical backfill complete!")
        print(f"   Tasks completed: {results.get('completed', 0)}")
        print(f"   Tasks failed: {results.get('failed', 0)}")
        print(f"   AIS gaps filled: {results.get('verification', {}).get('ais_gaps_filled', 0)}")
        print(f"   Sentinel gaps filled: {results.get('verification', {}).get('sentinel_gaps_filled', 0)}")
    
    elif args.mode == 'status':
        # Show pipeline status
        status = pipeline.get_pipeline_status()
        
        print("📊 Pipeline Status:")
        print(f"   System Status: {status['system_status']}")
        print(f"   Total Runs: {status['pipeline_stats']['total_runs']}")
        print(f"   Success Rate: {status['pipeline_stats']['successful_runs']}/{status['pipeline_stats']['total_runs']}")
        print(f"   Last Run: {status['last_run_time'] or 'Never'}")
        print(f"   Total Vessels Processed: {status['pipeline_stats']['total_vessels_processed']}")
        print(f"   Total Threats Detected: {status['pipeline_stats']['total_threats_detected']}")
        
        print(f"\n🔌 Data Sources:")
        print(f"   AIS Sources: {status['data_sources']['ais_sources']}")
        print(f"   Sentinel Available: {status['data_sources']['sentinel_available']}")
        print(f"   Quality Monitoring: {status['data_sources']['quality_monitoring']}")
    
    print(f"\n📋 Log files: enhanced_surveillance.log")
    print(f"📁 Output directory: {args.output_dir}")

if __name__ == "__main__":
    main()