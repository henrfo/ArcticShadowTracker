# Arctic Shadow Tracker - Troubleshooting Guide

## 🔧 **Common Issues and Solutions**

### **Issue 1: ModuleNotFoundError: No module named 'detection.advanced_dark_vessels'**

**Problem**: Python can't find the project modules.

**Solutions**:
```bash
# 1. Make sure you're in the correct directory
cd ArcticShadowTracker/notebooks/
jupyter notebook arctic_shadow_tracker.ipynb

# 2. Check project structure exists (NEW naming convention)
ls ../detection/  # Should show: advanced_dark_vessels.py, advanced_cable_monitor.py, basic_vessel_detection.py
ls ../models/     # Should show: advanced_autoencoder.py, basic_autoencoder.py, etc.

# 3. If files are missing, you're in wrong directory
cd /path/to/ArcticShadowTracker/notebooks/

# 4. Check you're using correct import names (updated file structure):
# ✅ CORRECT: from detection.advanced_dark_vessels import DarkVesselDetector
# ❌ OLD: from detection.dark_vessels import DarkVesselDetector
```

### **Issue 2: Missing Dependencies**

**Problem**: `ImportError: No module named 'cv2'` or similar errors.

**Solution**:
```bash
# Install all required packages
pip install -r requirements.txt

# If specific package fails:
pip install opencv-python
pip install rasterio
pip install shapely
pip install geopy
pip install folium
pip install tensorflow
```

### **Issue 3: No Live AIS Data Retrieved**

**Problem**: API returns empty data or connection errors.

**Solutions**:
```python
# 1. Check internet connection
import requests
response = requests.get("http://httpbin.org/ip")
print(response.json())  # Should show your IP

# 2. Try alternative AIS APIs or use demo mode
# See notebooks for fallback data options
```

### **Issue 4: Jupyter Notebook Won't Start**

**Problem**: Jupyter command not found or crashes.

**Solutions**:
```bash
# 1. Install/reinstall Jupyter
pip install jupyter

# 2. Start from correct directory
cd ArcticShadowTracker/notebooks/
jupyter notebook

# 3. If port is busy
jupyter notebook --port 8889
```

### **Issue 5: Satellite Data Processing Errors**

**Problem**: GDAL or rasterio errors when processing SAR imagery.

**Solutions**:
```bash
# On macOS with conda:
conda install rasterio

# On Ubuntu/Linux:
sudo apt-get install gdal-bin libgdal-dev
pip install rasterio

# On Windows:
# Use conda instead of pip for geospatial packages
conda install rasterio
```

---

## 🔍 **Debugging Steps**

### **Step 1: Verify Environment**
```python
# Run this in a notebook cell to check your setup
import sys
import os
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path[:3]}")  # First 3 entries

# Check if project modules exist
project_root = os.path.abspath(os.path.join(os.getcwd(), '..'))
print(f"Project root: {project_root}")
print(f"Detection folder exists: {os.path.exists(os.path.join(project_root, 'detection'))}")
print(f"Models folder exists: {os.path.exists(os.path.join(project_root, 'models'))}")
```

### **Step 2: Test Individual Modules**
```python
# Test each module separately (NEW file names)
try:
    from detection.advanced_dark_vessels import DarkVesselDetector
    print("✅ DarkVesselDetector imported")
except ImportError as e:
    print(f"❌ DarkVesselDetector failed: {e}")

try:
    from detection.advanced_cable_monitor import CableMonitor
    print("✅ CableMonitor imported")
except ImportError as e:
    print(f"❌ CableMonitor failed: {e}")

try:
    from models.advanced_autoencoder import MaritimeAnomalyDetector
    print("✅ MaritimeAnomalyDetector imported")
except ImportError as e:
    print(f"❌ MaritimeAnomalyDetector failed: {e}")

# Test educational modules (simpler versions)
try:
    from detection.basic_vessel_detection import SimpleVesselDetector
    print("✅ SimpleVesselDetector imported")
except ImportError as e:
    print(f"❌ SimpleVesselDetector failed: {e}")

try:
    from models.basic_autoencoder import SimpleAnomalyDetector
    print("✅ SimpleAnomalyDetector imported")
except ImportError as e:
    print(f"❌ SimpleAnomalyDetector failed: {e}")
```

### **Step 3: Check Dependencies**
```python
# Test critical dependencies
missing_packages = []

try:
    import cv2
    print("✅ OpenCV available")
except ImportError:
    missing_packages.append('opencv-python')

try:
    import rasterio
    print("✅ Rasterio available")
except ImportError:
    missing_packages.append('rasterio')

try:
    import shapely
    print("✅ Shapely available")
except ImportError:
    missing_packages.append('shapely')

try:
    import folium
    print("✅ Folium available")
except ImportError:
    missing_packages.append('folium')

if missing_packages:
    print(f"❌ Missing packages: {missing_packages}")
    print("Install with: pip install " + " ".join(missing_packages))
```

---

## 📞 **Getting Help**

### **Educational Support**
- Review [PROGRESSION.md](PROGRESSION.md) for learning path
- Start with simple modules if advanced ones are too complex
- Check example notebooks for working implementations

### **Technical Issues**
- Ensure you're using the correct Python environment
- Verify all files are in the expected locations
- Check that dependencies are properly installed
- Review error messages for specific module names

### **Quick Fix Checklist**
- [ ] In correct directory (`ArcticShadowTracker/notebooks/`)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Python path includes project root
- [ ] All module files exist in detection/ and models/
- [ ] Internet connection available (for live data)

Most issues are resolved by ensuring the correct working directory and having all dependencies installed.