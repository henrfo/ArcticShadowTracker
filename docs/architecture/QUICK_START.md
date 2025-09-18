# Arctic Shadow Tracker - Quick Start Guide

## 🚀 Get Started in 5 Steps

### 1. Setup Real Data
```bash
python setup_real_data.py
```

### 2. Install Dependencies
```bash
pip install -r config/requirements.txt
```

### 3. Download Satellite Data
```bash
python sentinel_downloader.py
```
Choose option 1 for sample data or option 2 for real Copernicus data.

### 4. Start Automated Pipeline (Optional - for 24/7 operations)
```bash
python data_pipeline.py
```
Choose option 2 for continuous surveillance every 30 minutes.

### 5. Open Simplified Operational Dashboard
```bash
jupyter notebook notebooks/operational/arctic_surveillance_dashboard.ipynb
```

**Run All Cells** - The dashboard will:
- ✅ Load simplified detection systems (no more basic/advanced split!)
- ✅ Collect real AIS data from Arctic waters 
- ✅ Process satellite imagery automatically
- ✅ Monitor 4 submarine cables for threats  
- ✅ Detect dark vessels near cables
- ✅ Generate operational intelligence reports

**Fixed Issues:**
- ✅ No more import errors or variable scope problems
- ✅ Self-contained cells that work independently  
- ✅ Simplified code that maritime analysts can understand
- ✅ Automatic sample data creation if needed

## 📁 Clean Project Structure

```
ArcticShadowTracker/
├── 📓 notebooks/operational/     ← START HERE
│   └── operational_arctic_surveillance.ipynb
├── 🔧 detection/               # Core algorithms  
├── 🧠 models/                  # ML models
├── 📊 analysis/                # Analysis tools
├── 📋 docs/                    # All documentation
├── ⚙️ config/                  # Settings & requirements
├── 🧪 scripts/                 # Test scripts
└── 📤 outputs/                 # Reports & results
```

## 🎯 Mission
Detect dark vessels (AIS-off) near submarine cables in Arctic waters.

## 📊 What You'll See
- Live AIS vessel tracking
- Cable proximity alerts
- Threat level assessments  
- Operational intelligence reports

**That's it! One notebook runs the entire Arctic surveillance system.**

---
*Ready for Arctic maritime surveillance operations.*