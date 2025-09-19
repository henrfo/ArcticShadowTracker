# Arctic Shadow Tracker - Simple Streaming System

A clean, simple streaming system based on the proven `barentswatch_test_v2.ipynb` functionality. Monitors Arctic waters for dark vessels and submarine cable threats every 30 minutes using real BarentsWatch AIS data.

## 🎯 What This Does

**Core Capabilities (from the notebook):**
- **Real AIS Data Streaming** - BarentsWatch API every 30 minutes
- **Norwegian Vessel Filtering** - Focus on foreign vessels (MMSI filtering)
- **Dark Vessel Detection** - Find vessels with 2-48 hour AIS gaps
- **Submarine Cable Monitoring** - Alert when vessels approach critical infrastructure
- **CSV Time-Series Storage** - Build historical database for analysis
- **Interactive HTML Dashboard** - Real-time visualization

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Access
Create `config.yaml` with your BarentsWatch credentials:
```yaml
barentswatch:
  client_id: "your_client_id"
  client_secret: "your_client_secret"
  scope: "ais"
```

### 3. Test Single Cycle
```bash
python run_streamer.py test
```

### 4. Start Streaming
```bash
python run_streamer.py run
```

## 📊 Data Files Created

All data is saved in `streaming_data/` directory:

- **`vessel_tracking.csv`** - Time-series vessel positions
- **`cable_alerts.csv`** - Submarine cable proximity alerts
- **`dark_vessels.csv`** - Dark vessel detections
- **`arctic_dashboard.html`** - Interactive map (open in browser)
- **`streamer.log`** - System logs

## 🎛️ Simple Commands

```bash
# Test one cycle
python run_streamer.py test

# Start continuous streaming (30-min intervals)
python run_streamer.py run

# Check status and recent data
python run_streamer.py status

# Show help
python run_streamer.py help
```

## 📈 How It Works

The streaming system extracts and simplifies the 5 core functions from your excellent notebook:

1. **`collect_ais_data()`** - Get current vessel positions from BarentsWatch
2. **`check_cable_proximity()`** - Monitor vessels near submarine cables
3. **`detect_dark_vessels()`** - Find AIS gaps in historical data
4. **`save_to_csv()`** - Store data in time-series format
5. **`create_html_dashboard()`** - Generate interactive map

### Norwegian Vessel Filtering
Excludes vessels with:
- MMSI starting with 257, 258, 259 (Norwegian)
- Norwegian name patterns (HAVILA, HURTIGRUTEN, etc.)

### Dark Vessel Detection
Considers vessels "dark" if:
- Previously active in last 48 hours
- Missing from current AIS for 2-48 hours
- Not appearing in current stream

## 🗺️ Dashboard Features

The HTML dashboard shows:
- **Blue dots** - Current foreign vessels
- **Orange dots** - Vessels near submarine cables
- **Red dots** - Dark vessels (last known position)
- **Red lines** - Critical submarine cables
- **Real-time stats** - Vessel count, alerts, dark vessels

## 🔧 Configuration

Edit `arctic_shadow_streamer.py` to customize:

```python
# Streaming interval
STREAM_INTERVAL_MINUTES = 30  # Change to 15, 60, etc.

# Dark vessel detection thresholds
DARK_VESSEL_MIN_HOURS = 2     # Minimum hours to consider "dark"
DARK_VESSEL_MAX_HOURS = 48    # Maximum hours to track

# Submarine cable alert distances
SUBMARINE_CABLES = {
    'svalbard_cable': {
        'alert_distance_km': 10  # Alert distance in km
    }
}
```

## 📝 Monitoring

**Check logs:**
```bash
tail -f streaming_data/streamer.log
```

**Analyze CSV data:**
```python
import pandas as pd

# Load vessel tracking data
vessels = pd.read_csv('streaming_data/vessel_tracking.csv')
vessels['timestamp'] = pd.to_datetime(vessels['timestamp'])

# Count vessels by hour
hourly_counts = vessels.groupby(vessels['timestamp'].dt.hour).size()
print(hourly_counts)
```

## 🛡️ Error Handling

The streamer includes robust error handling:
- **API failures** - Retries with exponential backoff
- **Network issues** - Continues on next cycle
- **Data corruption** - Logs errors, continues operation
- **Interrupted cycles** - Automatic recovery on restart

## 💡 Based on Proven Notebook

This streaming system directly implements the excellent functionality from `barentswatch_test_v2.ipynb`:
- Same AIS data source and filtering logic
- Same submarine cable definitions and proximity calculations
- Same dark vessel detection algorithm
- Same map visualization approach
- Simplified for continuous operation

**The notebook's proven real-data approach is preserved while adding streaming and CSV storage capabilities.**