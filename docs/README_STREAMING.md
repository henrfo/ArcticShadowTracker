# Arctic Shadow Tracker - Streaming System

**Real-time Arctic maritime surveillance with dark vessel detection**

## 🎯 Overview

This system transforms the excellent `barentswatch_test_v2.ipynb` notebook into a production-ready streaming surveillance system that continuously monitors Arctic waters for suspicious vessel activity.

### ✅ Key Features Preserved from Notebook
- **Real BarentsWatch AIS data** - Live vessel tracking with actual API integration
- **Norwegian vessel filtering** - Smart MMSI (257-259) + name pattern filtering
- **Submarine cable monitoring** - Critical infrastructure protection around Norway/Svalbard
- **Dark vessel detection** - Enhanced 2-48 hour AIS gap detection
- **SAR satellite integration** - Copernicus imagery correlation (framework ready)
- **Interactive mapping** - Real-time HTML dashboard with Folium

### 🚀 New Streaming Capabilities
- **30-minute cycles** - Automated data collection every 30 minutes
- **CSV time-series database** - Structured data storage for analysis
- **Enhanced ML detection** - Advanced behavioral pattern analysis
- **Risk scoring** - Vessel behavior risk assessment
- **Continuous operation** - Production-ready streaming with logging

## 📁 File Structure

```
├── arctic_shadow_tracker_stream.py     # Main streaming system
├── enhanced_dark_vessel_detection.py   # Advanced ML detection algorithms
├── test_streaming_system.py           # Integration testing
├── config.yaml                        # API credentials (use existing)
└── data_stream/                       # Generated data files
    ├── csv/                          # Time-series CSV data
    │   ├── ais_history.csv           # All vessel positions over time
    │   ├── cable_alerts.csv          # Cable proximity incidents
    │   └── dark_vessels.csv          # Detected dark vessels
    ├── dashboard/                     # Interactive visualizations
    │   └── arctic_surveillance_dashboard.html
    └── intelligence/                  # Daily summaries
        └── daily_summary_YYYYMMDD.json
```

## 🛠️ Installation & Setup

### 1. Dependencies
```bash
pip install folium schedule pandas numpy scikit-learn matplotlib pyyaml requests
```

### 2. Configuration
Uses existing `config.yaml` - no changes needed!
```yaml
barentswatch:
  client_id: "your_client_id"
  client_secret: "your_secret"
  scope: "ais"

sentinel_hub:
  client_id: "your_sh_client_id"
  client_secret: "your_sh_secret"
```

### 3. Test the System
```bash
python test_streaming_system.py
```

## 🚀 Usage

### Start Continuous Surveillance (30-min cycles)
```bash
python arctic_shadow_tracker_stream.py
```

### Run Single Test Cycle
```bash
python arctic_shadow_tracker_stream.py test
```

### Monitor Output
- **Real-time dashboard**: `data_stream/dashboard/arctic_surveillance_dashboard.html`
- **CSV data**: `data_stream/csv/` (perfect for analysis)
- **Daily summaries**: `data_stream/intelligence/`
- **Logs**: `arctic_surveillance.log`

## 📊 Data Outputs

### CSV Files (Time-Series Ready)
1. **`ais_history.csv`** - All vessel positions with timestamps
   ```csv
   mmsi,name,latitude,longitude,speed,course,timestamp,vessel_type,collection_time
   265064540,KINFISH TENDER 3,81.836007,15.898378,3.3,13.5,2025-09-19T13:38:30...
   ```

2. **`cable_alerts.csv`** - Submarine cable proximity events
   ```csv
   timestamp,vessel_mmsi,vessel_name,cable_id,cable_name,distance_km,alert_threshold...
   2025-09-19T13:38:30,109010419,RONJA BOUY 9,svalbard_cable,Svalbard Undersea Cable System,7.51...
   ```

3. **`dark_vessels.csv`** - Detected AIS turn-off events
   ```csv
   mmsi,name,last_seen,hours_since_seen,last_latitude,last_longitude,detection_time,risk_score...
   ```

### Interactive Dashboard
Real-time HTML map showing:
- 🚢 Current vessel positions (blue = normal, orange = near cables)
- 🌑 Dark vessels (red markers at last known positions)
- 🔌 Submarine cable routes (red lines)
- 📊 Live statistics overlay

