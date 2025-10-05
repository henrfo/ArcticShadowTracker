# Live AIS Data Sync Setup

The Arctic Shadow Tracker automatically synchronizes with GitHub Actions vessel data updates **without creating commits to the main branch**.

## How It Works

### GitHub Actions (Automated)
- **Runs every 30 minutes** via `.github/workflows/arctic_monitor.yml`
- Collects AIS data from BarentsWatch API
- Processes vessel tracks and generates map
- **Deploys to GitHub Pages ONLY** (no commits to main branch!)
- GitHub Pages URL: https://henrfo.github.io/ArcticShadowTracker

### Local Development (Your Choice)

You have multiple options to get fresh data locally:

## Option 1: Download On-Demand (Recommended)

Download latest data whenever you need it:

```bash
python scripts/download_live_data.py
```

**What it does:**
- Downloads `vessel_tracks.json` from GitHub Pages
- Downloads latest map HTML
- No git operations needed
- Takes ~2 seconds

**When to use:**
- Before starting local development
- When you want latest vessel positions
- After GitHub Actions has run (every 30 min)

## Option 2: Auto-Download in Background

Keep data synced continuously:

```bash
# Run in terminal (Ctrl+C to stop)
python scripts/download_live_data.py --watch
```

Or run in background:
```bash
# macOS/Linux
nohup python scripts/download_live_data.py --watch > download.log 2>&1 &

# Or use screen
screen -dmS datadownload python scripts/download_live_data.py --watch
```

**Features:**
- Downloads fresh data every 30 minutes
- Runs silently in background
- No git commits or conflicts

**To stop:**
```bash
ps aux | grep download_live_data
kill [PID]
```

## Option 3: Cron Job (Set and Forget)

Schedule automatic downloads:

```bash
# Edit crontab
crontab -e

# Add this line (downloads every 30 minutes)
*/30 * * * * cd /Users/henrikformoe/Desktop/Desktop_M2/Projects_25/ArcticShadowTracker && python scripts/download_live_data.py
```

## GitHub Actions Workflow

**Automated commits removed!**

The workflow now:
1. ✅ Collects AIS data (every 30 min)
2. ✅ Processes vessel tracks
3. ✅ Generates map visualization
4. ✅ Deploys to GitHub Pages
5. ❌ ~~No longer commits to main branch~~ (keeps history clean!)

**Weekly shadow fleet updates:**
- `.github/workflows/shadow-fleet-update.yml` still commits weekly (Sundays)
- This is intentional - shadow fleet database updates are important enough to track in git

## Benefits of This Approach

✅ **Clean main branch** - only manual code commits, no automated spam
✅ **Clean contribution graph** - automated data collection doesn't clutter your GitHub profile
✅ **No merge conflicts** - HTTP download instead of git pull
✅ **Faster sync** - direct download is quicker than git operations
✅ **Automation continues** - GitHub Actions still runs every 30 min
✅ **GitHub Pages stays updated** - live dashboard updates every 30 min

## Data Sources

- **GitHub Pages (Live):** https://henrfo.github.io/ArcticShadowTracker/
  - Updated every 30 minutes by GitHub Actions
  - Always has latest vessel positions
  - No authentication required

- **Local (Development):**
  - `data/vessel_tracks.json` - Downloaded from GitHub Pages
  - `outputs/index.html` - Downloaded from GitHub Pages
  - Use `download_live_data.py` to sync

## Files Modified

**Removed:**
- `.github/workflows/arctic-tracker.yml` (duplicate workflow deleted)
- `.git/hooks/post-commit` (no longer needed - no git sync required)

**Modified:**
- `.github/workflows/arctic_monitor.yml` - Removed commit step, deploys to gh-pages only

**Added:**
- `scripts/download_live_data.py` - Download data from GitHub Pages

## Troubleshooting

**Data not updating locally:**
```bash
# Download latest data manually
python scripts/download_live_data.py

# Check GitHub Pages is working
curl https://henrfo.github.io/ArcticShadowTracker/vessel_tracks.json
```

**GitHub Actions failing:**
```bash
# Check workflow runs on GitHub
# Go to: https://github.com/henrfo/ArcticShadowTracker/actions

# Manually trigger workflow
# Go to Actions → Arctic AIS Monitor → Run workflow
```

**Need historical data:**
```bash
# Historical snapshots are no longer committed to main branch
# Use GitHub Pages or run collect_ais.py locally with API credentials
```

## Local Development with API

If you want to collect data locally (optional):

1. Add BarentsWatch credentials to `config.yaml`:
```yaml
barentswatch:
  client_id: "your-email:ArcticShadowTracker"
  client_secret: "your-secret-here"
```

2. Run data collection:
```bash
python scripts/collect_ais.py
```

This generates fresh data without relying on GitHub Pages.
