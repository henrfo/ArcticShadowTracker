# Enhanced Dark Vessel Detection System
**Building on the Excellent Foundation from barentswatch_test_v2.ipynb**

## Overview

The enhanced dark vessel detection system builds upon the excellent foundation established in `barentswatch_test_v2.ipynb`, adding sophisticated pattern analysis and risk scoring while preserving all original functionality.

## Original Foundation (Preserved)

The notebook established an excellent dark vessel detection system:

### Core Capabilities
- **AIS History Tracking**: Tracks vessel positions over time in `ais_history.json`
- **2-48 Hour Detection Window**: Detects AIS gaps between 2-48 hours
- **Foreign Vessel Focus**: Excludes Norwegian vessels (MMSI 257-259 + name patterns)
- **Last Known Positions**: Stores detailed position data for disappeared vessels
- **Real BarentsWatch Data**: Works with actual AIS streams

### Norwegian Vessel Filtering
```python
# MMSI patterns (preserved exactly)
norwegian_mmsi_patterns = ['257', '258', '259']

# Name patterns (from real alerts in notebook)
norwegian_patterns = [
    'NO ', 'NORGE', 'NORSK', 'BERGEN', 'OSLO', 'STAVANGER', 
    'TROMSOE', 'TROMSO', 'HAVILA', 'HURTIGRUTEN', 'FJORD', 
    'STIND', 'FISK', 'FROST', 'POLAR', 'KVAL', 'SUND', 
    'BORG', 'HOLM', 'NESS', 'VIK', 'HAUG', 'STRAND'
]
```

### Submarine Cable Monitoring (Preserved)
```python
# Cable coordinates and alert distances (from notebook)
SUBMARINE_CABLES = {
    'svalbard_cable': {
        'coordinates': [[78.9, 11.9], [71.0, 25.8]],
        'alert_distance_km': 10
    },
    'lofoten_vesteralen': {
        'coordinates': [[68.8, 13.6], [69.3, 16.0]], 
        'alert_distance_km': 5
    },
    'norway_uk': {
        'coordinates': [[70.0, 23.0], [69.0, 18.0]],
        'alert_distance_km': 8
    }
}
```

## Enhancements Added

### 1. Enhanced AIS Gap Detection with Pattern Analysis

**Original**: Basic time-based detection (2-48 hours)
**Enhanced**: Adds behavioral pattern analysis

```python
class SuspiciousPattern(Enum):
    REPEATED_DARK_PERIODS = "REPEATED_DARK_PERIODS"
    SPEED_CHANGE_BEFORE_DARK = "SPEED_CHANGE_BEFORE_DARK"
    COURSE_DEVIATION_BEFORE_DARK = "COURSE_DEVIATION_BEFORE_DARK"
    PROXIMITY_TO_CABLES_WHEN_DARK = "PROXIMITY_TO_CABLES_WHEN_DARK"
    REAPPEARANCE_DISTANT_LOCATION = "REAPPEARANCE_DISTANT_LOCATION"
    DARK_NEAR_SENSITIVE_AREA = "DARK_NEAR_SENSITIVE_AREA"
```

### 2. Behavioral Pattern Analysis

Analyzes vessel behavior in the 6 hours before going dark:

- **Speed Changes**: Significant speed alterations before AIS turn-off
- **Course Deviations**: Suspicious course changes (>45° threshold)
- **Proximity Patterns**: Going dark near submarine cables or sensitive areas
- **Repeated Behavior**: Vessels with history of turning off AIS

### 3. Risk Scoring System

**Four-Level Risk Classification**:
- **CRITICAL** (75-100): Immediate attention required
- **HIGH** (50-74): Priority investigation
- **MEDIUM** (25-49): Standard monitoring
- **LOW** (0-24): Routine tracking

**Risk Factors**:
```python
# Base scoring components
dark_duration_score = min(hours_dark / 24.0, 1.0) * 30.0
pattern_scores = {
    REPEATED_DARK_PERIODS: 25.0,
    SPEED_CHANGE_BEFORE_DARK: 15.0,
    COURSE_DEVIATION_BEFORE_DARK: 15.0,
    PROXIMITY_TO_CABLES_WHEN_DARK: 30.0,
    REAPPEARANCE_DISTANT_LOCATION: 20.0,
    DARK_NEAR_SENSITIVE_AREA: 20.0
}
```

### 4. Real-time Correlation

- **Cable Proximity Analysis**: Distance to submarine cables when going dark
- **Sensitive Area Detection**: Arctic regions (Svalbard, Barents Sea, Northern Norway)
- **Historical Pattern Tracking**: Previous dark vessel events per MMSI
- **Satellite Imagery Timing**: Correlates AIS gaps with satellite pass times

### 5. Enhanced CSV Integration

**New Enhanced Schema**: `enhanced_dark_vessel_events.csv`
```csv
mmsi,name,detection_timestamp,last_seen_timestamp,hours_silent,
last_latitude,last_longitude,last_speed,last_course,status,
risk_level,risk_score,suspicious_patterns,previous_dark_events,
cable_proximity_when_dark,speed_change_before_dark,
course_deviation_before_dark,reappearance_distance
```

**Backward Compatibility**: Also saves to original `dark_vessel_events.csv` format

### 6. Advanced Alert Generation

