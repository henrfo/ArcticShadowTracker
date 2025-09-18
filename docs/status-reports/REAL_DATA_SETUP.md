# Arctic Shadow Tracker - Real Data Setup Guide

## 🎯 **REAL DATA COLLECTION SETUP**

The Arctic Shadow Tracker is designed to work with **REAL AIS and satellite data** from Arctic waters. Here's how to set it up:

---

## 📡 **AIS Data Sources (Real Vessel Positions)**

### **Option 1: Free AIS Sources** (Limited Coverage)

#### **Norwegian Coastal Administration (Free)**
- **API**: https://www.kystverket.no/navigasjonstjenester/ais/
- **Coverage**: Norwegian Arctic waters, Svalbard region
- **Cost**: Free
- **Setup**:
```bash
# No API key required for basic access
# Limited to Norwegian territorial waters
```

#### **OpenAIS Project (Open Source)**
- **API**: https://www.aishub.net/stations
- **Coverage**: Community-driven AIS receivers
- **Cost**: Free but limited
- **Setup**:
```bash
# Community data - inconsistent coverage
# Better for testing than production
```

### **Option 2: Commercial AIS APIs** (Full Coverage)

#### **MarineTraffic API (Recommended)**
- **Website**: https://www.marinetraffic.com/en/ais-api-services
- **Coverage**: Global, excellent Arctic coverage
- **Cost**: $50-200/month depending on usage
- **Setup**:
```bash
# 1. Sign up for API access
# 2. Get API key
export MARINETRAFFIC_API_KEY="your_api_key_here"

# 3. Test the connection
python -c "
from utils.real_ais_sources import RealAISDataCollector
import os
collector = RealAISDataCollector()
vessels = collector.collect_with_marinetraffic_api(os.getenv('MARINETRAFFIC_API_KEY'))
print(f'Collected {len(vessels)} real vessels')
"
```

#### **VesselFinder API**
- **Website**: https://www.vesselfinder.com/api
- **Coverage**: Global
- **Cost**: $30-100/month
- **Setup**:
```bash
export VESSELFINDER_API_KEY="your_api_key_here"
```

#### **AISHub Premium**
- **Website**: https://www.aishub.net/
- **Coverage**: Good Arctic coverage
- **Cost**: $20-50/month
- **Setup**:
```bash
export AISHUB_USERNAME="your_username"
export AISHUB_PASSWORD="your_password"
```

---

## 🛰️ **Sentinel-1 SAR Data (Real Satellite Imagery)**

### **Option 1: Copernicus Data Space Ecosystem (Free)**
- **Website**: https://dataspace.copernicus.eu/
- **Coverage**: Global, including Arctic
- **Cost**: Free (up to quotas)
- **Setup**:
```bash
# 1. Register for free account
# 2. Get credentials
export COPERNICUS_USERNAME="your_username"
export COPERNICUS_PASSWORD="your_password"

# 3. Test satellite data collection
python -c "
from utils.real_sentinel_collector import RealSentinelCollector
collector = RealSentinelCollector()
products = collector.search_sentinel_products(
    start_date='2025-09-01',
    end_date='2025-09-18',
    arctic_bbox=(5, 69, 35, 82)
)
print(f'Found {len(products)} SAR products')
"
```

### **Option 2: SciHub (ESA)**
- **Website**: https://scihub.copernicus.eu/
- **Coverage**: Complete Sentinel archive
- **Cost**: Free
- **Setup**:
```bash
export SCIHUB_USERNAME="your_username"
export SCIHUB_PASSWORD="your_password"
```

---

## 🚀 **Quick Start with Real Data**

### **Step 1: Set Environment Variables**
Create a `.env` file in the project root:
```bash
# AIS Data
MARINETRAFFIC_API_KEY=your_key_here
VESSELFINDER_API_KEY=your_key_here
AISHUB_USERNAME=your_username
AISHUB_PASSWORD=your_password

# Sentinel SAR Data
COPERNICUS_USERNAME=your_username
COPERNICUS_PASSWORD=your_password
SCIHUB_USERNAME=your_username
SCIHUB_PASSWORD=your_password

# Optional: Email alerts
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

### **Step 2: Test Real Data Collection**
```bash
# Test AIS data collection
python utils/real_ais_sources.py

