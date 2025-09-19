"""
AIS Anomaly Detection Module for Arctic Shadow Tracker

This module detects various anomalies in AIS data including:
- Stale/static position transponders
- Vessels that have gone dark
- Abnormal update patterns
- Ghost vessels (in history but not current data)
- Statistical outliers in AIS behavior

Author: Claude Code (Arctic Intelligence Analysis)
Date: 2025-09-19
"""

import csv
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
import statistics

@dataclass
class VesselAISMetrics:
    """Metrics for a vessel's AIS behavior"""
    mmsi: str
    name: str
    country: str
    total_positions: int
    unique_positions: int
    first_seen: datetime
    last_seen: datetime
    duration_hours: float
    avg_update_interval_minutes: float
    stale_positions: int
    stale_percentage: float
    hours_since_last_update: float
    is_static: bool
    is_stale: bool
    is_ghost: bool
    risk_level: str
    priority_vessel: bool

@dataclass
class AISAnomaly:
    """Represents an AIS anomaly"""
    mmsi: str
    name: str
    country: str
    anomaly_type: str
    severity: str
    description: str
    evidence: Dict
    timestamp: datetime
    coordinates: Tuple[float, float]

class AISAnomalyDetector:
    """Detects anomalies in AIS data for Arctic maritime surveillance"""
    
    def __init__(self, config: Dict = None):
        """Initialize the AIS anomaly detector"""
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
        
        # Priority vessel MMSI patterns (Russian and Chinese)
        self.priority_patterns = {
            'russian': ['273'],  # Russian MMSI start with 273
            'chinese': ['412', '413', '414']  # Chinese MMSI ranges
        }
        
        # Alert thresholds
        self.thresholds = {
            'stale_hours': 1.0,      # Hours without real position update
            'critical_stale_hours': 6.0,  # Critical stale threshold
            'ghost_hours': 12.0,     # Hours to consider vessel "ghost"
            'static_positions': 3,   # Min positions to determine if static
            'min_positions': 2,      # Minimum positions for analysis
            'outlier_std_dev': 2.0   # Standard deviations for outlier detection
        }
    
    def _default_config(self) -> Dict:
        """Default configuration for the detector"""
        return {
            'enable_statistical_analysis': True,
            'enable_priority_vessel_tracking': True,
            'enable_pattern_analysis': True,
            'alert_on_stale': True,
            'alert_on_ghost': True
        }
    
    def analyze_vessel_positions(self, csv_file: str, history_file: str) -> Dict:
        """
        Analyze vessel positions for AIS anomalies
        
        Args:
            csv_file: Path to vessel positions CSV
            history_file: Path to vessel history JSON
            
        Returns:
            Dictionary containing analysis results
        """
        self.logger.info("Starting AIS anomaly analysis")
        
        # Load data
        current_vessels = self._load_current_positions(csv_file)
        historical_vessels = self._load_historical_positions(history_file)
        
        # Analyze each vessel
        vessel_metrics = {}
        anomalies = []
        
        # Analyze vessels in current data
        for mmsi, positions in current_vessels.items():
            metrics = self._analyze_vessel_metrics(mmsi, positions, is_current=True)
            vessel_metrics[mmsi] = metrics
            
            # Check for anomalies
            vessel_anomalies = self._detect_vessel_anomalies(metrics, positions)
            anomalies.extend(vessel_anomalies)
        
        # Check for ghost vessels (in history but not current)
        ghost_vessels = self._detect_ghost_vessels(historical_vessels, current_vessels)
        for ghost_mmsi in ghost_vessels:
            if ghost_mmsi in historical_vessels:
                ghost_metrics = self._analyze_vessel_metrics(
                    ghost_mmsi, 
                    historical_vessels[ghost_mmsi].get('positions', []), 
                    is_current=False
                )
                ghost_metrics.is_ghost = True
                vessel_metrics[ghost_mmsi] = ghost_metrics
                
                # Create ghost vessel anomaly
                anomaly = AISAnomaly(
                    mmsi=ghost_mmsi,
                    name=historical_vessels[ghost_mmsi].get('name', 'Unknown'),
                    country=self._get_country_from_mmsi(ghost_mmsi),
                    anomaly_type='ghost_vessel',
                    severity='HIGH',
                    description=f"Vessel disappeared from current tracking after being active",
                    evidence={'last_seen_hours_ago': ghost_metrics.hours_since_last_update},
                    timestamp=datetime.now(),
                    coordinates=(0.0, 0.0)  # Unknown current position
                )
                anomalies.append(anomaly)
        
        # Generate statistical insights
        stats = self._calculate_fleet_statistics(vessel_metrics)
        
        # Generate alerts
        alerts = self._generate_alerts(anomalies)
        
        return {
            'analysis_timestamp': datetime.now().isoformat(),
            'vessel_metrics': {mmsi: asdict(metrics) for mmsi, metrics in vessel_metrics.items()},
            'anomalies': [asdict(anomaly) for anomaly in anomalies],
            'statistics': stats,
            'alerts': alerts,
            'summary': self._generate_summary(vessel_metrics, anomalies)
        }
    
    def _load_current_positions(self, csv_file: str) -> Dict:
        """Load current vessel positions from CSV"""
        vessels = defaultdict(list)
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('mmsi'):
                        mmsi = row['mmsi']
                        vessels[mmsi].append({
                            'timestamp': row.get('timestamp', ''),
                            'latitude': float(row.get('latitude', 0)),
                            'longitude': float(row.get('longitude', 0)),
                            'speed': float(row.get('speed', 0)) if row.get('speed') else 0,
                            'course': float(row.get('course', 0)) if row.get('course') else 0,
                            'name': row.get('name', ''),
                            'country': row.get('country', '')
                        })
        except Exception as e:
            self.logger.error(f"Error loading current positions: {e}")
        
        return dict(vessels)
    
    def _load_historical_positions(self, history_file: str) -> Dict:
        """Load historical vessel positions from JSON"""
        try:
            with open(history_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading historical positions: {e}")
            return {}
    
    def _analyze_vessel_metrics(self, mmsi: str, positions: List[Dict], is_current: bool = True) -> VesselAISMetrics:
        """Analyze metrics for a single vessel"""
        if not positions:
            return self._empty_metrics(mmsi)
        
        # Parse timestamps and sort positions
        parsed_positions = []
        for pos in positions:
            try:
                if isinstance(pos, dict):
                    # Current CSV format
                    timestamp_str = pos.get('timestamp', '')
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        parsed_positions.append({
                            'timestamp': timestamp,
                            'latitude': pos.get('latitude', 0),
                            'longitude': pos.get('longitude', 0),
                            'name': pos.get('name', ''),
                            'country': pos.get('country', '')
                        })
                else:
                    # Historical JSON format
                    timestamp = datetime.fromisoformat(pos.get('timestamp', ''))
                    parsed_positions.append({
                        'timestamp': timestamp,
                        'latitude': pos.get('latitude', 0),
                        'longitude': pos.get('longitude', 0),
                        'name': '',
                        'country': ''
                    })
            except Exception as e:
                self.logger.warning(f"Error parsing position for {mmsi}: {e}")
                continue
        
        if not parsed_positions:
            return self._empty_metrics(mmsi)
        
        # Sort by timestamp
        parsed_positions.sort(key=lambda x: x['timestamp'])
        
        # Basic metrics
        total_positions = len(parsed_positions)
        first_seen = parsed_positions[0]['timestamp']
        last_seen = parsed_positions[-1]['timestamp']
        duration = last_seen - first_seen
        duration_hours = duration.total_seconds() / 3600
        
        # Get vessel info
        name = ''
        country = ''
        for pos in parsed_positions:
            if pos.get('name'):
                name = pos['name']
            if pos.get('country'):
                country = pos['country']
        
        if not country:
            country = self._get_country_from_mmsi(mmsi)
        
        # Unique positions (check for static coordinates)
        unique_coords = set()
        for pos in parsed_positions:
            coord = (round(pos['latitude'], 4), round(pos['longitude'], 4))
            unique_coords.add(coord)
        
        unique_positions = len(unique_coords)
        is_static = unique_positions == 1 and total_positions >= self.thresholds['static_positions']
        
        # Calculate stale positions (identical coordinates in sequence)
        stale_positions = 0
        if total_positions > 1:
            for i in range(1, len(parsed_positions)):
                curr_pos = parsed_positions[i]
                prev_pos = parsed_positions[i-1]
                if (curr_pos['latitude'] == prev_pos['latitude'] and 
                    curr_pos['longitude'] == prev_pos['longitude']):
                    stale_positions += 1
        
        stale_percentage = (stale_positions / total_positions * 100) if total_positions > 0 else 0
        
        # Time since last update
        now = datetime.now()
        hours_since_last_update = (now - last_seen).total_seconds() / 3600
        
        # Average update interval
        avg_update_interval_minutes = 0
        if total_positions > 1:
            total_interval = duration.total_seconds() / 60  # minutes
            avg_update_interval_minutes = total_interval / (total_positions - 1)
        
        # Determine if stale or ghost
        is_stale = (hours_since_last_update > self.thresholds['stale_hours'] or 
                   stale_percentage > 80)
        is_ghost = hours_since_last_update > self.thresholds['ghost_hours'] and not is_current
        
        # Priority vessel check
        priority_vessel = self._is_priority_vessel(mmsi)
        
        # Risk level assessment
        risk_level = self._assess_risk_level(
            is_static, is_stale, is_ghost, priority_vessel, 
            hours_since_last_update, stale_percentage
        )
        
        return VesselAISMetrics(
            mmsi=mmsi,
            name=name,
            country=country,
            total_positions=total_positions,
            unique_positions=unique_positions,
            first_seen=first_seen,
            last_seen=last_seen,
            duration_hours=duration_hours,
            avg_update_interval_minutes=avg_update_interval_minutes,
            stale_positions=stale_positions,
            stale_percentage=stale_percentage,
            hours_since_last_update=hours_since_last_update,
            is_static=is_static,
            is_stale=is_stale,
            is_ghost=is_ghost,
            risk_level=risk_level,
            priority_vessel=priority_vessel
        )
    
    def _empty_metrics(self, mmsi: str) -> VesselAISMetrics:
        """Return empty metrics for vessels with no data"""
        return VesselAISMetrics(
            mmsi=mmsi,
            name='',
            country=self._get_country_from_mmsi(mmsi),
            total_positions=0,
            unique_positions=0,
            first_seen=datetime.now(),
            last_seen=datetime.now(),
            duration_hours=0,
            avg_update_interval_minutes=0,
            stale_positions=0,
            stale_percentage=0,
            hours_since_last_update=999,
            is_static=False,
            is_stale=True,
            is_ghost=True,
            risk_level='UNKNOWN',
            priority_vessel=self._is_priority_vessel(mmsi)
        )
    
    def _detect_vessel_anomalies(self, metrics: VesselAISMetrics, positions: List[Dict]) -> List[AISAnomaly]:
        """Detect anomalies for a specific vessel"""
        anomalies = []
        
        # Static position anomaly
        if metrics.is_static and metrics.total_positions >= 3:
            anomaly = AISAnomaly(
                mmsi=metrics.mmsi,
                name=metrics.name,
                country=metrics.country,
                anomaly_type='static_position',
                severity='HIGH' if metrics.priority_vessel else 'MEDIUM',
                description=f"Vessel broadcasting identical coordinates across {metrics.total_positions} position reports",
                evidence={
                    'total_positions': metrics.total_positions,
                    'unique_positions': metrics.unique_positions,
                    'duration_hours': metrics.duration_hours,
                    'stale_percentage': metrics.stale_percentage
                },
                timestamp=datetime.now(),
                coordinates=(positions[0]['latitude'], positions[0]['longitude']) if positions else (0, 0)
            )
            anomalies.append(anomaly)
        
        # Stale transponder anomaly
        if metrics.is_stale and not metrics.is_static:
            severity = 'CRITICAL' if metrics.hours_since_last_update > self.thresholds['critical_stale_hours'] else 'HIGH'
            if metrics.priority_vessel:
                severity = 'CRITICAL'
            
            anomaly = AISAnomaly(
                mmsi=metrics.mmsi,
                name=metrics.name,
                country=metrics.country,
                anomaly_type='stale_transponder',
                severity=severity,
                description=f"AIS transponder not updating position for {metrics.hours_since_last_update:.1f} hours",
                evidence={
                    'hours_since_update': metrics.hours_since_last_update,
                    'stale_percentage': metrics.stale_percentage,
                    'last_seen': metrics.last_seen.isoformat()
                },
                timestamp=datetime.now(),
                coordinates=(positions[-1]['latitude'], positions[-1]['longitude']) if positions else (0, 0)
            )
            anomalies.append(anomaly)
        
        # High frequency updates (potential spoofing)
        if metrics.avg_update_interval_minutes < 0.5 and metrics.total_positions > 10:
            anomaly = AISAnomaly(
                mmsi=metrics.mmsi,
                name=metrics.name,
                country=metrics.country,
                anomaly_type='high_frequency_updates',
                severity='MEDIUM',
                description=f"Unusually high update frequency: {metrics.avg_update_interval_minutes:.1f} minutes average",
                evidence={
                    'avg_interval_minutes': metrics.avg_update_interval_minutes,
                    'total_positions': metrics.total_positions,
                    'duration_hours': metrics.duration_hours
                },
                timestamp=datetime.now(),
                coordinates=(positions[-1]['latitude'], positions[-1]['longitude']) if positions else (0, 0)
            )
            anomalies.append(anomaly)
        
        return anomalies
    
    def _detect_ghost_vessels(self, historical: Dict, current: Dict) -> Set[str]:
        """Detect vessels that were active historically but are now missing"""
        ghost_vessels = set()
        
        # Check for vessels in historical data that are not in current data
        for mmsi in historical.keys():
            if mmsi not in current:
                # Check if vessel was recently active
                vessel_data = historical[mmsi]
                if 'positions' in vessel_data and vessel_data['positions']:
                    last_pos = vessel_data['positions'][-1]
                    try:
                        last_seen = datetime.fromisoformat(last_pos.get('timestamp', ''))
                        hours_since = (datetime.now() - last_seen).total_seconds() / 3600
                        
                        # Only consider as ghost if recently active but now missing
                        if hours_since < 48:  # Last seen within 48 hours
                            ghost_vessels.add(mmsi)
                    except Exception:
                        continue
        
        return ghost_vessels
    
    def _calculate_fleet_statistics(self, vessel_metrics: Dict[str, VesselAISMetrics]) -> Dict:
        """Calculate overall fleet statistics"""
        if not vessel_metrics:
            return {}
        
        metrics_list = list(vessel_metrics.values())
        
        # Basic counts
        total_vessels = len(metrics_list)
        static_vessels = sum(1 for m in metrics_list if m.is_static)
        stale_vessels = sum(1 for m in metrics_list if m.is_stale)
        ghost_vessels = sum(1 for m in metrics_list if m.is_ghost)
        priority_vessels = sum(1 for m in metrics_list if m.priority_vessel)
        
        # Risk distribution
        risk_counts = Counter(m.risk_level for m in metrics_list)
        
        # Country distribution
        country_counts = Counter(m.country for m in metrics_list if m.country)
        
        # Average metrics
        update_intervals = [m.avg_update_interval_minutes for m in metrics_list if m.avg_update_interval_minutes > 0]
        avg_update_interval = statistics.mean(update_intervals) if update_intervals else 0
        
        hours_since_updates = [m.hours_since_last_update for m in metrics_list]
        avg_hours_since_update = statistics.mean(hours_since_updates) if hours_since_updates else 0
        
        return {
            'total_vessels': total_vessels,
            'static_vessels': static_vessels,
            'stale_vessels': stale_vessels,
            'ghost_vessels': ghost_vessels,
            'priority_vessels': priority_vessels,
            'static_percentage': (static_vessels / total_vessels * 100) if total_vessels > 0 else 0,
            'stale_percentage': (stale_vessels / total_vessels * 100) if total_vessels > 0 else 0,
            'risk_distribution': dict(risk_counts),
            'country_distribution': dict(country_counts),
            'avg_update_interval_minutes': avg_update_interval,
            'avg_hours_since_update': avg_hours_since_update
        }
    
    def _generate_alerts(self, anomalies: List[AISAnomaly]) -> List[Dict]:
        """Generate alert messages from anomalies"""
        alerts = []
        
        for anomaly in anomalies:
            alert_level = anomaly.severity
            priority_flag = '🚨 PRIORITY VESSEL' if anomaly.country in ['Russia', 'China'] else ''
            
            alert = {
                'timestamp': anomaly.timestamp.isoformat(),
                'level': alert_level,
                'vessel': f"{anomaly.name} ({anomaly.mmsi})",
                'country': anomaly.country,
                'type': anomaly.anomaly_type,
                'message': f"{priority_flag} {anomaly.description}",
                'coordinates': anomaly.coordinates,
                'evidence': anomaly.evidence
            }
            alerts.append(alert)
        
        # Sort by severity and priority
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
        alerts.sort(key=lambda x: (
            severity_order.get(x['level'], 4),
            0 if x['country'] in ['Russia', 'China'] else 1
        ))
        
        return alerts
    
    def _generate_summary(self, vessel_metrics: Dict[str, VesselAISMetrics], anomalies: List[AISAnomaly]) -> Dict:
        """Generate analysis summary"""
        critical_anomalies = [a for a in anomalies if a.severity == 'CRITICAL']
        high_anomalies = [a for a in anomalies if a.severity == 'HIGH']
        priority_anomalies = [a for a in anomalies if a.country in ['Russia', 'China']]
        
        return {
            'total_vessels_analyzed': len(vessel_metrics),
            'total_anomalies': len(anomalies),
            'critical_anomalies': len(critical_anomalies),
            'high_priority_anomalies': len(high_anomalies),
            'priority_vessel_anomalies': len(priority_anomalies),
            'most_concerning_vessels': [
                {'mmsi': a.mmsi, 'name': a.name, 'type': a.anomaly_type, 'severity': a.severity}
                for a in sorted(anomalies, key=lambda x: (
                    0 if x.severity == 'CRITICAL' else 1,
                    0 if x.country in ['Russia', 'China'] else 1
                ))[:10]
            ]
        }
    
    def _get_country_from_mmsi(self, mmsi: str) -> str:
        """Get country from MMSI prefix"""
        if not mmsi:
            return 'Unknown'
        
        mmsi_str = str(mmsi)
        
        # Common MMSI country codes for Arctic region
        country_codes = {
            '273': 'Russia',
            '257': 'Norway', 
            '219': 'Denmark',
            '230': 'Finland',
            '266': 'Sweden',
            '245': 'Netherlands',
            '235': 'United Kingdom',
            '412': 'China',
            '413': 'China',
            '414': 'China',
            '338': 'United States',
            '316': 'Canada'
        }
        
        for prefix, country in country_codes.items():
            if mmsi_str.startswith(prefix):
                return country
        
        return 'Unknown'
    
    def _is_priority_vessel(self, mmsi: str) -> bool:
        """Check if vessel is a priority vessel (Russian or Chinese)"""
        if not mmsi:
            return False
        
        mmsi_str = str(mmsi)
        
        for pattern_list in self.priority_patterns.values():
            for pattern in pattern_list:
                if mmsi_str.startswith(pattern):
                    return True
        
        return False
    
    def _assess_risk_level(self, is_static: bool, is_stale: bool, is_ghost: bool, 
                          priority_vessel: bool, hours_since_update: float, 
                          stale_percentage: float) -> str:
        """Assess overall risk level for a vessel"""
        
        if is_ghost:
            return 'CRITICAL' if priority_vessel else 'HIGH'
        
        if is_static and priority_vessel:
            return 'CRITICAL'
        
        if hours_since_update > self.thresholds['critical_stale_hours']:
            return 'CRITICAL' if priority_vessel else 'HIGH'
        
        if is_stale or stale_percentage > 80:
            return 'HIGH' if priority_vessel else 'MEDIUM'
        
        if is_static:
            return 'MEDIUM'
        
        return 'LOW'


def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze AIS data for anomalies')
    parser.add_argument('--csv', required=True, help='Path to vessel positions CSV file')
    parser.add_argument('--history', required=True, help='Path to vessel history JSON file')
    parser.add_argument('--output', help='Output file for results (JSON)')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Run analysis
    detector = AISAnomalyDetector()
    results = detector.analyze_vessel_positions(args.csv, args.history)
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Results saved to {args.output}")
    else:
        # Print summary to console
        summary = results['summary']
        print(f"\nAIS Anomaly Analysis Summary:")
        print(f"Total vessels analyzed: {summary['total_vessels_analyzed']}")
        print(f"Total anomalies detected: {summary['total_anomalies']}")
        print(f"Critical anomalies: {summary['critical_anomalies']}")
        print(f"Priority vessel anomalies: {summary['priority_vessel_anomalies']}")
        
        if results['alerts']:
            print(f"\nTop 5 Alerts:")
            for i, alert in enumerate(results['alerts'][:5], 1):
                print(f"{i}. [{alert['level']}] {alert['vessel']} - {alert['message']}")


if __name__ == '__main__':
    main()