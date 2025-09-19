# Arctic Shadow Tracker - CSV Storage Schemas

**Based on real BarentsWatch AIS data structure from barentswatch_test_v2.ipynb**

## Design Principles
- **Real data only** - Uses actual BarentsWatch API field names
- **Simple CSV structure** - Easy pandas DataFrame operations
- **Time-series optimized** - Efficient for trend analysis
- **Foreign vessel focus** - Excludes Norwegian MMSI patterns (257-259)
- **Dashboard ready** - Structured for interactive HTML generation

---

## 1. vessel_positions.csv
**Real-time AIS positions for all foreign vessels**

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| timestamp | datetime | ISO format timestamp | 2025-09-19T12:41:37.306199 |
| mmsi | int | Maritime Mobile Service Identity | 265064540 |
| name | string | Vessel name | KINFISH TENDER 3 |
| latitude | float | WGS84 latitude | 81.836007 |
| longitude | float | WGS84 longitude | 15.898378 |
| speed | float | Speed over ground (knots) | 3.3 |
| course | float | Course over ground (degrees) | 13.5 |
| vessel_type | int | AIS vessel type code | 90 |

**Sample Data:**
```csv
timestamp,mmsi,name,latitude,longitude,speed,course,vessel_type
2025-09-19T12:41:37.306199,265064540,KINFISH TENDER 3,81.836007,15.898378,3.3,13.5,90
2025-09-19T12:41:37.306209,257898600,BERGSFJORD,70.483413,22.161433,0.0,7.1,65
2025-09-19T12:41:37.306211,257747800,KIM ROGER,67.889017,13.02815,0.1,,30
```

**Usage:**
- Append each collection cycle (every 10-30 minutes)
- Filter foreign vessels only (exclude MMSI 257-259*)
- Enable vessel track analysis over time
- Support speed/course behavior pattern detection

---

## 2. dark_vessel_events.csv
**Vessels that have turned off AIS or gone silent**

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| detection_timestamp | datetime | When dark status was detected | 2025-09-19T14:30:00.000000 |
| mmsi | int | Vessel MMSI | 310123456 |
| name | string | Last known vessel name | MYSTERY SHIP |
| last_seen_timestamp | datetime | Last AIS transmission | 2025-09-19T08:15:00.000000 |
| hours_silent | float | Hours since last AIS | 6.25 |
| last_latitude | float | Last known latitude | 75.123456 |
| last_longitude | float | Last known longitude | 18.654321 |
| last_speed | float | Last reported speed | 12.3 |
| last_course | float | Last reported course | 45.0 |
| status | string | Detection status | DARK_VESSEL_SUSPECTED |

**Sample Data:**
```csv
detection_timestamp,mmsi,name,last_seen_timestamp,hours_silent,last_latitude,last_longitude,last_speed,last_course,status
2025-09-19T14:30:00.000000,310123456,MYSTERY SHIP,2025-09-19T08:15:00.000000,6.25,75.123456,18.654321,12.3,45.0,DARK_VESSEL_SUSPECTED
2025-09-19T15:45:00.000000,420987654,GHOST VESSEL,2025-09-19T02:30:00.000000,13.25,73.987654,22.345678,8.7,180.0,DARK_VESSEL_CONFIRMED
```

**Usage:**
- Track AIS gaps for intelligence analysis
- Correlate with satellite imagery for verification
- Monitor patterns of vessels going dark
- Generate alerts for suspicious behavior

---

## 3. cable_alerts.csv
**Vessel proximity to submarine cable infrastructure**

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| timestamp | datetime | Alert generation time | 2025-09-19T12:41:39.791202 |
| vessel_mmsi | int | Vessel MMSI | 257974800 |
| vessel_name | string | Vessel name | KVAENANGSTIND |
| cable_id | string | Cable system identifier | norway_uk |
| cable_name | string | Full cable name | Norway-UK Cable (Arctic Section) |
| distance_km | float | Distance to cable (km) | 6.16 |
| alert_threshold | int | Alert distance threshold | 8 |
| cable_status | string | Cable criticality level | HIGH |
| vessel_latitude | float | Vessel position latitude | 69.855578 |
| vessel_longitude | float | Vessel position longitude | 21.990712 |