# Test Sentinel SAR data
python utils/real_sentinel_collector.py

# Run complete surveillance with real data
python scripts/working_surveillance_pipeline.py --mode single
```

### **Step 3: Multi-Day Real Data Operation**
```bash
# Collect 7 days of real historical data
python scripts/working_surveillance_pipeline.py --mode multi-day --days 7

# Set up automated daily collection
python scripts/run_daily_surveillance.py
```

---

## 💰 **Cost Breakdown for Real Data**

### **Minimal Setup** ($50-70/month)
- MarineTraffic Basic API: $50/month
- Copernicus SAR: Free
- **Total**: ~$50/month

### **Professional Setup** ($150-250/month)
- MarineTraffic Premium API: $150/month
- VesselFinder API: $50/month
- AISHub Premium: $30/month
- Copernicus SAR: Free
- **Total**: ~$230/month

### **Enterprise Setup** ($500+/month)
- Multiple AIS providers for redundancy
- Real-time streaming APIs
- Historical data access
- Priority support

---

## 🔧 **API Integration Status**

| Data Source | Integration Status | Test Status | Production Ready |
|-------------|-------------------|-------------|------------------|
| **MarineTraffic API** | ✅ Complete | ✅ Working | ✅ Yes |
| **VesselFinder API** | ✅ Complete | ⚠️ Needs API Key | ✅ Yes |
| **AISHub Premium** | ✅ Complete | ⚠️ Needs Credentials | ✅ Yes |
| **Norwegian Coastal** | 🔄 In Progress | ❌ Testing | ⚠️ Limited |
| **Copernicus SAR** | ✅ Complete | ✅ Working | ✅ Yes |
| **SciHub SAR** | ✅ Complete | ✅ Working | ✅ Yes |

---

## 📊 **Data Quality & Coverage**

### **Arctic AIS Coverage**
- **Svalbard Region**: Excellent (Norwegian Coastal + Commercial APIs)
- **Barents Sea**: Good (Commercial APIs)
- **Kola Peninsula**: Moderate (Commercial APIs only)
- **Franz Josef Land**: Limited (Satellite AIS only)

### **Sentinel-1 SAR Coverage**
- **Repeat Cycle**: 6-12 days depending on location
- **Resolution**: 10m ground resolution
- **Coverage**: Complete Arctic coverage
- **Availability**: 1-3 hour delay from acquisition

---

## ⚡ **Performance Requirements**

### **For Real-Time Operations**
- **AIS Update Rate**: Every 30 minutes
- **SAR Processing**: New images within 6 hours
- **Threat Detection**: Sub-minute response time
- **Data Storage**: 100GB+ for 30-day archive

### **System Resources**
- **CPU**: 4+ cores for SAR processing
- **RAM**: 8GB+ for large SAR scenes
- **Storage**: 500GB+ for operational data
- **Network**: Stable internet for API calls

---

## 🛡️ **Security & Compliance**

### **API Security**
- Environment variables for credentials
- No hardcoded API keys in source code
- Rate limiting to prevent API blocks
- Error handling for failed requests

### **Data Compliance**
- AIS data is publicly broadcast maritime information
- Sentinel SAR data is public domain
- No personal information collected
- GDPR compliant data handling

---

## 🎯 **Next Steps**

1. **Choose Data Plan**: Select AIS provider based on budget and coverage needs
2. **Register for APIs**: Sign up for chosen data sources
3. **Set Environment Variables**: Configure credentials in `.env` file
4. **Test Collection**: Run test scripts to verify data access
5. **Deploy Operations**: Set up automated daily surveillance

**Ready for real Arctic maritime surveillance operations!**