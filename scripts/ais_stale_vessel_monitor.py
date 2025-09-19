#!/usr/bin/env python3
"""
AIS Stale Vessel Monitor Script
Real-time monitoring for vessels with stale or turned-off AIS transponders

This script provides continuous monitoring of vessel AIS health and generates
alerts for vessels that stop updating their positions or broadcast stale data.

Usage:
    python scripts/ais_stale_vessel_monitor.py
    python scripts/ais_stale_vessel_monitor.py --priority-only
    python scripts/ais_stale_vessel_monitor.py --export-alerts

Author: Claude Code (Arctic Intelligence)
Date: 2025-09-19
"""

import csv
import json
import argparse
from datetime import datetime, timedelta
from collections import defaultdict
import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from arctic_tracker.analysis.ais_anomaly_detector import AISAnomalyDetector

class AISStaleVesselMonitor:
    """Real-time monitor for stale vessel transponders"""
    
    def __init__(self):
        self.detector = AISAnomalyDetector()
        self.priority_countries = ['Russia', 'China']
        
    def run_monitoring_cycle(self):
        """Run a single monitoring cycle"""
        print("🛰️  Arctic Shadow Tracker - AIS Stale Vessel Monitor")
        print("=" * 60)
        print(f"Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print()
        
        # Paths to data files
        csv_file = "arctic_intelligence/vessel_positions.csv"
        history_file = "arctic_intelligence/vessel_history.json"
        
        if not os.path.exists(csv_file) or not os.path.exists(history_file):
            print("❌ Error: Data files not found. Ensure the Arctic Shadow Tracker is running.")
            return False
        
        # Run analysis
        results = self.detector.analyze_vessel_positions(csv_file, history_file)
        
        # Display results
        self._display_monitoring_results(results)
        
        return True
    
    def _display_monitoring_results(self, results):
        """Display monitoring results in a formatted way"""
        
        # Summary statistics
        summary = results.get('summary', {})
        stats = results.get('statistics', {})
        
        print("📊 FLEET STATUS OVERVIEW")
        print("-" * 30)
        print(f"Total Vessels Tracked: {summary.get('total_vessels_analyzed', 0)}")
        print(f"Vessels with Anomalies: {summary.get('total_anomalies', 0)}")
        print(f"Critical Issues: {summary.get('critical_anomalies', 0)}")
        print(f"High Priority Issues: {summary.get('high_priority_anomalies', 0)}")
        print(f"Priority Vessel Anomalies: {summary.get('priority_vessel_anomalies', 0)}")
        print()
        
        print(f"Static Position Vessels: {stats.get('static_vessels', 0)} ({stats.get('static_percentage', 0):.1f}%)")
        print(f"Stale Transponders: {stats.get('stale_vessels', 0)} ({stats.get('stale_percentage', 0):.1f}%)")
        print(f"Priority Vessels Monitored: {stats.get('priority_vessels', 0)}")
        print()
        
        # Critical alerts
        alerts = results.get('alerts', [])
        critical_alerts = [a for a in alerts if a['level'] == 'CRITICAL']
        high_alerts = [a for a in alerts if a['level'] == 'HIGH']
        
        if critical_alerts:
            print("🚨 CRITICAL ALERTS")
            print("-" * 20)
            for i, alert in enumerate(critical_alerts, 1):
                self._print_alert(i, alert)
            print()
        
        if high_alerts:
            print("⚠️  HIGH PRIORITY ALERTS")
            print("-" * 25)
            for i, alert in enumerate(high_alerts[:10], 1):  # Show top 10
                self._print_alert(i, alert)
            print()
        
        # Stale vessel summary
        self._display_stale_vessel_summary(results)
        
        # Priority vessel status
        self._display_priority_vessel_status(results)
    
    def _print_alert(self, index, alert):
        """Print a formatted alert"""
        vessel = alert.get('vessel', 'Unknown')
        country = alert.get('country', 'Unknown')
        message = alert.get('message', 'No message')
        coords = alert.get('coordinates', [0, 0])
        
        print(f"{index:2d}. {vessel} ({country})")
        print(f"    {message}")
        print(f"    Position: {coords[0]:.4f}°N, {coords[1]:.4f}°E")
        print()
    
    def _display_stale_vessel_summary(self, results):
        """Display summary of stale vessels"""
        vessel_metrics = results.get('vessel_metrics', {})
        
        # Find vessels with stale data
        stale_vessels = []
        for mmsi, metrics in vessel_metrics.items():
            if metrics.get('is_stale') or metrics.get('is_static'):
                stale_vessels.append({
                    'mmsi': mmsi,
                    'name': metrics.get('name', 'Unknown'),
                    'country': metrics.get('country', 'Unknown'),
                    'hours_stale': metrics.get('hours_since_last_update', 0),
                    'stale_percentage': metrics.get('stale_percentage', 0),
                    'is_priority': metrics.get('priority_vessel', False),
                    'risk_level': metrics.get('risk_level', 'UNKNOWN')
                })
        
        # Sort by priority and staleness
        stale_vessels.sort(key=lambda x: (
            0 if x['is_priority'] else 1,
            -x['hours_stale']
        ))
        
        if stale_vessels:
            print("📡 STALE TRANSPONDER SUMMARY")
            print("-" * 35)
            print(f"{'Vessel':<20} {'Country':<10} {'Hours Stale':<12} {'Risk':<8} {'Priority'}")
            print("-" * 70)
            
            for vessel in stale_vessels[:15]:  # Show top 15
                name = vessel['name'][:18] if len(vessel['name']) > 18 else vessel['name']
                country = vessel['country'][:8] if len(vessel['country']) > 8 else vessel['country']
                hours = f"{vessel['hours_stale']:.1f}h"
                risk = vessel['risk_level']
                priority = "🚨" if vessel['is_priority'] else ""
                
                print(f"{name:<20} {country:<10} {hours:<12} {risk:<8} {priority}")
            
            print()
    
    def _display_priority_vessel_status(self, results):
        """Display status of priority vessels (Russian and Chinese)"""
        vessel_metrics = results.get('vessel_metrics', {})
        
        priority_vessels = []
        for mmsi, metrics in vessel_metrics.items():
            if metrics.get('priority_vessel'):
                priority_vessels.append({
                    'mmsi': mmsi,
                    'name': metrics.get('name', 'Unknown'),
                    'country': metrics.get('country', 'Unknown'),
                    'total_positions': metrics.get('total_positions', 0),
                    'unique_positions': metrics.get('unique_positions', 0),
                    'hours_since_update': metrics.get('hours_since_last_update', 0),
                    'risk_level': metrics.get('risk_level', 'UNKNOWN'),
                    'is_static': metrics.get('is_static', False),
                    'is_stale': metrics.get('is_stale', False)
                })
        
        if priority_vessels:
            print("🎯 PRIORITY VESSEL STATUS (Russian & Chinese)")
            print("-" * 50)
            
            # Group by country
            by_country = defaultdict(list)
            for vessel in priority_vessels:
                by_country[vessel['country']].append(vessel)
            
            for country, vessels in by_country.items():
                print(f"\n{country.upper()} VESSELS ({len(vessels)}):")
                vessels.sort(key=lambda x: (
                    0 if x['risk_level'] == 'CRITICAL' else 1,
                    -x['hours_since_update']
                ))
                
                for vessel in vessels:
                    status = "🔴" if vessel['risk_level'] == 'CRITICAL' else "🟡" if vessel['risk_level'] == 'HIGH' else "🟢"
                    static_flag = " [STATIC]" if vessel['is_static'] else ""
                    stale_flag = " [STALE]" if vessel['is_stale'] else ""
                    
                    print(f"  {status} {vessel['name']} ({vessel['mmsi']})")
                    print(f"     Last update: {vessel['hours_since_update']:.1f}h ago{static_flag}{stale_flag}")
                    print(f"     Positions: {vessel['unique_positions']}/{vessel['total_positions']} unique")
    
    def export_alerts_to_file(self, results, filename="arctic_intelligence/ais_monitoring_alerts.json"):
        """Export current alerts to a file"""
        alerts = results.get('alerts', [])
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_alerts': len(alerts),
            'critical_alerts': len([a for a in alerts if a['level'] == 'CRITICAL']),
            'high_alerts': len([a for a in alerts if a['level'] == 'HIGH']),
            'alerts': alerts,
            'summary': results.get('summary', {}),
            'statistics': results.get('statistics', {})
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"✅ Alerts exported to: {filename}")
        
    def monitor_priority_only(self):
        """Monitor only priority vessels (Russian and Chinese)"""
        print("🎯 PRIORITY VESSEL MONITORING MODE")
        print("=" * 40)
        
        csv_file = "arctic_intelligence/vessel_positions.csv"
        history_file = "arctic_intelligence/vessel_history.json"
        
        results = self.detector.analyze_vessel_positions(csv_file, history_file)
        
        # Filter for priority vessels only
        vessel_metrics = results.get('vessel_metrics', {})
        priority_metrics = {k: v for k, v in vessel_metrics.items() if v.get('priority_vessel')}
        
        if not priority_metrics:
            print("No priority vessels currently tracked.")
            return
        
        print(f"Monitoring {len(priority_metrics)} priority vessels")
        print()
        
        # Show only priority vessel alerts
        alerts = results.get('alerts', [])
        priority_alerts = [a for a in alerts if a.get('country') in self.priority_countries]
        
        if priority_alerts:
            print("🚨 PRIORITY VESSEL ALERTS")
            print("-" * 30)
            for i, alert in enumerate(priority_alerts, 1):
                self._print_alert(i, alert)
        else:
            print("✅ No critical alerts for priority vessels at this time.")


