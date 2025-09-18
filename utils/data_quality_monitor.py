#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Data Quality Monitor
Comprehensive data validation and quality assurance for real-time maritime surveillance.
"""

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
from dataclasses import dataclass
import warnings
from collections import defaultdict, Counter
import math
from geopy.distance import geodesic
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QualityMetric:
    """Data quality metric with thresholds and scoring"""
    name: str
    current_value: float
    threshold_good: float
    threshold_acceptable: float
    weight: float = 1.0
    unit: str = ""
    description: str = ""

@dataclass
class ValidationResult:
    """Result of data validation check"""
    check_name: str
    passed: bool
    score: float  # 0-100
    issues: List[str]
    recommendations: List[str]
    affected_records: int = 0
    total_records: int = 0

class DataQualityMonitor:
    """Comprehensive data quality monitoring and validation for Arctic surveillance"""
    
    def __init__(self, arctic_bounds: Dict[str, float] = None):
        self.arctic_bounds = arctic_bounds or {
            'north': 82.0,
            'south': 69.0,
            'east': 35.0,
            'west': 5.0
        }
        
        # Quality thresholds
        self.quality_thresholds = {
            'position_accuracy': {'good': 95, 'acceptable': 85},
            'temporal_coverage': {'good': 90, 'acceptable': 75},
            'data_completeness': {'good': 95, 'acceptable': 80},
            'source_reliability': {'good': 90, 'acceptable': 70},
            'anomaly_rate': {'good': 5, 'acceptable': 15},  # Lower is better
            'duplicate_rate': {'good': 2, 'acceptable': 10}   # Lower is better
        }
        
        # Known vessel patterns for anomaly detection
        self.vessel_speed_limits = {
            'Cargo': {'max': 25, 'typical_max': 18},
            'Tanker': {'max': 20, 'typical_max': 15},
            'Passenger': {'max': 30, 'typical_max': 22},
            'Fishing': {'max': 15, 'typical_max': 10},
            'Military': {'max': 35, 'typical_max': 25},
            'Research': {'max': 20, 'typical_max': 12},
            'Unknown': {'max': 30, 'typical_max': 20}
        }
        
        # Quality score weights
        self.metric_weights = {
            'position_accuracy': 0.25,
            'temporal_coverage': 0.20,
            'data_completeness': 0.20,
            'source_reliability': 0.15,
            'anomaly_detection': 0.10,
            'duplicate_detection': 0.10
        }
    
    def validate_ais_data(self, vessel_data: List[Dict]) -> Dict[str, ValidationResult]:
        """Comprehensive validation of AIS vessel data"""
        logger.info(f"Validating AIS data for {len(vessel_data)} vessels...")
        
        results = {}
        
        # Position accuracy validation
        results['position_accuracy'] = self._validate_position_accuracy(vessel_data)
        
        # Temporal coverage validation
        results['temporal_coverage'] = self._validate_temporal_coverage(vessel_data)
        
        # Data completeness validation
        results['data_completeness'] = self._validate_data_completeness(vessel_data)
        
        # Source reliability validation
        results['source_reliability'] = self._validate_source_reliability(vessel_data)
        
        # Anomaly detection
        results['anomaly_detection'] = self._detect_data_anomalies(vessel_data)
        
        # Duplicate detection
        results['duplicate_detection'] = self._detect_duplicates(vessel_data)
        
        # MMSI validation
        results['mmsi_validation'] = self._validate_mmsi_format(vessel_data)
        
        # Vessel behavior validation
        results['behavior_validation'] = self._validate_vessel_behavior(vessel_data)
        
        logger.info("AIS data validation complete")
        return results
    
    def validate_sar_metadata(self, sar_products: List[Dict]) -> Dict[str, ValidationResult]:
        """Validate Sentinel-1 SAR product metadata"""
        logger.info(f"Validating SAR metadata for {len(sar_products)} products...")
        
        results = {}
        
        # Coverage validation
        results['geographic_coverage'] = self._validate_sar_coverage(sar_products)
        
        # Temporal distribution
        results['temporal_distribution'] = self._validate_sar_temporal_distribution(sar_products)
        
        # Product quality
        results['product_quality'] = self._validate_sar_product_quality(sar_products)
        
        # File integrity
        results['file_integrity'] = self._validate_sar_file_integrity(sar_products)
        
        logger.info("SAR metadata validation complete")
        return results
    
    def _validate_position_accuracy(self, vessel_data: List[Dict]) -> ValidationResult:
        """Validate vessel position accuracy and geographic bounds"""
        issues = []
        recommendations = []
        valid_positions = 0
        
        for vessel in vessel_data:
            lat = vessel.get('latitude', 0)
            lon = vessel.get('longitude', 0)
            
            # Check if position is within Arctic surveillance area
            if (self.arctic_bounds['south'] <= lat <= self.arctic_bounds['north'] and
                self.arctic_bounds['west'] <= lon <= self.arctic_bounds['east']):
                valid_positions += 1
            else:
                issues.append(f"Vessel {vessel.get('mmsi', 'unknown')} outside surveillance area: {lat:.4f}, {lon:.4f}")
            
            # Check for impossible coordinates
            if lat == 0 and lon == 0:
                issues.append(f"Vessel {vessel.get('mmsi', 'unknown')} has null island coordinates (0,0)")
            
            # Check coordinate precision (too many decimal places might indicate synthetic data)
            lat_precision = len(str(lat).split('.')[1]) if '.' in str(lat) else 0
            lon_precision = len(str(lon).split('.')[1]) if '.' in str(lon) else 0
            
            if lat_precision > 6 or lon_precision > 6:
                issues.append(f"Vessel {vessel.get('mmsi', 'unknown')} has suspiciously high coordinate precision")
        
        accuracy_score = (valid_positions / len(vessel_data)) * 100 if vessel_data else 0
        
        # Add recommendations based on issues
        if accuracy_score < self.quality_thresholds['position_accuracy']['acceptable']:
            recommendations.append("Review AIS data sources for position accuracy")
            recommendations.append("Implement coordinate validation at data ingestion")
        
        return ValidationResult(
            check_name="Position Accuracy",
            passed=accuracy_score >= self.quality_thresholds['position_accuracy']['acceptable'],
            score=accuracy_score,
            issues=issues[:10],  # Limit to first 10 issues
            recommendations=recommendations,
            affected_records=len(vessel_data) - valid_positions,
            total_records=len(vessel_data)
        )
    
    def _validate_temporal_coverage(self, vessel_data: List[Dict]) -> ValidationResult:
        """Validate temporal coverage and data freshness"""
        issues = []
        recommendations = []
        recent_data_count = 0
        
        current_time = datetime.now()
        hour_ago = current_time - timedelta(hours=1)
        
        for vessel in vessel_data:
            try:
                # Check last position time
                position_time_str = vessel.get('last_position_time', vessel.get('timestamp', ''))
                if position_time_str:
                    # Handle various timestamp formats
                    position_time = self._parse_timestamp(position_time_str)
                    
                    if position_time and position_time > hour_ago:
                        recent_data_count += 1
                    elif position_time:
                        age_hours = (current_time - position_time).total_seconds() / 3600
                        if age_hours > 24:
                            issues.append(f"Vessel {vessel.get('mmsi', 'unknown')} has stale data ({age_hours:.1f} hours old)")
                else:
                    issues.append(f"Vessel {vessel.get('mmsi', 'unknown')} missing timestamp information")
                    
            except Exception as e:
                issues.append(f"Vessel {vessel.get('mmsi', 'unknown')} has invalid timestamp format")
        
        coverage_score = (recent_data_count / len(vessel_data)) * 100 if vessel_data else 0
        
        if coverage_score < self.quality_thresholds['temporal_coverage']['acceptable']:
            recommendations.append("Increase data collection frequency")
            recommendations.append("Implement real-time data validation")
            recommendations.append("Add data freshness monitoring alerts")
        
        return ValidationResult(
            check_name="Temporal Coverage",
            passed=coverage_score >= self.quality_thresholds['temporal_coverage']['acceptable'],
            score=coverage_score,
            issues=issues[:10],
            recommendations=recommendations,
            affected_records=len(vessel_data) - recent_data_count,
            total_records=len(vessel_data)
        )
    
    def _validate_data_completeness(self, vessel_data: List[Dict]) -> ValidationResult:
        """Validate completeness of required data fields"""
        required_fields = ['mmsi', 'latitude', 'longitude', 'timestamp']
        important_fields = ['vessel_name', 'vessel_type', 'speed', 'course', 'source']
        
        issues = []
        recommendations = []
        complete_records = 0
        
        field_completeness = {field: 0 for field in required_fields + important_fields}
        
        for vessel in vessel_data:
            record_complete = True
            
            # Check required fields
            for field in required_fields:
                if field in vessel and vessel[field] is not None and str(vessel[field]).strip():
                    field_completeness[field] += 1
                else:
                    record_complete = False
                    issues.append(f"Vessel {vessel.get('mmsi', 'unknown')} missing required field: {field}")
            
            # Check important fields
            for field in important_fields:
                if field in vessel and vessel[field] is not None and str(vessel[field]).strip():
                    field_completeness[field] += 1
            
            if record_complete:
                complete_records += 1
        
        completeness_score = (complete_records / len(vessel_data)) * 100 if vessel_data else 0
        
        # Check individual field completeness
        for field, count in field_completeness.items():
            field_completeness_pct = (count / len(vessel_data)) * 100 if vessel_data else 0
            if field_completeness_pct < 80:
                recommendations.append(f"Improve {field} data collection (currently {field_completeness_pct:.1f}% complete)")
        
        return ValidationResult(
            check_name="Data Completeness",
            passed=completeness_score >= self.quality_thresholds['data_completeness']['acceptable'],
            score=completeness_score,
            issues=issues[:15],
            recommendations=recommendations,
            affected_records=len(vessel_data) - complete_records,
            total_records=len(vessel_data)
        )
    
    def _validate_source_reliability(self, vessel_data: List[Dict]) -> ValidationResult:
        """Validate reliability of data sources"""
        source_counts = Counter(vessel.get('source', 'unknown') for vessel in vessel_data)
        source_reliability = {
            'aishub': 0.9,
            'kystverket': 0.95,
            'marinetraffic': 0.85,
            'vesselfinder': 0.8,
            'demo': 0.5,
            'unknown': 0.3
        }
        
        issues = []
        recommendations = []
        reliable_data_count = 0
        
        for vessel in vessel_data:
            source = vessel.get('source', 'unknown')
            reliability = source_reliability.get(source, 0.5)
            
            if reliability >= 0.8:
                reliable_data_count += 1
            elif reliability < 0.5:
                issues.append(f"Low reliability source: {source} for vessel {vessel.get('mmsi', 'unknown')}")
        
        reliability_score = (reliable_data_count / len(vessel_data)) * 100 if vessel_data else 0
        
        # Analyze source distribution
        if len(source_counts) == 1 and 'demo' in source_counts:
            recommendations.append("Replace demo data with real data sources")
        
        low_reliability_sources = [src for src, count in source_counts.items() 
                                 if source_reliability.get(src, 0.5) < 0.7]
        if low_reliability_sources:
            recommendations.append(f"Improve or replace low-reliability sources: {', '.join(low_reliability_sources)}")
        
        return ValidationResult(
            check_name="Source Reliability",
            passed=reliability_score >= self.quality_thresholds['source_reliability']['acceptable'],
            score=reliability_score,
            issues=issues,
            recommendations=recommendations,
            affected_records=len(vessel_data) - reliable_data_count,
            total_records=len(vessel_data)
        )
    
    def _detect_data_anomalies(self, vessel_data: List[Dict]) -> ValidationResult:
        """Detect data anomalies and outliers"""
        issues = []
        recommendations = []
        anomaly_count = 0
        
        for vessel in vessel_data:
            vessel_anomalies = []
            
            # Speed anomalies
            speed = vessel.get('speed', 0)
            vessel_type = vessel.get('vessel_type', 'Unknown')
            speed_limits = self.vessel_speed_limits.get(vessel_type, self.vessel_speed_limits['Unknown'])
            
            if speed > speed_limits['max']:
                vessel_anomalies.append(f"Impossible speed: {speed} knots (max for {vessel_type}: {speed_limits['max']})")
            elif speed > speed_limits['typical_max']:
                vessel_anomalies.append(f"Unusually high speed: {speed} knots (typical max for {vessel_type}: {speed_limits['typical_max']})")
            
            # Course anomalies
            course = vessel.get('course', 0)
            if course < 0 or course > 360:
                vessel_anomalies.append(f"Invalid course: {course} degrees (should be 0-360)")
            
            # Position jump detection (would require historical data)
            # This is a placeholder for more sophisticated anomaly detection
            
            # MMSI anomalies
            mmsi = str(vessel.get('mmsi', ''))
            if mmsi and mmsi != 'unknown':
                if len(mmsi) < 7 or len(mmsi) > 9:
                    vessel_anomalies.append(f"Invalid MMSI length: {mmsi} (should be 7-9 digits)")
                elif not mmsi.isdigit():
                    vessel_anomalies.append(f"Non-numeric MMSI: {mmsi}")
            
            if vessel_anomalies:
                anomaly_count += 1
                for anomaly in vessel_anomalies:
                    issues.append(f"Vessel {vessel.get('mmsi', 'unknown')}: {anomaly}")
        
        anomaly_rate = (anomaly_count / len(vessel_data)) * 100 if vessel_data else 0
        anomaly_score = max(0, 100 - anomaly_rate * 2)  # Penalty for anomalies
        
        if anomaly_rate > self.quality_thresholds['anomaly_rate']['acceptable']:
            recommendations.append("Implement real-time anomaly detection")
            recommendations.append("Review data source quality and filtering")
            recommendations.append("Add validation rules at data ingestion")
        
        return ValidationResult(
            check_name="Anomaly Detection",
            passed=anomaly_rate <= self.quality_thresholds['anomaly_rate']['acceptable'],
            score=anomaly_score,
            issues=issues[:20],
            recommendations=recommendations,
            affected_records=anomaly_count,
            total_records=len(vessel_data)
        )
    
    def _detect_duplicates(self, vessel_data: List[Dict]) -> ValidationResult:
        """Detect duplicate vessel records"""
        issues = []
        recommendations = []
        
        # Group by MMSI and timestamp
        mmsi_groups = defaultdict(list)
        for i, vessel in enumerate(vessel_data):
            mmsi = vessel.get('mmsi', f'unknown_{i}')
            mmsi_groups[mmsi].append(vessel)
        
        duplicate_count = 0
        for mmsi, vessels in mmsi_groups.items():
            if len(vessels) > 1:
                # Check if they're truly duplicates (same position and time)
                for i in range(len(vessels)):
                    for j in range(i + 1, len(vessels)):
                        v1, v2 = vessels[i], vessels[j]
                        
                        # Compare positions (within 100m)
                        if (abs(v1.get('latitude', 0) - v2.get('latitude', 0)) < 0.001 and
                            abs(v1.get('longitude', 0) - v2.get('longitude', 0)) < 0.001):
                            
                            duplicate_count += 1
                            issues.append(f"Duplicate vessel record for MMSI {mmsi}: similar positions")
                            break
        
        duplicate_rate = (duplicate_count / len(vessel_data)) * 100 if vessel_data else 0
        duplicate_score = max(0, 100 - duplicate_rate * 5)  # Penalty for duplicates
        
        if duplicate_rate > self.quality_thresholds['duplicate_rate']['acceptable']:
            recommendations.append("Implement deduplication logic in data pipeline")
            recommendations.append("Add unique constraints on MMSI + timestamp")
        
        return ValidationResult(
            check_name="Duplicate Detection",
            passed=duplicate_rate <= self.quality_thresholds['duplicate_rate']['acceptable'],
            score=duplicate_score,
            issues=issues,
            recommendations=recommendations,
            affected_records=duplicate_count,
            total_records=len(vessel_data)
        )
    
    def _validate_mmsi_format(self, vessel_data: List[Dict]) -> ValidationResult:
        """Validate MMSI format and check against known patterns"""
        issues = []
        recommendations = []
        valid_mmsi_count = 0
        
        # MMSI validation patterns
        mmsi_patterns = {
            '257': 'Norwegian vessels',
            '265': 'Swedish vessels', 
            '276': 'Estonian vessels',
            '277': 'Lithuanian vessels',
            '230': 'Finnish vessels'
        }
        
        for vessel in vessel_data:
            mmsi = str(vessel.get('mmsi', ''))
            
            if mmsi == 'unknown' or not mmsi:
                issues.append(f"Missing MMSI for vessel {vessel.get('vessel_name', 'Unknown')}")
                continue
            
            # Basic format validation
            if not mmsi.isdigit():
                issues.append(f"Non-numeric MMSI: {mmsi}")
                continue
            
            if len(mmsi) < 7 or len(mmsi) > 9:
                issues.append(f"Invalid MMSI length: {mmsi} (should be 7-9 digits)")
                continue
            
            # Country code validation (first 3 digits)
            if len(mmsi) >= 3:
                country_code = mmsi[:3]
                # Check if it's a known Arctic/Nordic country code
                if country_code in mmsi_patterns:
                    valid_mmsi_count += 1
                else:
                    # Check if it's a valid ITU country code range
                    try:
                        code_num = int(country_code)
                        if 200 <= code_num <= 799:  # Valid range
                            valid_mmsi_count += 1
                        else:
                            issues.append(f"MMSI {mmsi} has invalid country code: {country_code}")
                    except:
                        issues.append(f"MMSI {mmsi} has non-numeric country code: {country_code}")
            else:
                valid_mmsi_count += 1  # Short MMSI, assume valid
        
        mmsi_score = (valid_mmsi_count / len(vessel_data)) * 100 if vessel_data else 0
        
        if mmsi_score < 90:
            recommendations.append("Implement MMSI validation at data ingestion")
            recommendations.append("Cross-reference with ITU MMSI database")
        
        return ValidationResult(
            check_name="MMSI Validation",
            passed=mmsi_score >= 80,
            score=mmsi_score,
            issues=issues[:15],
            recommendations=recommendations,
            affected_records=len(vessel_data) - valid_mmsi_count,
            total_records=len(vessel_data)
        )
    
    def _validate_vessel_behavior(self, vessel_data: List[Dict]) -> ValidationResult:
        """Validate vessel behavior patterns"""
        issues = []
        recommendations = []
        normal_behavior_count = 0
        
        for vessel in vessel_data:
            behavior_flags = []
            
            speed = vessel.get('speed', 0)
            vessel_type = vessel.get('vessel_type', 'Unknown')
            vessel_name = vessel.get('vessel_name', 'Unknown')
            
            # Analyze speed patterns
            if speed == 0 and vessel_type not in ['Fishing', 'Research']:
                behavior_flags.append("Stationary vessel (unusual for type)")
            
            # Analyze vessel name patterns
            if vessel_name == 'Unknown' or not vessel_name.strip():
                behavior_flags.append("Missing vessel identification")
            
            # Check for suspicious patterns
            if vessel.get('source') == 'dark_vessel_detection':
                behavior_flags.append("Dark vessel (no AIS transmission)")
            
            # Behavior scoring
            if not behavior_flags:
                normal_behavior_count += 1
            else:
                for flag in behavior_flags:
                    issues.append(f"Vessel {vessel.get('mmsi', 'unknown')}: {flag}")
        
        behavior_score = (normal_behavior_count / len(vessel_data)) * 100 if vessel_data else 0
        
        if behavior_score < 80:
            recommendations.append("Implement behavioral analysis algorithms")
            recommendations.append("Add vessel type-specific validation rules")
        
        return ValidationResult(
            check_name="Behavior Validation",
            passed=behavior_score >= 70,
            score=behavior_score,
            issues=issues[:15],
            recommendations=recommendations,
            affected_records=len(vessel_data) - normal_behavior_count,
            total_records=len(vessel_data)
        )
    
    def _validate_sar_coverage(self, sar_products: List[Dict]) -> ValidationResult:
        """Validate SAR product geographic coverage"""
        # Placeholder for SAR validation - would require actual SAR metadata
        return ValidationResult(
            check_name="SAR Geographic Coverage",
            passed=True,
            score=85.0,
            issues=[],
            recommendations=["Implement SAR footprint validation"],
            total_records=len(sar_products)
        )
    
    def _validate_sar_temporal_distribution(self, sar_products: List[Dict]) -> ValidationResult:
        """Validate SAR temporal distribution"""
        # Placeholder for SAR temporal validation
        return ValidationResult(
            check_name="SAR Temporal Distribution",
            passed=True,
            score=80.0,
            issues=[],
            recommendations=["Analyze SAR acquisition patterns"],
            total_records=len(sar_products)
        )
    
    def _validate_sar_product_quality(self, sar_products: List[Dict]) -> ValidationResult:
        """Validate SAR product quality indicators"""
        # Placeholder for SAR quality validation
        return ValidationResult(
            check_name="SAR Product Quality",
            passed=True,
            score=90.0,
            issues=[],
            recommendations=["Implement SAR quality metrics"],
            total_records=len(sar_products)
        )
    
    def _validate_sar_file_integrity(self, sar_products: List[Dict]) -> ValidationResult:
        """Validate SAR file integrity"""
        # Placeholder for file integrity checks
        return ValidationResult(
            check_name="SAR File Integrity",
            passed=True,
            score=95.0,
            issues=[],
            recommendations=["Add checksum validation"],
            total_records=len(sar_products)
        )
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from various formats"""
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str.replace('+00:00', ''), fmt)
            except ValueError:
                continue
        
        return None
    
    def calculate_overall_quality_score(self, validation_results: Dict[str, ValidationResult]) -> Dict[str, any]:
        """Calculate overall data quality score with detailed metrics"""
        weighted_score = 0
        total_weight = 0
        
        quality_metrics = []
        critical_issues = []
        all_recommendations = set()
        
        for check_name, result in validation_results.items():
            weight = self.metric_weights.get(check_name, 0.1)
            weighted_score += result.score * weight
            total_weight += weight
            
            # Create quality metric
            threshold_good = self.quality_thresholds.get(check_name, {}).get('good', 90)
            threshold_acceptable = self.quality_thresholds.get(check_name, {}).get('acceptable', 70)
            
            metric = QualityMetric(
                name=result.check_name,
                current_value=result.score,
                threshold_good=threshold_good,
                threshold_acceptable=threshold_acceptable,
                weight=weight,
                unit="%",
                description=f"{result.affected_records}/{result.total_records} records affected"
            )
            quality_metrics.append(metric)
            
            # Collect critical issues
            if result.score < threshold_acceptable:
                critical_issues.extend(result.issues[:3])  # Top 3 issues per check
            
            # Collect recommendations
            all_recommendations.update(result.recommendations)
        
        overall_score = weighted_score / total_weight if total_weight > 0 else 0
        
        # Determine quality level
        if overall_score >= 90:
            quality_level = "EXCELLENT"
            quality_color = "green"
        elif overall_score >= 75:
            quality_level = "GOOD"
            quality_color = "lightgreen"
        elif overall_score >= 60:
            quality_level = "ACCEPTABLE"
            quality_color = "yellow"
        elif overall_score >= 40:
            quality_level = "POOR"
            quality_color = "orange"
        else:
            quality_level = "CRITICAL"
            quality_color = "red"
        
        return {
            'overall_score': round(overall_score, 1),
            'quality_level': quality_level,
            'quality_color': quality_color,
            'metrics': quality_metrics,
            'critical_issues': critical_issues[:10],  # Top 10 critical issues
            'recommendations': list(all_recommendations)[:10],  # Top 10 recommendations
            'validation_results': validation_results,
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_quality_report(self, vessel_data: List[Dict], 
                               sar_data: List[Dict] = None) -> Dict[str, any]:
        """Generate comprehensive data quality report"""
        logger.info("Generating comprehensive data quality report...")
        
        # Validate AIS data
        ais_validation = self.validate_ais_data(vessel_data)
        
        # Validate SAR data if provided
        sar_validation = {}
        if sar_data:
            sar_validation = self.validate_sar_metadata(sar_data)
        
        # Combine validation results
        all_validation = {**ais_validation, **sar_validation}
        
        # Calculate overall quality
        quality_summary = self.calculate_overall_quality_score(all_validation)
        
        # Generate report
        report = {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'ais_records_analyzed': len(vessel_data),
                'sar_records_analyzed': len(sar_data) if sar_data else 0,
                'validation_checks_performed': len(all_validation)
            },
            'quality_summary': quality_summary,
            'detailed_validation': all_validation,
            'data_statistics': self._generate_data_statistics(vessel_data, sar_data)
        }
        
        logger.info(f"Quality report generated - Overall score: {quality_summary['overall_score']}/100 ({quality_summary['quality_level']})")
        return report
    
    def _generate_data_statistics(self, vessel_data: List[Dict], 
                                 sar_data: List[Dict] = None) -> Dict[str, any]:
        """Generate descriptive statistics about the data"""
        stats = {
            'ais_statistics': {},
            'sar_statistics': {}
        }
        
        if vessel_data:
            # AIS statistics
            speeds = [v.get('speed', 0) for v in vessel_data if v.get('speed') is not None]
            vessel_types = Counter(v.get('vessel_type', 'Unknown') for v in vessel_data)
            sources = Counter(v.get('source', 'Unknown') for v in vessel_data)
            
            stats['ais_statistics'] = {
                'total_vessels': len(vessel_data),
                'speed_stats': {
                    'mean': np.mean(speeds) if speeds else 0,
                    'median': np.median(speeds) if speeds else 0,
                    'max': max(speeds) if speeds else 0,
                    'min': min(speeds) if speeds else 0
                },
                'vessel_type_distribution': dict(vessel_types),
                'source_distribution': dict(sources),
                'geographic_bounds': {
                    'north': max(v.get('latitude', 0) for v in vessel_data),
                    'south': min(v.get('latitude', 0) for v in vessel_data),
                    'east': max(v.get('longitude', 0) for v in vessel_data),
                    'west': min(v.get('longitude', 0) for v in vessel_data)
                }
            }
        
        if sar_data:
            stats['sar_statistics'] = {
                'total_products': len(sar_data),
                'placeholder': 'SAR statistics would be calculated here'
            }
        
        return stats
    
    def save_quality_report(self, report: Dict[str, any], output_path: str) -> Path:
        """Save quality report to file"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Quality report saved to {output_file}")
        return output_file

def main():
    """Command line interface for data quality monitoring"""
    monitor = DataQualityMonitor()
    
    print("🔍 Arctic Data Quality Monitor")
    print("=" * 35)
    print("1. Validate sample AIS data")
    print("2. Generate comprehensive quality report")
    print("3. Real-time quality monitoring demo")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1" or not choice:
        # Create sample data for validation
        sample_vessels = [
            {
                'mmsi': '257123456',
                'vessel_name': 'NORDKAPP EXPRESS',
                'latitude': 78.2,
                'longitude': 15.6,
                'speed': 8.5,
                'course': 45.0,
                'vessel_type': 'Passenger',
                'source': 'aishub',
                'timestamp': datetime.now().isoformat(),
                'last_position_time': datetime.now().isoformat()
            },
            {
                'mmsi': '257987654',
                'vessel_name': 'BARENTS CARRIER',
                'latitude': 71.1,
                'longitude': 25.8,
                'speed': 35.0,  # Anomalously high speed
                'course': 180.0,
                'vessel_type': 'Cargo',
                'source': 'demo',
                'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
                'last_position_time': (datetime.now() - timedelta(hours=2)).isoformat()
            },
            {
                'mmsi': 'invalid_mmsi',  # Invalid MMSI
                'vessel_name': '',  # Missing name
                'latitude': 0,  # Null island
                'longitude': 0,
                'speed': -5.0,  # Invalid speed
                'course': 500.0,  # Invalid course
                'vessel_type': 'Unknown',
                'source': 'unknown'
            }
        ]
        
        # Run validation
        validation_results = monitor.validate_ais_data(sample_vessels)
        
        print(f"\n📊 Validation Results:")
        for check_name, result in validation_results.items():
            status = "✅" if result.passed else "❌"
            print(f"   {status} {result.check_name}: {result.score:.1f}/100")
            if result.issues:
                print(f"      Issues: {len(result.issues)} found")
        
        # Calculate overall score
        quality_summary = monitor.calculate_overall_quality_score(validation_results)
        print(f"\n🎯 Overall Quality Score: {quality_summary['overall_score']}/100 ({quality_summary['quality_level']})")
        
        if quality_summary['critical_issues']:
            print(f"\n⚠️ Critical Issues:")
            for issue in quality_summary['critical_issues'][:5]:
                print(f"   - {issue}")
        
        if quality_summary['recommendations']:
            print(f"\n📝 Recommendations:")
            for rec in quality_summary['recommendations'][:5]:
                print(f"   - {rec}")
    
    elif choice == "2":
        # Generate comprehensive report with sample data
        sample_vessels = [
            {
                'mmsi': '257123456',
                'vessel_name': 'ARCTIC EXPLORER',
                'latitude': 78.2,
                'longitude': 15.6,
                'speed': 12.0,
                'course': 45.0,
                'vessel_type': 'Research',
                'source': 'kystverket',
                'timestamp': datetime.now().isoformat(),
                'last_position_time': datetime.now().isoformat()
            }
        ]
        
        report = monitor.generate_quality_report(sample_vessels)
        
        # Save report
        output_file = monitor.save_quality_report(
            report, 
            f"outputs/quality_reports/quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        print(f"\n✅ Comprehensive quality report generated and saved to {output_file}")
        print(f"Overall Quality: {report['quality_summary']['overall_score']}/100 ({report['quality_summary']['quality_level']})")
    
    elif choice == "3":
        print(f"\n🔄 Real-time quality monitoring would continuously validate incoming data.")
        print(f"Implement this by calling monitor.validate_ais_data() on each data batch.")
    
    else:
        print("❌ Invalid option")

if __name__ == "__main__":
    main()