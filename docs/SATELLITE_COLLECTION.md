# Satellite Imagery Collection - Sentinel-1 SAR

The Arctic Shadow Tracker uses Sentinel-1 Synthetic Aperture Radar (SAR) imagery for dark vessel detection - identifying vessels that are not transmitting AIS signals.

## Overview

**Purpose**: Detect vessels that disable their AIS transponders (dark vessels) by analyzing satellite radar imagery.

**Satellite**: Sentinel-1 (ESA Copernicus program)
- **Type**: C-band Synthetic Aperture Radar
- **Advantage**: Works day/night, through clouds and fog
- **Resolution**: 10-100 meters
- **Coverage**: Global, including Arctic waters
- **Revisit Time**: ~6 days for Arctic region

## Quick Start

### Local Collection

```bash
# Run satellite collection script
python scripts/collect_satellite.py
```

### Requirements

1. **Sentinel Hub Account** (Free tier available)
   - Sign up at: https://www.sentinel-hub.com/
   - Get OAuth credentials (client_id, client_secret)

2. **Add credentials to config.yaml**:
```yaml
sentinel_hub:
  client_id: "your-client-id"
  client_secret: "your-client-secret"
```

3. **Install dependencies**:
```bash
pip install sentinelhub numpy
```

## GitHub Actions Automation

The satellite collection runs automatically **daily** via `.github/workflows/satellite_monitor.yml`.

### Setup GitHub Secrets

Add these secrets in GitHub repo settings:
- `SENTINEL_CLIENT_ID`: Your Sentinel Hub OAuth client ID
- `SENTINEL_CLIENT_SECRET`: Your Sentinel Hub OAuth client secret

### Workflow Schedule
- **Frequency**: Daily at midnight UTC
- **Reason**: SAR imagery updates less frequently than AIS (every 6-12 days vs. every 30 minutes)
- **Manual Trigger**: Available via "Run workflow" button in Actions tab

## Data Storage

### Local Development
```
data/
  satellite_imagery/
    metadata.json         # Tracked in git - image catalog
    tiles/
      YYYYMMDD_HHMMSS_*.tiff   # Excluded from git (large files)
```

### What's Committed to Git
- ✅ `metadata.json` - Image catalog, timestamps, coverage info
- ❌ `tiles/*.tiff` - Raw satellite imagery (excluded by .gitignore)

**Why?** TIFF files are large (50-200MB each). Only metadata is tracked in git.

### Retention Policy
- **Local tiles**: 14 days (auto-cleanup)
- **Metadata**: Permanent (for historical tracking)

## How Satellite Collection Works

### 1. Search for Imagery
```python
# Searches Sentinel Hub catalog for recent Sentinel-1 images
# Coverage: Arctic region (65-82°N, 0-40°E)
# Time range: Last 7 days
```

### 2. Download SAR Tiles
```python
# Downloads up to 5 most recent images
# Bands: VV and VH polarization (for vessel detection)
# Resolution: 100 meters per pixel
# Format: GeoTIFF
```

### 3. Save Metadata
```python
# Records:
# - Image ID, timestamp, location
# - Download status
# - Instrument mode (IW - Interferometric Wide Swath)
```

### 4. Cleanup Old Files
```python
# Deletes tiles older than 14 days
# Keeps metadata indefinitely
```

## SAR Vessel Detection Basics

Sentinel-1 SAR imagery can detect vessels because:
1. **Metal hulls reflect radar** - Vessels appear as bright spots
2. **Cloud-independent** - Works in Arctic fog/darkness
3. **Wake detection** - Ship wakes visible in calm seas
4. **Size estimation** - Vessel length correlates with brightness

### Polarization Bands
- **VV (Vertical-Vertical)**: Best for vessel detection on calm water
- **VH (Vertical-Horizontal)**: Reduces sea clutter, enhances vessel signatures

## Integration with AIS Data

### Dark Vessel Detection Workflow
1. **Collect AIS positions** (every 30 minutes via `collect_ais.py`)
2. **Collect SAR imagery** (daily via `collect_satellite.py`)
3. **Compare locations**:
   - SAR detections WITH matching AIS → Normal vessels
   - SAR detections WITHOUT matching AIS → **Dark vessels** (suspicious)

### Future Development
The project will add:
- Automated vessel detection algorithms (OpenCV, YOLO)
- AIS-SAR correlation analysis
- Dark vessel alert system
- Historical dark vessel tracking

## Sentinel Hub API Limits

### Free Tier (Default)
- **Processing Units**: 30,000 per month
- **Cost per tile**: ~100-300 PU (depending on resolution)
- **Estimated tiles**: ~100-300 tiles per month

### Commercial Tier
- Higher quotas available
- Required for high-frequency monitoring

**Tip**: Daily collection (1 tile/day) = ~30 tiles/month, well within free tier.

## Troubleshooting

### Authentication Error
```bash
# Error: Invalid credentials
# Solution: Check config.yaml or GitHub Secrets
```

### No Imagery Found
```bash
# Sentinel-1 revisit time is 6-12 days for Arctic
# Try increasing search window: days_back=14
```

### Download Failed
```bash
# Check Sentinel Hub quota
# Visit: https://apps.sentinel-hub.com/dashboard/
```

### Tiles Too Large
```bash
# Reduce resolution in collect_satellite.py:
# resolution=100  →  resolution=200
```

## Testing Locally

```bash
# Test satellite collection (uses local credentials)
python scripts/collect_satellite.py

# Check downloaded tiles
ls -lh data/satellite_imagery/tiles/

# View metadata
cat data/satellite_imagery/metadata.json
```

## Next Steps

1. **Vessel Detection Algorithm**: Implement automated detection using image processing
2. **AIS Correlation**: Cross-reference SAR detections with AIS positions
3. **Alert System**: Flag dark vessels near critical infrastructure (submarine cables)
4. **Historical Analysis**: Track dark vessel patterns over time

## References

- **Sentinel Hub API**: https://docs.sentinel-hub.com/api/latest/
- **Sentinel-1 Specs**: https://sentinels.copernicus.eu/web/sentinel/missions/sentinel-1
- **SAR Vessel Detection**: https://www.mdpi.com/2072-4292/11/6/692
- **Dark Vessels Research**: https://globalfishingwatch.org/

## Related Files

- `scripts/collect_satellite.py` - Main collection script
- `.github/workflows/satellite_monitor.yml` - GitHub Actions automation
- `config.yaml` - Credentials configuration (local only)
- `requirements.txt` - Python dependencies
