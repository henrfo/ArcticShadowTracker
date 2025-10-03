# Arctic Shadow Tracker

Automated Arctic maritime intelligence system tracking Russian/Chinese vessels with three-tier historical analysis.

## Features

- **Automated Collection**: 30-minute AIS data updates via GitHub Actions
- **Three-Tier Tracking**: Real-time (0-2hr), Tactical (2-48hr), Strategic (2-7d)
- **Focus Mode Dashboard**: Interactive map with click-to-focus vessel tracking
- **Risk-Based Visualization**: Color-coded by vessel country and behavior
- **Auto-Deployment**: GitHub Pages hosting with automatic updates

## Quick Start

### 1. Configure API Credentials

Add GitHub Secret (Settings → Secrets and variables → Actions):
- Name: `BARENTSWATCH_CLIENT_SECRET`
- Value: Your BarentsWatch API client secret

Get credentials at: https://www.barentswatch.no/

### 2. Enable GitHub Pages

Settings → Pages:
- Source: Deploy from branch
- Branch: `gh-pages`
- Path: `/` (root)

### 3. Run First Collection

Actions tab → "Arctic AIS Monitor" → Run workflow

Dashboard will be available at:
```
https://<username>.github.io/ArcticShadowTracker/
```

## Local Development

Create `config.yaml`:
```yaml
barentswatch:
  client_id: "your-email:ClientName"
  client_secret: "your-secret-here"
```

Install and run:
```bash
pip install -r requirements.txt
python scripts/collect_ais.py
open outputs/index.html
```

## How It Works

### Data Collection
- Fetches all AIS data from BarentsWatch API
- Filters to Arctic region (65-82°N, 0-40°E)
- Focuses on Russian/Chinese vessels (~30-40 active)
- Saves snapshots every 30 minutes

### Three-Tier Tracking
Each vessel maintains three levels of history:

**Tier 1 - Real-time (0-2 hours)**
- Every 30-minute update
- ~4 data points
- Shows: Current detailed movement

**Tier 2 - Tactical (2-48 hours)**
- Sampled every 30 minutes
- ~92 data points
- Shows: Movement patterns and routes

**Tier 3 - Strategic (2-7 days)**
- Events only: turns >45°, speed changes >5kts, stops
- ~10-20 data points
- Shows: Long-term behavior patterns

### Map Visualization
- **Red vessels**: Russia/China (high risk) - Full tracks visible
- **Gray vessels**: Norwegian (low risk) - Strategic tier only
- **Solid lines**: Real-time track (0-2hr)
- **Dashed lines**: Tactical track (2-48hr)
- **Dotted lines**: Strategic track (2-7d)
- **Click vessel**: Focus mode (shows all tiers)

## Project Structure

```
ArcticShadowTracker/
├── scripts/
│   └── collect_ais.py          # Main collection pipeline
├── src/
│   ├── mmsi_country_reference.py  # MMSI to country mapping
│   ├── ais_ship_types.py          # Ship type decoder
│   ├── track_manager.py           # Three-tier tracking logic
│   └── map_generator.py           # Interactive map generation
├── data/
│   ├── snapshots/              # Raw 30-min snapshots (7-day retention)
│   └── vessel_tracks.json      # Processed three-tier tracks
├── outputs/
│   └── index.html              # GitHub Pages dashboard
└── .github/workflows/
    └── arctic_monitor.yml      # Automation configuration
```

## Data Retention

- **Snapshots**: 7 days (auto-cleanup)
- **Vessel Tracks**: 7 days with three-tier downsampling
- **Storage**: ~20MB per week (well under GitHub limits)

## Automation

GitHub Actions runs every 30 minutes:
1. Fetch AIS data from BarentsWatch
2. Save snapshot to `data/snapshots/`
3. Process three-tier tracks
4. Generate interactive map
5. Commit data and outputs
6. Deploy to GitHub Pages

## Customization

### Change Coverage Area
Edit `scripts/collect_ais.py`:
```python
ARCTIC_REGION = {
    'lat_min': 65.0,
    'lat_max': 82.0,
    'lon_min': 0.0,
    'lon_max': 40.0
}
```

### Adjust Tracking Parameters
Edit `src/track_manager.py`:
- Tier durations (currently 2hr/48hr/7d)
- Strategic event thresholds (course/speed)
- Sampling intervals (currently 30min)

### Track More Countries
Edit `scripts/collect_ais.py` - line 118:
```python
if country in ['Russia', 'China', 'YourCountry']:
```

## Troubleshooting

### Workflow Fails
- Verify `BARENTSWATCH_CLIENT_SECRET` secret is set
- Check GitHub Actions logs for errors
- Test API credentials locally with `config.yaml`

### Dashboard Not Updating
- Ensure `gh-pages` branch exists
- Check GitHub Pages deployment status
- Allow 1-2 minutes after workflow completes

### No Vessels Showing
- Verify vessels are currently in Arctic region
- Check `data/snapshots/` for recent files
- Review most recent snapshot JSON

## Technical Details

- **Language**: Python 3.9+
- **API**: BarentsWatch AIS API
- **Map Library**: Folium (Leaflet.js)
- **Automation**: GitHub Actions
- **Hosting**: GitHub Pages
- **Data Format**: JSON snapshots + processed tracks

## Security

- API client secret stored in GitHub Secrets (encrypted)
- Client ID can be public (used in OAuth flow)
- No sensitive vessel data stored
- All data publicly accessible via AIS already

## License

This project processes publicly available AIS data from BarentsWatch.
Vessel tracking data is public information transmitted by ships.

## Credits

- AIS data provided by BarentsWatch (Norwegian Coastal Administration)
- MMSI country mapping from ITU-R M.1371 standard
- Ship type codes from NOAA Marine Cadastre 2018
