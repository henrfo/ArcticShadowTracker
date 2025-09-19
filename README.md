# Arctic Shadow Tracker (Consolidated)

A lean Arctic vessel surveillance system focusing on core AIS tracking functionality.

## What it does
- **24/7 AIS vessel tracking** in Arctic waters (latitude >= 65°N)
- **Dark vessel detection** - identifies vessels that stop transmitting AIS
- **Cable proximity monitoring** - alerts when vessels approach submarine cables
- **Interactive dashboard** - live HTML maps showing vessel positions and tracks

## Core Features (Preserved)
✅ Real-time AIS data collection via BarentsWatch API  
✅ CSV data storage (vessel positions, dark vessels, cable alerts)  
✅ Interactive HTML dashboard with vessel tracks  
✅ Automatic buoy/platform filtering  
✅ Country identification from MMSI prefixes  

## Eliminated Features (Scope Creep Removed)
❌ Satellite image collection and analysis  
❌ Complex ML models and autoencoders  
❌ Advanced risk scoring systems  
❌ Multiple testing frameworks  
❌ Duplicate configuration systems  
❌ Over-engineered analysis tools  

## Quick Start
```bash
# Install minimal dependencies
pip install -r requirements.txt

# Configure API credentials in config.yaml
# Run single test
python arctic_shadow_streamer.py test

# Run continuous monitoring (30-minute cycles)
python arctic_shadow_streamer.py
```

## Data Output
- `arctic_intelligence/vessel_positions.csv` - Current vessel positions
- `arctic_intelligence/dark_vessels.csv` - Vessels that stopped transmitting
- `arctic_intelligence/cable_alerts.csv` - Cable proximity alerts
- `arctic_intelligence/arctic_dashboard_with_tracks_latest.html` - Live dashboard

## Project Structure (Simplified)
```
ArcticShadowTracker/
├── arctic_shadow_streamer.py     # Main entry point
├── requirements.txt              # Minimal dependencies (4 packages)
├── config.yaml                   # API configuration
├── arctic_intelligence/          # Data output directory
└── src/arctic_tracker/           # Core modules only
    ├── core/                     # Main streaming logic
    ├── collectors/               # BarentsWatch API
    ├── monitoring/               # Cable monitoring
    └── utils/                    # Dashboard generation
```

## Consolidation Summary

### Before Cleanup:
- **926MB total** (137MB archive + 789MB outputs)
- **83 Python files** in archive alone
- **209 HTML dashboard files** with timestamps
- Complex satellite intelligence, ML models, multiple testing frameworks
- Duplicate code across multiple directories

### After Cleanup:
- **~50MB active code** (excluding virtual environment)
- **12 Python files** total (core functionality only)
- **Single dashboard file** (keeps latest only)
- Focus on working AIS tracking, dark vessel detection, cable monitoring
- Clean, maintainable structure

The project now follows the "less code, same functionality" principle - maintaining all working features while eliminating scope creep and technical debt.