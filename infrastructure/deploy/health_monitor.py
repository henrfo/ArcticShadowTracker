#!/usr/bin/env python3
"""
Arctic Shadow Tracker - System Health Monitor
Comprehensive health monitoring with metrics collection and alerting.
"""

import sys
import os
import time
import json
import psutil
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class HealthMonitor:
    """Comprehensive system health monitoring for Arctic Shadow Tracker."""
    
    def __init__(self):
        """Initialize health monitor."""
        self.data_dir = project_root / 'data'
        self.logs_dir = project_root / 'logs'
        self.outputs_dir = project_root / 'outputs'
        
        # Health check configuration
        self.thresholds = {
            'memory_usage_percent': 80,
            'disk_usage_percent': 85,
            'cpu_usage_percent': 85,
            'data_staleness_hours': 6,
            'ais_staleness_minutes': 30,
            'log_file_size_mb': 100
        }
        
        self.status = {
            'overall': 'UNKNOWN',
            'components': {},
            'metrics': {},
            'last_check': None,
            'alerts': []
        }
    
    def check_system_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive system health check.
        
        Returns:
            Dictionary with complete health status
        """
        logger.info("Starting system health check")
        self.status['last_check'] = datetime.now().isoformat()
        self.status['alerts'] = []
        
        # Check all components
        checks = [
            ('system_resources', self._check_system_resources),
            ('data_availability', self._check_data_availability),
            ('data_freshness', self._check_data_freshness),
            ('log_health', self._check_log_health),
            ('api_endpoints', self._check_api_endpoints),
            ('storage_capacity', self._check_storage_capacity),
            ('process_status', self._check_process_status)
        ]
        
        all_healthy = True
        
        for component_name, check_func in checks:
            try:
                component_status = check_func()
                self.status['components'][component_name] = component_status
                
                if component_status['status'] not in ['HEALTHY', 'WARNING']:
                    all_healthy = False
                    
                if component_status.get('alerts'):
                    self.status['alerts'].extend(component_status['alerts'])
                    
            except Exception as e:
                logger.error(f"Health check failed for {component_name}: {e}")
                self.status['components'][component_name] = {
                    'status': 'ERROR',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                all_healthy = False
        
        # Determine overall status
        if all_healthy:
            self.status['overall'] = 'HEALTHY'
        elif any(comp.get('status') == 'CRITICAL' for comp in self.status['components'].values()):
            self.status['overall'] = 'CRITICAL'
        else:
            self.status['overall'] = 'WARNING'
        
        logger.info(f"Health check complete: {self.status['overall']}")
        return self.status
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource utilization."""
        try:
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # CPU usage (5-second average)
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Disk usage for app directory
            if os.path.exists('/app'):
                disk_usage = psutil.disk_usage('/app')
                disk_percent = (disk_usage.used / disk_usage.total) * 100
            else:
                disk_usage = psutil.disk_usage(str(project_root))
                disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Load average
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
            
            # Determine status
            alerts = []
            status = 'HEALTHY'
            
            if memory_percent > self.thresholds['memory_usage_percent']:
                status = 'WARNING' if memory_percent < 90 else 'CRITICAL'
                alerts.append(f"High memory usage: {memory_percent:.1f}%")
            
            if cpu_percent > self.thresholds['cpu_usage_percent']:
                status = 'WARNING' if cpu_percent < 95 else 'CRITICAL'
                alerts.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if disk_percent > self.thresholds['disk_usage_percent']:
                status = 'WARNING' if disk_percent < 95 else 'CRITICAL'
                alerts.append(f"High disk usage: {disk_percent:.1f}%")
            
            self.status['metrics'].update({
                'memory_usage_percent': memory_percent,
                'cpu_usage_percent': cpu_percent,
                'disk_usage_percent': disk_percent,
                'load_average_1min': load_avg[0],
                'load_average_5min': load_avg[1],
                'load_average_15min': load_avg[2]
            })
            
            return {
                'status': status,
                'message': f"Memory: {memory_percent:.1f}%, CPU: {cpu_percent:.1f}%, Disk: {disk_percent:.1f}%",
                'metrics': {
                    'memory_percent': memory_percent,
                    'cpu_percent': cpu_percent,
                    'disk_percent': disk_percent,
                    'load_average': load_avg
                },
                'alerts': alerts,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {
                'status': 'ERROR',
                'message': f"Failed to check system resources: {e}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _check_data_availability(self) -> Dict[str, Any]:
        """Check availability of required data directories and files."""
        try:
            required_dirs = [
                self.data_dir / 'ais',
                self.data_dir / 'satellite',
                self.data_dir / 'operational' / 'daily',
                self.data_dir / 'operational' / 'latest',
                self.outputs_dir
            ]
            
            missing_dirs = []
            existing_dirs = []
            
            for dir_path in required_dirs:
                if dir_path.exists():
                    existing_dirs.append(str(dir_path))
                else:
                    missing_dirs.append(str(dir_path))
            
            # Check for recent operational data
            latest_dir = self.data_dir / 'operational' / 'latest'
            has_recent_data = False
            if latest_dir.exists():
                for file_path in latest_dir.glob('*.json'):
                    if file_path.stat().st_mtime > time.time() - 3600:  # Within last hour
                        has_recent_data = True
                        break
            
            status = 'HEALTHY'
            alerts = []
            
            if missing_dirs:
                status = 'WARNING'
                alerts.append(f"Missing directories: {', '.join(missing_dirs)}")
            
            if not has_recent_data:
                status = 'WARNING'
                alerts.append("No recent operational data found")
            
            return {
                'status': status,
                'message': f"Data directories: {len(existing_dirs)}/{len(required_dirs)} available",
                'details': {
                    'existing_dirs': existing_dirs,
                    'missing_dirs': missing_dirs,
                    'has_recent_data': has_recent_data
                },
                'alerts': alerts,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Data availability check failed: {e}")
            return {
                'status': 'ERROR',
                'message': f"Failed to check data availability: {e}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _check_data_freshness(self) -> Dict[str, Any]:
        """Check freshness of operational data."""
        try:
            current_time = datetime.now()
            alerts = []
            status = 'HEALTHY'
            freshness_info = {}
            
            # Check AIS data freshness
            ais_latest = self.data_dir / 'operational' / 'latest' / 'ais_latest.json'
            if ais_latest.exists():
                ais_age_minutes = (current_time.timestamp() - ais_latest.stat().st_mtime) / 60
                freshness_info['ais_age_minutes'] = ais_age_minutes
                
                if ais_age_minutes > self.thresholds['ais_staleness_minutes']:
                    status = 'WARNING'
                    alerts.append(f"AIS data is {ais_age_minutes:.1f} minutes old")
            else:
                status = 'WARNING'
                alerts.append("No AIS data found")
            
            # Check SAR data freshness
            sar_latest = self.data_dir / 'operational' / 'latest' / 'sar_latest.json'
            if sar_latest.exists():
                sar_age_hours = (current_time.timestamp() - sar_latest.stat().st_mtime) / 3600
                freshness_info['sar_age_hours'] = sar_age_hours
                
                if sar_age_hours > self.thresholds['data_staleness_hours']:
                    status = 'WARNING'
                    alerts.append(f"SAR data is {sar_age_hours:.1f} hours old")
            else:
                status = 'WARNING'
                alerts.append("No SAR data found")
            
            # Check today's operational summary
            today_summary = self.data_dir / 'operational' / 'latest' / 'summary_latest.json'
            if today_summary.exists():
                summary_age_hours = (current_time.timestamp() - today_summary.stat().st_mtime) / 3600
                freshness_info['summary_age_hours'] = summary_age_hours
                
                if summary_age_hours > 24:
                    status = 'WARNING'
                    alerts.append(f"Daily summary is {summary_age_hours:.1f} hours old")
            
            self.status['metrics'].update(freshness_info)
            
            return {
                'status': status,
                'message': f"Data freshness check: {len(alerts)} issues found",
                'details': freshness_info,
                'alerts': alerts,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Data freshness check failed: {e}")
            return {
                'status': 'ERROR',
                'message': f"Failed to check data freshness: {e}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _check_log_health(self) -> Dict[str, Any]:
        """Check log file health and recent error patterns."""
        try:
            alerts = []
            status = 'HEALTHY'
            log_info = {}
            
            # Check log directory
            if not self.logs_dir.exists():
                return {
                    'status': 'WARNING',
                    'message': "Log directory does not exist",
                    'timestamp': datetime.now().isoformat()
                }
            
            # Check recent log files
            recent_logs = []
            error_count = 0
            
            for log_file in self.logs_dir.glob('*.log'):
                file_size_mb = log_file.stat().st_size / (1024 * 1024)
                file_age_hours = (time.time() - log_file.stat().st_mtime) / 3600
                
                if file_age_hours < 24:  # Check logs from last 24 hours
                    recent_logs.append({
                        'file': log_file.name,
                        'size_mb': round(file_size_mb, 2),
                        'age_hours': round(file_age_hours, 1)
                    })
                
                # Check for oversized log files
                if file_size_mb > self.thresholds['log_file_size_mb']:
                    alerts.append(f"Large log file: {log_file.name} ({file_size_mb:.1f}MB)")
                    status = 'WARNING'
                
                # Quick error check in recent logs
                if file_age_hours < 1:  # Only recent logs
                    try:
                        with open(log_file, 'r') as f:
                            # Check last 100 lines for errors
                            lines = f.readlines()[-100:]
                            for line in lines:
                                if 'ERROR' in line.upper() or 'CRITICAL' in line.upper():
                                    error_count += 1
                    except Exception:
                        pass  # Ignore read errors
            
            log_info = {
                'recent_logs': recent_logs,
                'recent_error_count': error_count
            }
            
            if error_count > 10:
                status = 'WARNING'
                alerts.append(f"High error count in recent logs: {error_count}")
            
            self.status['metrics']['recent_log_errors'] = error_count
            
            return {
                'status': status,
                'message': f"Log health: {len(recent_logs)} recent files, {error_count} errors",
                'details': log_info,
                'alerts': alerts,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Log health check failed: {e}")
            return {
                'status': 'ERROR',
                'message': f"Failed to check log health: {e}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _check_api_endpoints(self) -> Dict[str, Any]:
        """Check API endpoint availability."""
        try:
            endpoints_to_check = [
                'http://localhost:8000/health',
                'http://localhost:8000/metrics',
                'http://localhost:9090/metrics'  # Prometheus
            ]
            
            endpoint_status = {}
            alerts = []
            overall_status = 'HEALTHY'
            
            for endpoint in endpoints_to_check:
                try:
                    response = requests.get(endpoint, timeout=5)
                    if response.status_code == 200:
                        endpoint_status[endpoint] = 'UP'
                    else:
                        endpoint_status[endpoint] = f'DOWN ({response.status_code})'
                        alerts.append(f"Endpoint down: {endpoint}")
                        overall_status = 'WARNING'
                except requests.exceptions.RequestException as e:
                    endpoint_status[endpoint] = 'DOWN (Connection Error)'
                    # Don't alert for localhost endpoints if we're not running API
                    if 'localhost' not in endpoint:
                        alerts.append(f"Endpoint unreachable: {endpoint}")
                        overall_status = 'WARNING'
            
            return {
                'status': overall_status,
                'message': f"API endpoints: {len([v for v in endpoint_status.values() if v == 'UP'])}/{len(endpoints_to_check)} available",
                'details': endpoint_status,
                'alerts': alerts,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"API endpoint check failed: {e}")
            return {
                'status': 'ERROR',
                'message': f"Failed to check API endpoints: {e}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _check_storage_capacity(self) -> Dict[str, Any]:
        """Check storage capacity and growth trends."""
        try:
            storage_info = {}
            alerts = []
            status = 'HEALTHY'
            
            # Check main data directory sizes
            directories_to_check = [
                ('data_total', self.data_dir),
                ('logs_total', self.logs_dir),
                ('outputs_total', self.outputs_dir)
            ]
            
            for name, dir_path in directories_to_check:
                if dir_path.exists():
                    total_size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                    size_mb = total_size / (1024 * 1024)
                    storage_info[name + '_mb'] = round(size_mb, 2)
                    
                    # Alert on large directories
                    if size_mb > 1000:  # 1GB
                        alerts.append(f"Large directory: {name} ({size_mb:.1f}MB)")
                        status = 'WARNING'
                else:
                    storage_info[name + '_mb'] = 0
            
            # Check for rapid growth in daily data
            daily_dir = self.data_dir / 'operational' / 'daily'
            if daily_dir.exists():
                recent_dirs = [d for d in daily_dir.iterdir() if d.is_dir()]
                if len(recent_dirs) > 30:  # More than 30 days of data
                    alerts.append(f"Many daily data directories: {len(recent_dirs)}")
                    status = 'WARNING'
            
            self.status['metrics'].update(storage_info)
            
            return {
                'status': status,
                'message': f"Storage check: {len(alerts)} issues found",
                'details': storage_info,
                'alerts': alerts,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Storage capacity check failed: {e}")
            return {
                'status': 'ERROR',
                'message': f"Failed to check storage capacity: {e}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _check_process_status(self) -> Dict[str, Any]:
        """Check status of key processes."""
        try:
            process_info = {}
            alerts = []
            status = 'HEALTHY'
            
            # Get current Python processes
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    if 'python' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        if 'arctic' in cmdline.lower() or 'daily_operations' in cmdline:
                            python_processes.append({
                                'pid': proc.info['pid'],
                                'command': cmdline[:100],  # Truncate long commands
                                'cpu_percent': proc.info['cpu_percent'],
                                'memory_percent': proc.info['memory_percent']
                            })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            process_info['arctic_processes'] = python_processes
            process_info['total_arctic_processes'] = len(python_processes)
            
            # Check if main processes are running
            has_main_process = any('daily_operations' in proc['command'] for proc in python_processes)
            if not has_main_process:
                alerts.append("Main Arctic Shadow Tracker process not found")
                status = 'WARNING'
            
            self.status['metrics']['active_processes'] = len(python_processes)
            
            return {
                'status': status,
                'message': f"Process check: {len(python_processes)} Arctic processes running",
                'details': process_info,
                'alerts': alerts,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Process status check failed: {e}")
            return {
                'status': 'ERROR',
                'message': f"Failed to check process status: {e}",
                'timestamp': datetime.now().isoformat()
            }
    
    def save_health_report(self) -> str:
        """Save health report to file."""
        try:
            report_file = self.logs_dir / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(self.status, f, indent=2)
            return str(report_file)
        except Exception as e:
            logger.error(f"Failed to save health report: {e}")
            return ""
    
    def run_daemon(self, check_interval: int = 300):
        """Run health monitor as daemon with periodic checks."""
        logger.info(f"Starting health monitor daemon (check interval: {check_interval}s)")
        
        while True:
            try:
                health_status = self.check_system_health()
                
                # Save periodic health reports
                if health_status['overall'] in ['WARNING', 'CRITICAL']:
                    self.save_health_report()
                
                # Log summary
                logger.info(f"Health check complete: {health_status['overall']} "
                           f"({len(health_status['alerts'])} alerts)")
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Health monitor daemon stopped")
                break
            except Exception as e:
                logger.error(f"Health monitor daemon error: {e}")
                time.sleep(60)  # Wait before retrying


def docker_health_check():
    """Docker health check entry point."""
    try:
        monitor = HealthMonitor()
        status = monitor.check_system_health()
        
        if status['overall'] in ['HEALTHY', 'WARNING']:
            print("OK")
            return True
        else:
            print(f"FAIL: {status['overall']}")
            return False
    except Exception as e:
        print(f"FAIL: Health check error: {e}")
        return False


def check_system_health():
    """Standalone health check function for cron."""
    try:
        monitor = HealthMonitor()
        status = monitor.check_system_health()
        
        print(f"System Health: {status['overall']}")
        if status['alerts']:
            print("Alerts:")
            for alert in status['alerts']:
                print(f"  - {alert}")
        
        # Save report if there are issues
        if status['overall'] != 'HEALTHY':
            report_file = monitor.save_health_report()
            if report_file:
                print(f"Health report saved: {report_file}")
        
        return status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        print(f"Health check failed: {e}")
        return {'overall': 'ERROR', 'message': str(e)}


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Arctic Shadow Tracker Health Monitor")
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--interval', type=int, default=300, help='Check interval in seconds (daemon mode)')
    parser.add_argument('--docker', action='store_true', help='Docker health check mode')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.docker:
        success = docker_health_check()
        sys.exit(0 if success else 1)
    elif args.daemon:
        monitor = HealthMonitor()
        monitor.run_daemon(args.interval)
    else:
        check_system_health()