# Auto-Pull AIS Data Setup

The Arctic Shadow Tracker now has automatic synchronization with GitHub Actions vessel data updates.

## Setup Options

### Option 1: Post-Commit Hook (Automatic)
Already installed! After every local commit, the repository will automatically:
- Check for remote updates
- Pull new AIS data from GitHub Actions
- Keep vessel data synced

**How it works:**
- Git hook at `.git/hooks/post-commit` runs after each commit
- No action required from you

**To reinstall/update:**
```bash
./.github/hooks/auto-pull-setup.sh
```

### Option 2: Background Auto-Pull (Manual Start)
For continuous syncing without commits, run the auto-pull script:

```bash
python scripts/auto_pull_ais.py
```

**Features:**
- Checks for remote updates every 5 minutes
- Automatically pulls new vessel data
- Runs in background
- Press Ctrl+C to stop

**Run in background:**
```bash
# macOS/Linux
nohup python scripts/auto_pull_ais.py > auto_pull.log 2>&1 &

# Or use screen/tmux
screen -dmS autopull python scripts/auto_pull_ais.py
```

## How It Works

1. **GitHub Actions** runs every 30 minutes:
   - Collects AIS data from BarentsWatch
   - Processes vessel tracks
   - Commits to `data/vessel_tracks.json` and `outputs/`

2. **Local Repository** auto-syncs:
   - Post-commit hook: Syncs after local commits
   - Auto-pull script: Syncs every 5 minutes (if running)

3. **Conflict Resolution:**
   - Remote data (vessel positions) takes precedence
   - Local code changes preserved
   - Merge conflicts resolved automatically when possible

## Files Modified

- `.git/hooks/post-commit` - Auto-pull after commits
- `scripts/auto_pull_ais.py` - Background auto-pull script
- `.github/workflows/arctic-tracker.yml` - Fixed to include vessel_tracks.json

## Troubleshooting

**If auto-pull fails:**
```bash
# Manually sync
git fetch origin main
git pull origin main

# Check status
git status
```

**To disable post-commit hook:**
```bash
rm .git/hooks/post-commit
```

**To stop background auto-pull:**
```bash
# Find process
ps aux | grep auto_pull_ais.py

# Kill it
kill [PID]
```