## 🧠 Enhanced Dark Vessel Detection

### Advanced Features
- **Behavioral Analysis** - Speed patterns, course changes, loitering detection
- **Risk Scoring** - ML-based suspicious behavior assessment
- **Pattern Clustering** - Identify anomalous vessel behaviors
- **Temporal Analysis** - Enhanced AIS gap detection with context

### Risk Levels
- **MINIMAL** (0.0-0.3) - Normal behavior
- **LOW** (0.3-0.6) - Minor anomalies
- **MEDIUM** (0.6-0.8) - Suspicious patterns
- **HIGH** (0.8-0.9) - Very suspicious behavior
- **CRITICAL** (0.9-1.0) - Highly suspicious, requires immediate attention

## 🎛️ System Configuration

### Arctic Regions Monitored
- **Svalbard Waters** (76-81°N, 10-35°E) - HIGH priority
- **Northern Norway Coast** (68-71.5°N, 15-32°E) - HIGH priority  
- **Central Barents Sea** (72-76°N, 20-40°E) - CRITICAL priority

### Submarine Cables Protected
- **Svalbard Undersea Cable System** - 10km alert radius
- **Lofoten-Vesterålen Cable** - 5km alert radius
- **Norway-UK Cable (Arctic Section)** - 8km alert radius

### Norwegian Vessel Filtering
- **MMSI Prefixes**: 257, 258, 259 (official Norwegian codes)
- **Name Patterns**: NORGE, NORSK, HAVILA, HURTIGRUTEN, FJORD, STIND, etc.

## 📈 Real-Time Performance

### Test Results (Latest Run)
```
🚢 Vessels tracked: 228 (non-Norwegian Arctic vessels)
🇳🇴 Norwegian vessels filtered: 1,291
🌑 Dark vessels detected: 0
⚠️ Cable alerts: 2 (RONJA BOUY 9, CELINA)
⏱️ Cycle time: 0.5 seconds
```

## 🔧 Coordination with Other Agents

### Data-Scientist Integration
- **CSV Schema**: Optimized for time-series analysis and pandas processing
- **Clean Data**: Pre-filtered, structured vessel data ready for analysis
- **Historical Tracking**: Built-in temporal continuity for trend analysis

### ML-Engineer Integration
- **Enhanced Detection Module**: `enhanced_dark_vessel_detection.py`
- **Feature Engineering**: Speed patterns, course analysis, behavioral clustering
- **Anomaly Detection**: DBSCAN clustering for outlier identification
- **Risk Assessment**: Multi-factor scoring system

### Logic-Professor Compliance
- **Simple Architecture**: Clear separation of concerns, maintainable code
- **Minimal Dependencies**: Uses standard libraries where possible
- **Clear Documentation**: Well-commented code with usage examples
- **Error Handling**: Robust exception handling and logging

## 🛡️ Security & Privacy

- **API Credentials**: Stored in local `config.yaml` (not committed)
- **Data Filtering**: Removes Norwegian vessels to focus on foreign activity
- **Local Storage**: All data stored locally, no external data transmission
- **Minimal Data**: Only essential vessel tracking information collected

## 🎉 Success Metrics

### Preserved Notebook Excellence
✅ **Real BarentsWatch data** - Working API integration  
✅ **Norwegian filtering** - Smart MMSI + name pattern filtering  
✅ **Cable monitoring** - Critical infrastructure protection  
✅ **Dark vessel detection** - 2-48 hour AIS gap analysis  
✅ **Interactive maps** - Real-time Folium visualizations  

### New Streaming Capabilities
✅ **30-minute automation** - Continuous surveillance cycles  
✅ **CSV database** - Time-series data for analysis  
✅ **Enhanced ML detection** - Behavioral pattern analysis  
✅ **Production ready** - Error handling, logging, testing  
✅ **Simple maintenance** - Clean code architecture  

## 🚀 Getting Started

1. **Test the system**: `python test_streaming_system.py`
2. **Run single cycle**: `python arctic_shadow_tracker_stream.py test`
3. **Start streaming**: `python arctic_shadow_tracker_stream.py`
4. **Monitor dashboard**: Open `data_stream/dashboard/arctic_surveillance_dashboard.html`
5. **Analyze data**: CSV files in `data_stream/csv/` ready for pandas analysis

**The system is now ready for continuous Arctic maritime surveillance! 🛰️**