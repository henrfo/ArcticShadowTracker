# 🛰️ Arctic Shadow Tracker - Free GitHub Deployment

Simple 5-minute setup to run 24/7 on GitHub Actions - **completely free!**

## 🚀 Quick Setup

### 1. Push to GitHub
```bash
git add .
git commit -m "Initial Arctic Shadow Tracker"
git push origin main
```

### 2. Configure API Secret
1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `BARENTSWATCH_CLIENT_SECRET`
5. Value: `Xw5yCEXT5gMi5PJEKEW6` (your BarentsWatch secret)

### 3. Enable Actions (if needed)
1. Go to Actions tab in your repo
2. Click "I understand my workflows, go ahead and enable them"

### 4. Test Run
1. Go to Actions tab
2. Click "Arctic Shadow Tracker" workflow
3. Click "Run workflow" → "Run workflow"
4. Watch it collect Arctic vessel data!

## 📊 What Happens

- **Runs every 30 minutes** automatically
- **Collects foreign vessel data** from BarentsWatch API
- **Filters out buoys** and Norwegian vessels
- **Saves data** to CSV files in the repo
- **Creates interactive maps** with vessel positions
- **Commits data back** to GitHub automatically

## 📁 Output Files

- `arctic_intelligence/vessel_positions.csv` - All vessel tracking data
- `arctic_intelligence/cable_alerts.csv` - Infrastructure alerts
- `arctic_intelligence/dark_vessels.csv` - AIS turn-off events  
- `arctic_intelligence/arctic_dashboard_latest.html` - Interactive map

## 💰 Cost

**$0/month** - Completely free on GitHub!

## 🔧 Manual Run

To run manually:
```bash
BARENTSWATCH_CLIENT_SECRET="Xw5yCEXT5gMi5PJEKEW6" python arctic_shadow_streamer.py test
```

That's it! Your Arctic surveillance system is now running 24/7 for free. 🎯