def main():
    parser = argparse.ArgumentParser(description='Monitor AIS transponder health for stale vessels')
    parser.add_argument('--priority-only', action='store_true', 
                        help='Monitor only priority vessels (Russian and Chinese)')
    parser.add_argument('--export-alerts', action='store_true',
                        help='Export alerts to JSON file')
    parser.add_argument('--continuous', action='store_true',
                        help='Run continuous monitoring (every 5 minutes)')
    
    args = parser.parse_args()
    
    monitor = AISStaleVesselMonitor()
    
    try:
        if args.priority_only:
            monitor.monitor_priority_only()
        elif args.continuous:
            print("Starting continuous monitoring mode...")
            while True:
                monitor.run_monitoring_cycle()
                if args.export_alerts:
                    csv_file = "arctic_intelligence/vessel_positions.csv"
                    history_file = "arctic_intelligence/vessel_history.json"
                    results = monitor.detector.analyze_vessel_positions(csv_file, history_file)
                    monitor.export_alerts_to_file(results)
                
                print("Sleeping for 5 minutes...")
                import time
                time.sleep(300)  # 5 minutes
        else:
            success = monitor.run_monitoring_cycle()
            if success and args.export_alerts:
                csv_file = "arctic_intelligence/vessel_positions.csv"
                history_file = "arctic_intelligence/vessel_history.json"
                results = monitor.detector.analyze_vessel_positions(csv_file, history_file)
                monitor.export_alerts_to_file(results)
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
    except Exception as e:
        print(f"Error during monitoring: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()