**Enhanced Alert Structure**:
```python
alert = {
    'type': 'ENHANCED_DARK_VESSEL',
    'priority': risk_level,
    'vessel_info': {
        'mmsi': mmsi,
        'name': name,
        'last_position': [lat, lon],
        'hours_dark': hours_silent
    },
    'risk_assessment': {
        'score': risk_score,
        'level': risk_level,
        'patterns': suspicious_patterns,
        'previous_events': previous_dark_events
    },
    'location_analysis': {
        'cable_proximity': cable_distance,
        'sensitive_area': area_name
    }
}
```

## Implementation Architecture

### Core Components

1. **EnhancedDarkVesselDetector**: Main detection engine
2. **EnhancedDarkVesselDetectorProxy**: Streaming system integration
3. **EnhancedDashboardGenerator**: Risk-based visualization
4. **Integration Functions**: Backward compatibility

### File Structure
```
enhanced_dark_vessel_detection.py      # Core enhanced detection
streaming_integration_patch.py         # Streaming system integration
enhanced_streaming_example.py          # Complete usage example
test_enhanced_system.py               # Test suite
```

## Integration with Existing System

### Method 1: Direct Replacement
```python
# Replace existing detector
from streaming_integration_patch import EnhancedDarkVesselDetectorProxy
detector = EnhancedDarkVesselDetectorProxy()

# Same interface as original
dark_vessels = detector.detect_dark_vessels(current_vessels, history_df)
```

### Method 2: Standalone Integration
```python
# Standalone enhanced detection
from enhanced_dark_vessel_detection import integrate_with_streaming_system
results = integrate_with_streaming_system(current_vessels)
```

### Method 3: Complete Enhanced System
```python
# Full enhanced surveillance system
from enhanced_streaming_example import EnhancedArcticSurveillanceSystem
surveillance = EnhancedArcticSurveillanceSystem()
result = surveillance.run_enhanced_surveillance_cycle()
```

## Key Benefits

### 1. **Maintains Simplicity**
- Preserves notebook's excellent simple algorithms
- No complex machine learning or overcomplicated analysis
- Easy to understand and maintain

### 2. **Real Data Focus**
- Works with actual BarentsWatch AIS streams
- Tested with real Arctic vessel data
- Practical thresholds based on maritime operations

### 3. **Foreign Vessel Focus**
- Continues filtering Norwegian vessels
- Focuses on vessels of intelligence interest
- Reduces false positives from domestic traffic

### 4. **Pattern-Based Intelligence**
- Identifies suspicious AIS turn-off behaviors
- Tracks vessels near critical infrastructure
- Correlates with submarine cable proximity

### 5. **Operational Integration**
- CSV-compatible with existing data pipelines
- Dashboard-ready alert generation
- Backward compatible with current system

## Usage Examples

### Enhanced Detection Log Output
```
🚨 Found 3 suspected dark vessels!
🔴 MYSTERY_VESSEL_1 (MMSI: 310123456) - CRITICAL risk (87.5)
     Dark for 18.3h, 3 suspicious patterns
     🔌 Cable proximity: 4.2km
     ⚠️ Patterns: PROXIMITY_TO_CABLES_WHEN_DARK, SPEED_CHANGE_BEFORE_DARK, REPEATED_DARK_PERIODS

🟡 GHOST_SHIP_2 (MMSI: 420987654) - HIGH risk (62.1)
     Dark for 12.7h, 2 suspicious patterns
     ⚠️ Patterns: COURSE_DEVIATION_BEFORE_DARK, DARK_NEAR_SENSITIVE_AREA

🟢 FISHING_VESSEL_3 (MMSI: 530456789) - MEDIUM risk (28.4)
     Dark for 6.1h, 1 suspicious patterns
     ⚠️ Patterns: SPEED_CHANGE_BEFORE_DARK
```

### Enhanced CSV Output
```csv
mmsi,name,risk_level,risk_score,suspicious_patterns,cable_proximity_when_dark
310123456,MYSTERY_VESSEL_1,CRITICAL,87.5,"PROXIMITY_TO_CABLES_WHEN_DARK,SPEED_CHANGE_BEFORE_DARK",4.2
420987654,GHOST_SHIP_2,HIGH,62.1,"COURSE_DEVIATION_BEFORE_DARK,DARK_NEAR_SENSITIVE_AREA",
530456789,FISHING_VESSEL_3,MEDIUM,28.4,SPEED_CHANGE_BEFORE_DARK,
```

## Deployment

### Requirements
- Python 3.8+
- pandas, numpy, folium
- Existing config.yaml with BarentsWatch credentials
- CSV data directory structure

### Installation
1. Add enhanced modules to existing project
2. Install requirements: `pip install pandas numpy folium`
3. Run test: `python test_enhanced_system.py`
4. Integrate with streaming: Apply `streaming_integration_patch.py`

### Configuration
Uses existing `config.yaml` - no additional configuration required.

## Testing

The system includes comprehensive tests:
- Enhanced detection functionality
- Streaming system integration
- CSV schema validation
- Dashboard compatibility
- Backward compatibility verification

Run tests: `python test_enhanced_system.py`

## Conclusion

The enhanced dark vessel detection system successfully builds upon the excellent foundation from `barentswatch_test_v2.ipynb`, adding sophisticated pattern analysis and risk scoring while preserving all original functionality. It maintains the notebook's focus on simplicity, real data, and foreign vessel monitoring while adding the intelligence capabilities needed for effective Arctic maritime surveillance.

The system is ready for immediate deployment and provides a significant enhancement to dark vessel detection capabilities without disrupting existing operations.