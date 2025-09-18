#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Prometheus Metrics Exporter
Exports operational metrics for monitoring and alerting.
"""

import sys
import os
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Prometheus client
from prometheus_client import start_http_server, Gauge, Counter, Histogram, Info
from prometheus_client.core import CollectorRegistry, REGISTRY

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class ArcticMetricsExporter:
    """Prometheus metrics exporter for Arctic Shadow Tracker."""
    
    def __init__(self, port: int = 9090):
        """Initialize metrics exporter."""
        self.port = port
        self.data_dir = project_root / 'data'
        self.logs_dir = project_root / 'logs'
        
        # Define Prometheus metrics
        self._setup_metrics()
        
        logger.info(f"Metrics exporter initialized on port {port}")
    
    def _setup_metrics(self):
        """Set up Prometheus metrics."""
        # Threat detection metrics
        self.threats_total = Counter(
            'arctic_threats_total',
            'Total number of threats detected',
            ['threat_level', 'vessel_type']
        )
        
        self.threats_critical_total = Gauge(
            'arctic_threats_critical_total',
            'Current number of critical threats'
        )
        
        self.dark_vessels_total = Counter(
            'arctic_dark_vessels_total',
            'Total number of dark vessels detected'
        )
        
        self.dark_vessels_near_cable_total = Gauge(
            'arctic_dark_vessels_near_cable_total',
            'Current number of dark vessels near cables'
        )
        
        # Data ingestion metrics
        self.ais_vessels_current = Gauge(
            'arctic_ais_vessels_current',
            'Current number of AIS vessels being tracked'
        )
        
        self.sar_detections_current = Gauge(
            'arctic_sar_detections_current',
            'Current number of SAR detections'
        )
        
        self.last_ais_update_timestamp = Gauge(
            'arctic_last_ais_update_timestamp',
            'Timestamp of last AIS data update'
        )
        
        self.last_satellite_update_timestamp = Gauge(
            'arctic_last_satellite_update_timestamp',
            'Timestamp of last satellite data update'
        )
        
        # System performance metrics
        self.data_pipeline_duration = Histogram(
            'arctic_data_pipeline_duration_seconds',
            'Time taken for data pipeline execution',
            buckets=[1, 5, 10, 30, 60, 120, 300, 600]
        )
        
        self.data_pipeline_errors_total = Counter(
            'arctic_data_pipeline_errors_total',
            'Total number of data pipeline errors',
            ['error_type']
        )
        
        # API and service metrics
        self.api_requests_total = Counter(
            'arctic_api_requests_total',
            'Total number of API requests',
            ['method', 'endpoint', 'status']
        )
        
        self.api_unauthorized_requests_total = Counter(
            'arctic_api_unauthorized_requests_total',
            'Total number of unauthorized API requests'
        )
        
        # Surveillance quality metrics
        self.surveillance_coverage_percent = Gauge(
            'arctic_surveillance_coverage_percent',
            'Percentage of Arctic region under surveillance'
        )
        
        self.data_quality_score = Gauge(
            'arctic_data_quality_score',
            'Overall data quality score (0-100)'
        )
        
        # Operational metrics
        self.daily_operations_status = Info(
            'arctic_daily_operations_status',
            'Status of daily operations'
        )
        
        self.suspicious_vessel_patterns_total = Counter(
            'arctic_suspicious_vessel_patterns_total',
            'Total number of suspicious vessel patterns detected'
        )
        
        # Infrastructure monitoring
        self.cable_proximity_alerts_total = Counter(
            'arctic_cable_proximity_alerts_total',
            'Total number of cable proximity alerts',
            ['cable_name']
        )
        
        self.system_health_score = Gauge(
            'arctic_system_health_score',
            'Overall system health score (0-100)'
        )
    
    def update_metrics_from_operational_data(self):
        """Update metrics from latest operational data."""
        try:
            # Load latest operational data
            latest_dir = self.data_dir / 'operational' / 'latest'
            
            # Update threat metrics
            self._update_threat_metrics(latest_dir)
            
            # Update data ingestion metrics
            self._update_data_metrics(latest_dir)
            
            # Update system health metrics
            self._update_system_health_metrics()
            
            # Update surveillance quality metrics
            self._update_surveillance_metrics(latest_dir)
            
            logger.debug("Metrics updated from operational data")
            
        except Exception as e:
            logger.error(f"Failed to update metrics from operational data: {e}")
            self.data_pipeline_errors_total.labels(error_type='metrics_update').inc()
    
    def _update_threat_metrics(self, latest_dir: Path):
        """Update threat-related metrics."""
        try:
            threats_file = latest_dir / 'threats_latest.json'
            
            if threats_file.exists():
                with open(threats_file, 'r') as f:
                    threats = json.load(f)
                
                # Reset current threat counters
                self.threats_critical_total.set(0)
                self.dark_vessels_near_cable_total.set(0)
                
                critical_count = 0
                dark_near_cable_count = 0
                
                for threat in threats:
                    threat_level = threat.get('threat_level', 'UNKNOWN')
                    vessel_type = threat.get('vessel_type', 'Unknown')
                    has_ais = threat.get('has_ais', True)
                    
                    # Count threats by level
                    self.threats_total.labels(
                        threat_level=threat_level,
                        vessel_type=vessel_type
                    ).inc()
                    
                    if threat_level == 'CRITICAL':
                        critical_count += 1
                    
                    # Count dark vessels
                    if not has_ais:
                        self.dark_vessels_total.inc()
                        if threat.get('near_cable', False):
                            dark_near_cable_count += 1
                    
                    # Cable proximity alerts
                    if threat.get('near_cable', False):
                        cable_name = threat.get('closest_cable', 'Unknown')
                        self.cable_proximity_alerts_total.labels(cable_name=cable_name).inc()
                
                self.threats_critical_total.set(critical_count)
                self.dark_vessels_near_cable_total.set(dark_near_cable_count)
                
        except Exception as e:
            logger.error(f"Failed to update threat metrics: {e}")
    
    def _update_data_metrics(self, latest_dir: Path):
        """Update data ingestion metrics."""
        try:
            # AIS data metrics
            ais_file = latest_dir / 'ais_latest.json'
            if ais_file.exists():
                with open(ais_file, 'r') as f:
                    ais_data = json.load(f)
                
                self.ais_vessels_current.set(len(ais_data))
                self.last_ais_update_timestamp.set(ais_file.stat().st_mtime)
            
            # SAR data metrics
            sar_file = latest_dir / 'sar_latest.json'
            if sar_file.exists():
                with open(sar_file, 'r') as f:
                    sar_data = json.load(f)
                
                self.sar_detections_current.set(len(sar_data))
                self.last_satellite_update_timestamp.set(sar_file.stat().st_mtime)
            
            # Daily operations status
            summary_file = latest_dir / 'summary_latest.json'
            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
                
                status = summary.get('status', 'UNKNOWN')
                self.daily_operations_status.info({
                    'status': status,
                    'last_update': summary.get('end_time', 'Unknown'),
                    'threats_detected': str(summary.get('data_collected', {}).get('threats', 0))
                })
                
                # Data quality assessment
                data_collected = summary.get('data_collected', {})
                ais_count = data_collected.get('ais_vessels', 0)
                sar_count = data_collected.get('sar_detections', 0)
                
                # Simple quality score based on data availability
                quality_score = min(100, (ais_count * 2 + sar_count * 10))
                self.data_quality_score.set(quality_score)
                
        except Exception as e:
            logger.error(f"Failed to update data metrics: {e}")
    
    def _update_system_health_metrics(self):
        """Update system health metrics."""
        try:
            from infrastructure.deploy.health_monitor import HealthMonitor
            
            health_monitor = HealthMonitor()
            health_status = health_monitor.check_system_health()
            
            # Convert health status to numeric score
            health_scores = {
                'HEALTHY': 100,
                'WARNING': 70,
                'CRITICAL': 30,
                'ERROR': 10,
                'UNKNOWN': 0
            }
            
            overall_status = health_status.get('overall', 'UNKNOWN')
            score = health_scores.get(overall_status, 0)
            self.system_health_score.set(score)
            
        except Exception as e:
            logger.error(f"Failed to update system health metrics: {e}")
    
    def _update_surveillance_metrics(self, latest_dir: Path):
        """Update surveillance quality metrics."""
        try:
            # Calculate coverage based on active data sources
            ais_file = latest_dir / 'ais_latest.json'
            sar_file = latest_dir / 'sar_latest.json'
            
            coverage_factors = []
            
            if ais_file.exists():
                coverage_factors.append(50)  # AIS provides 50% coverage
            
            if sar_file.exists():
                file_age_hours = (time.time() - sar_file.stat().st_mtime) / 3600
                if file_age_hours < 6:  # Recent SAR data
                    coverage_factors.append(50)  # SAR provides 50% coverage
                elif file_age_hours < 12:
                    coverage_factors.append(25)  # Degraded SAR coverage
            
            total_coverage = min(100, sum(coverage_factors))
            self.surveillance_coverage_percent.set(total_coverage)
            
        except Exception as e:
            logger.error(f"Failed to update surveillance metrics: {e}")
    
    def record_pipeline_execution(self, duration_seconds: float, status: str = 'success'):
        """Record data pipeline execution metrics."""
        self.data_pipeline_duration.observe(duration_seconds)
        
        if status != 'success':
            self.data_pipeline_errors_total.labels(error_type=status).inc()
    
    def record_api_request(self, method: str, endpoint: str, status_code: int):
        """Record API request metrics."""
        self.api_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
        
        if status_code == 401:
            self.api_unauthorized_requests_total.inc()
    
    def record_suspicious_pattern(self):
        """Record detection of suspicious vessel pattern."""
        self.suspicious_vessel_patterns_total.inc()
    
    def start_server(self):
        """Start the Prometheus metrics server."""
        try:
            start_http_server(self.port)
            logger.info(f"Metrics server started on port {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            return False
    
    def run_daemon(self, update_interval: int = 30):
        """Run metrics exporter as daemon."""
        logger.info(f"Starting metrics exporter daemon (update interval: {update_interval}s)")
        
        # Start Prometheus server
        if not self.start_server():
            return
        
        while True:
            try:
                self.update_metrics_from_operational_data()
                time.sleep(update_interval)
                
            except KeyboardInterrupt:
                logger.info("Metrics exporter daemon stopped")
                break
            except Exception as e:
                logger.error(f"Metrics exporter daemon error: {e}")
                time.sleep(60)


def collect_system_metrics():
    """Collect system metrics function for cron."""
    try:
        exporter = ArcticMetricsExporter()
        exporter.update_metrics_from_operational_data()
        
        logger.info("System metrics collected successfully")
        
    except Exception as e:
        logger.error(f"Failed to collect system metrics: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Arctic Shadow Tracker Metrics Exporter")
    parser.add_argument('--port', type=int, default=9090, help='Prometheus server port')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--interval', type=int, default=30, help='Update interval in seconds (daemon mode)')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    exporter = ArcticMetricsExporter(port=args.port)
    
    if args.daemon:
        exporter.run_daemon(args.interval)
    else:
        exporter.update_metrics_from_operational_data()
        print(f"Metrics updated. Start server with --daemon flag on port {args.port}")