# Enhanced Arctic Surveillance Dashboard with Vessel Tracks

## Overview

The enhanced Arctic surveillance dashboard provides 24-hour vessel tracking for priority vessels (Russian and Chinese ships) in Arctic waters. This system builds upon the existing Arctic Shadow Tracker surveillance infrastructure.

## Key Features

### 🇷🇺 Russian Vessel Tracking
- Tracks all vessels with MMSI starting with **273** (Russian flag)
- Displays 24-hour movement tracks as **red lines**
- Shows current vessel positions as **red circle markers**

### 🇨🇳 Chinese Vessel Tracking  
- Tracks all vessels with MMSI starting with **412, 413, 414** (Chinese flag)
- Displays 24-hour movement tracks as **orange lines**
- Shows current vessel positions as **orange circle markers**

### 🌍 Comprehensive Surveillance
- All existing features maintained (dark vessels, cable alerts, other vessels)
- Interactive submarine cable monitoring
- Real-time vessel information on hover/click
- Clean visualization without directional arrows

## Files Generated

### Main Dashboard Files
- `arctic_dashboard_with_tracks_latest.html` - **Use this for live updates**
- `arctic_dashboard_with_tracks_YYYYMMDD_HHMMSS.html` - Timestamped versions

### Legacy Files (maintained)
- `arctic_dashboard_latest.html` - Standard dashboard without tracks
- Other existing surveillance data files

## Usage

### Quick Start
```bash
# Create enhanced dashboard
python create_russian_tracks_dashboard.py

# Open in browser
open arctic_intelligence/arctic_dashboard_with_tracks_latest.html
```

### Integration with Live System
The enhanced dashboard integrates seamlessly with the existing streaming system:

```bash
# Run enhanced surveillance (creates both standard and enhanced dashboards)
python -c "
import sys
sys.path.insert(0, 'src')
from arctic_tracker.core.enhanced_arctic_shadow_streamer import run_enhanced_surveillance_cycle
run_enhanced_surveillance_cycle()
"
```

### Manual Dashboard Creation
```bash
# Standalone enhanced dashboard creation
python scripts/create_enhanced_dashboard.py
```

## Dashboard Information Panel

The dashboard displays real-time statistics:
- **🚢 Total Vessels**: All vessels currently tracked
- **🇷🇺 Russian Tracks**: Russian vessels with 24h movement data
- **🇨🇳 Chinese Tracks**: Chinese vessels with 24h movement data  
- **🌑 Dark Vessels**: Vessels that have gone silent (AIS off)
- **⚠️ Cable Alerts**: Vessels near submarine cables
- **🕐 Updated**: Last refresh timestamp

## Track Visualization Details

### Track Lines
- **Thin colored lines** showing vessel movement over last 24 hours
- **Red tracks** for Russian vessels
- **Orange tracks** for Chinese vessels
- Chronologically ordered from oldest to newest position

### Vessel Markers
- **Circle markers** at current vessel positions
- **Color-coded** by vessel nationality
- **Click for details**: MMSI, name, speed, course, track length
- **Hover for quick info**: Vessel name

### Interactive Features
- **Zoom/Pan**: Standard map controls
- **Click tracks**: View vessel movement details
- **Click markers**: Detailed vessel information
- **Submarine cables**: Purple lines with alert distances

## Data Sources

### Required Files
- `vessel_history.json` - Historical vessel positions (24h+ data)
- `vessel_positions.csv` - Current vessel positions
- `dark_vessels.csv` - Vessels that have gone dark
- `cable_alerts.csv` - Cable proximity alerts

### Data Flow
1. **AIS Data Collection** → Real-time vessel positions
2. **Historical Tracking** → 24-hour position history
3. **Track Generation** → Visual movement lines
4. **Dashboard Creation** → Interactive HTML map

## Technical Details

### Vessel Identification
- **Russian vessels**: MMSI codes 273xxxxxx
- **Chinese vessels**: MMSI codes 412xxxxxx, 413xxxxxx, 414xxxxxx
- **Track filtering**: Last 24 hours of position data
- **Minimum track**: Requires 2+ positions for track display

### Color Schemes
- **Russian vessels**: Various red shades (#FF0000, #FF4500, #FF6347, etc.)
- **Chinese vessels**: Orange/amber tones (#FF8C00, #FFA500, #FFB84D, etc.)
- **Other vessels**: Blue (friendly), Gray (unknown)
- **Submarine cables**: Purple (#800080)
- **Dark vessels**: Black/dark red

### Performance
- **Track complexity**: Optimized for Arctic surveillance scales
- **Update frequency**: 30-minute cycles (configurable)
- **Data retention**: Last 24 hours for tracks, longer for alerts

## Integration with Live Dashboard Server

The enhanced dashboard works with the existing live dashboard server:

```bash
# Start live server (serves latest enhanced dashboard)
python live_dashboard_server.py
```

Access via: `http://localhost:8000/arctic_intelligence/arctic_dashboard_with_tracks_latest.html`

## Troubleshooting

### No Tracks Displayed
- Verify `vessel_history.json` contains recent data (last 24h)
- Check that Russian/Chinese vessels have position data
- Ensure minimum 2 positions per vessel for track generation

### Missing Vessels
- Confirm vessel MMSI codes are correct (273xxx for Russia, 412/413/414xxx for China)
- Check data collection is running and updating vessel_history.json
- Verify vessel filtering is working correctly

### Dashboard Not Loading
- Ensure all required data files exist in `arctic_intelligence/` directory
- Check Python path and module imports
- Verify folium and other dependencies are installed

## Files and Scripts

### Core Modules
- `src/arctic_tracker/utils/enhanced_dashboard.py` - Enhanced dashboard generator
- `src/arctic_tracker/core/enhanced_arctic_shadow_streamer.py` - Enhanced streaming system

### Scripts
- `create_russian_tracks_dashboard.py` - Main launcher script
- `scripts/create_enhanced_dashboard.py` - Standalone creator

### Data Files
- `arctic_intelligence/vessel_history.json` - Historical positions
- `arctic_intelligence/vessel_positions.csv` - Current positions
- Generated HTML dashboards in `arctic_intelligence/`

---

**Note**: This enhanced dashboard maintains full compatibility with the existing Arctic Shadow Tracker system while adding advanced vessel tracking capabilities for priority vessels.