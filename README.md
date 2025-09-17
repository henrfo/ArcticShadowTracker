# ArcticShadowTracker

Advanced maritime surveillance system for Arctic waters using satellite imagery and AIS data to detect dark vessels and monitor critical infrastructure.

## Overview

ArcticShadowTracker combines machine learning with satellite imagery analysis to identify suspicious maritime activities in Arctic regions, with particular focus on:

- Dark vessel detection (ships operating without AIS transponders)
- Submarine cable infrastructure monitoring
- Behavioral pattern analysis in sensitive areas
- Kola Peninsula maritime surveillance

## Project Structure

```
ArcticShadowTracker/
├── README.md
├── requirements.txt
├── data/
│   ├── ais/           # AIS data ingestion
│   ├── satellite/     # Sentinel-1 downloads
│   └── cables/        # Infrastructure locations
├── models/
│   ├── autoencoder.py # Anomaly detection
│   ├── pattern_learner.py
│   └── vessel_classifier.py
├── detection/
│   ├── dark_vessels.py
│   ├── cable_monitor.py
│   └── kola_watcher.py  # Specific area monitoring
├── analysis/
│   ├── patterns.py    # Behavioral analysis
│   └── risk_scoring.py
├── outputs/
│   ├── daily_reports/
│   └── visualizations/
└── notebooks/
    ├── 01_initial_exploration.ipynb
    ├── 02_autoencoder_training.ipynb
    └── 03_pattern_analysis.ipynb
```

## Features

- **Satellite Image Processing**: Automated Sentinel-1 SAR imagery analysis
- **AIS Data Integration**: Real-time vessel tracking and correlation
- **Anomaly Detection**: Deep learning models for identifying unusual patterns
- **Infrastructure Monitoring**: Specialized algorithms for cable protection zones
- **Risk Assessment**: Automated scoring of potential threats

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure data sources and API keys

3. Run initial exploration notebook to understand the data

## Data Sources

- Sentinel-1 SAR imagery via Copernicus Open Access Hub
- AIS data from maritime tracking services
- Submarine cable locations from public databases
- Restricted area definitions

## Security Note

This project is designed for defensive maritime security research and monitoring of public waters in accordance with international law.