**Sample Data:**
```csv
timestamp,vessel_mmsi,vessel_name,cable_id,cable_name,distance_km,alert_threshold,cable_status,vessel_latitude,vessel_longitude
2025-09-19T12:41:39.791202,257974800,KVAENANGSTIND,norway_uk,Norway-UK Cable (Arctic Section),6.16,8,HIGH,69.855578,21.990712
2025-09-19T12:41:39.793546,257303700,ISFUGLEN,svalbard_cable,Svalbard Undersea Cable System,6.74,10,CRITICAL,70.979417,25.975103
```

**Usage:**
- Monitor critical infrastructure security
- Track repeat offenders near cables
- Generate proximity heat maps
- Alert on vessels loitering near cables

---

## 4. daily_summary.csv
**Aggregated daily intelligence statistics**

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| date | date | Collection date | 2025-09-19 |
| total_collections | int | Number of data collections | 48 |
| total_vessels | int | Unique vessels tracked | 1520 |
| foreign_vessels | int | Non-Norwegian vessels | 1245 |
| norwegian_filtered | int | Norwegian vessels excluded | 275 |
| dark_vessel_events | int | New dark vessel detections | 3 |
| cable_alerts | int | Cable proximity alerts | 26 |
| critical_alerts | int | CRITICAL cable alerts | 18 |
| high_alerts | int | HIGH cable alerts | 8 |
| svalbard_vessels | int | Vessels in Svalbard waters | 89 |
| barents_vessels | int | Vessels in Barents Sea | 456 |
| north_norway_vessels | int | Vessels near North Norway | 789 |

**Sample Data:**
```csv
date,total_collections,total_vessels,foreign_vessels,norwegian_filtered,dark_vessel_events,cable_alerts,critical_alerts,high_alerts,svalbard_vessels,barents_vessels,north_norway_vessels
2025-09-19,48,1520,1245,275,3,26,18,8,89,456,789
2025-09-18,47,1489,1198,291,1,19,12,7,95,423,734
```

**Usage:**
- Track daily trends and patterns
- Generate intelligence briefings
- Monitor seasonal vessel activity changes
- Support long-term analysis

---

## Implementation Notes

### Norwegian Vessel Filtering
```python
# MMSI patterns to exclude (Norwegian vessels)
norwegian_mmsi_patterns = ['257', '258', '259']

# Norwegian name patterns (from real alerts in notebook)
norwegian_patterns = [
    'NO ', 'NORGE', 'NORSK', 'BERGEN', 'OSLO', 'STAVANGER', 
    'TROMSOE', 'TROMSO', 'HAVILA', 'HURTIGRUTEN', 'FJORD', 
    'STIND', 'FISK', 'FROST', 'POLAR', 'KVAL', 'SUND', 
    'BORG', 'HOLM', 'NESS', 'VIK', 'HAUG', 'STRAND'
]
```

### Pandas Integration
```python
# Efficient CSV operations
import pandas as pd

# Load vessel positions for analysis
df = pd.read_csv('vessel_positions.csv', parse_dates=['timestamp'])

# Time-series analysis
df.set_index('timestamp', inplace=True)
vessel_tracks = df.groupby('mmsi')

# Dashboard data aggregation
daily_stats = df.groupby(df.index.date).agg({
    'mmsi': 'nunique',
    'speed': 'mean',
    'latitude': ['min', 'max']
})
```

### File Rotation Strategy
- **vessel_positions.csv**: Rotate monthly (vessel_positions_YYYYMM.csv)
- **dark_vessel_events.csv**: Keep all historical data
- **cable_alerts.csv**: Keep all historical data  
- **daily_summary.csv**: Keep all historical data

### Data Collection Integration
```python
def save_to_csv(vessels, dark_vessels, cable_alerts):
    """Save intelligence data to CSV files"""
    
    # Save vessel positions
    vessel_df = pd.DataFrame(vessels)
    vessel_df.to_csv('vessel_positions.csv', mode='a', header=False, index=False)
    
    # Save dark vessel events
    if dark_vessels:
        dark_df = pd.DataFrame(dark_vessels)
        dark_df.to_csv('dark_vessel_events.csv', mode='a', header=False, index=False)
    
    # Save cable alerts
    if cable_alerts:
        cable_df = pd.DataFrame(cable_alerts)
        cable_df.to_csv('cable_alerts.csv', mode='a', header=False, index=False)
```

**These CSV schemas are optimized for the real BarentsWatch data structure and ready for pandas analysis and interactive dashboard generation.**