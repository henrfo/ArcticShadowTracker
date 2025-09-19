# ArcticShadowTracker - Development Guide for Claude Code

## Quick Start for Claude Code Assistance

This document provides essential context for Claude Code when working with the ArcticShadowTracker project. It contains key information about the codebase structure, design decisions, and common development tasks.

## Project Context

**ArcticShadowTracker** is a **student research project** focusing on maritime vessel pattern analysis in Arctic waters using machine learning and satellite imagery. This is an **educational project** that demonstrates data science techniques applied to geospatial analysis.

### Key Design Principles
- **Educational Focus**: All code includes extensive documentation for learning purposes
- **Modular Architecture**: Clear separation between detection, analysis, and ML models
- **Defensive Security**: Only uses publicly available data for legitimate research
- **Reproducible Research**: All methods documented and testable with synthetic data

## Codebase Architecture

### Core Module Relationships
```
Detection Layer (Real-time Processing)
├── dark_vessels.py          # Core SAR/AIS correlation engine
├── cable_monitor.py         # Infrastructure proximity monitoring  
└── kola_watcher.py          # Regional surveillance specialization

Analysis Layer (Intelligence)
├── patterns.py              # Behavioral pattern recognition
└── risk_scoring.py          # Multi-dimensional threat assessment

Models Layer (Machine Learning)
├── autoencoder.py           # Anomaly detection neural network
├── pattern_learner.py       # Clustering and classification
└── vessel_classifier.py     # Multi-modal vessel identification
```

### Data Flow Pipeline
1. **Input**: Sentinel-1 SAR imagery + AIS broadcast data
2. **Detection**: `dark_vessels.py` correlates SAR detections with AIS
3. **Analysis**: `patterns.py` performs behavioral analysis
4. **Scoring**: `risk_scoring.py` calculates threat levels
5. **Output**: Structured reports with vessel assessments

## Key Code Patterns

### Error Handling Philosophy
- **Graceful Degradation**: System continues operating with partial data
- **Comprehensive Logging**: All errors logged with context for debugging
- **Fallback Mechanisms**: Default values when data sources unavailable

### Configuration Management
- **Environment Variables**: Sensitive configuration externalized
- **Default Values**: All parameters have sensible defaults for testing
- **Validation**: Input data validated before processing

### Testing Strategy
- **Synthetic Data**: Comprehensive test datasets for all scenarios
- **Unit Tests**: Each module tested independently
- **Integration Tests**: End-to-end pipeline validation

## Common Development Tasks

### Adding New Detection Algorithms
1. **Location**: `detection/` directory
2. **Base Class**: Inherit from common detection interface
3. **Testing**: Add synthetic test cases in `tests/`
4. **Documentation**: Include docstrings and usage examples

### Extending Machine Learning Models
1. **Location**: `models/` directory
2. **Dependencies**: Update `requirements.txt` if needed
3. **Training Data**: Use `create_synthetic_training_data()` pattern
4. **Validation**: Include performance metrics and visualization

### Adding New Analysis Capabilities
1. **Location**: `analysis/` directory
2. **Integration**: Hook into existing risk scoring framework
3. **Notebooks**: Demonstrate capabilities in Jupyter notebooks

## Important Implementation Details

### Coordinate Systems
- **Standard**: WGS84 (latitude, longitude) decimal degrees
- **Projection**: Geographic coordinates, not projected
- **Precision**: 6 decimal places (≈1 meter accuracy)

### Distance Calculations
- **Method**: Haversine formula via `geopy.distance.geodesic()`
- **Units**: Kilometers for consistency across modules
- **Thresholds**: Configurable via class initialization

### Time Handling
- **Format**: ISO 8601 strings (`YYYY-MM-DDTHH:MM:SS`)
- **Timezone**: UTC assumed unless specified
- **Tolerance**: 30-minute windows for SAR/AIS correlation

### Performance Considerations
- **Memory**: Large SAR images processed in chunks
- **CPU**: NumPy vectorized operations preferred
- **I/O**: Lazy loading of satellite imagery data

## Data Sources and APIs

### Satellite Imagery
- **Primary**: Sentinel-1 SAR via Copernicus Open Access Hub
- **Alternative**: Alaska Satellite Facility (ASF) API
- **Format**: GeoTIFF or .SAFE product format
- **Processing**: Rasterio for reading, OpenCV for analysis

### AIS Data Sources
- **Norwegian**: Kystverket/BarentsWatch API
- **International**: AISHub, MarineTraffic (rate limited)
- **Format**: JSON or NMEA 0183 sentence parsing
- **Real-time**: WebSocket or REST API polling

### Infrastructure Data
- **Cables**: TeleGeography submarine cable database
- **Ports**: OpenStreetMap or World Port Index
- **Format**: GeoJSON or Shapefile

## Machine Learning Pipeline

### Autoencoder Training
- **Architecture**: 10 → 5 → 10 fully connected layers
- **Loss Function**: Mean Squared Error reconstruction
- **Threshold**: 95th percentile of training reconstruction errors
- **Features**: Normalized vessel behavioral characteristics

### Pattern Recognition
- **Clustering**: DBSCAN for density-based grouping
- **Classification**: Random Forest for vessel type prediction
- **Validation**: Cross-validation with synthetic datasets

### Risk Scoring Components
- **Weights**: Configurable in `RiskScorer.__init__()`
- **Factors**: Vessel, behavioral, location, temporal, intelligence
- **Output**: 0-10 scale with categorical risk levels

## Common Issues and Solutions

### Large File Handling
```python
# Good: Process SAR images in chunks
with rasterio.open(sar_file) as src:
    for window in src.block_windows():
        data = src.read(window=window)
        # Process chunk
```

### Memory Management
```python
# Good: Use generators for large datasets
def process_vessels():
    for vessel_batch in batch_generator(vessel_list, batch_size=100):
        yield process_batch(vessel_batch)
```

### Geographic Calculations
```python
# Good: Use geopy for accurate distance calculations
from geopy.distance import geodesic
distance_km = geodesic(pos1, pos2).kilometers
```

## Testing Patterns

### Synthetic Data Generation
```python
# Pattern: Create realistic test scenarios
def create_test_vessel_track(behavior_type='normal'):
    # Generate realistic movement patterns
    # Include edge cases and anomalies
    # Return structured data for testing
```

### Mock API Responses
```python
# Pattern: Mock external data sources
@pytest.fixture
def mock_ais_data():
    return {
        'vessels': [test_vessel_data],
        'timestamp': datetime.now().isoformat()
    }
```

## Jupyter Notebook Guidelines

### Notebook Structure
1. **Introduction**: Clear explanation of objectives
2. **Data Loading**: Demonstrate data source access
3. **Analysis**: Step-by-step methodology
4. **Visualization**: Clear charts and maps
5. **Conclusions**: Summary of findings

### Code Style in Notebooks
- **Imports**: All imports in first cell
- **Configuration**: Set random seeds for reproducibility
- **Documentation**: Markdown explanations between code cells
- **Clean Output**: Clear outputs before committing

## Security and Ethics Notes

### Educational Project Scope
- **Purpose**: Academic research and learning
- **Data**: Only publicly available sources
- **Output**: Research findings, not operational intelligence
- **Compliance**: International maritime law and research ethics

### Sensitive Information
- **No Classified Data**: All sources are public/open
- **No Personal Data**: AIS data is publicly broadcast
- **Anonymization**: Vessel identifiers used only for correlation

## Performance Optimization

### Satellite Image Processing
- **Preprocessing**: Cache processed imagery chunks
- **Algorithms**: Use OpenCV optimized functions
- **Memory**: Process large images in tiles

### Database Operations
- **Indexing**: Geographic indices for spatial queries
- **Caching**: Cache frequently accessed reference data
- **Batch Processing**: Group operations for efficiency

## Future Development Areas

### Integration Opportunities
- **Web Interface**: Flask/Django dashboard for visualization
- **Real-time Processing**: Apache Kafka for streaming data
- **Cloud Deployment**: Docker containers for scalability

### Research Extensions
- **Multi-sensor Fusion**: Optical + SAR imagery combination
- **Temporal Analysis**: Long-term trend identification
- **Predictive Modeling**: Forecast vessel behavior patterns

## Troubleshooting Guide

### Common Import Errors
```bash
# Solution: Install all dependencies
pip install -r requirements.txt

# For geospatial libraries on macOS:
brew install gdal
pip install --no-binary rasterio rasterio
```

### Memory Issues with Large Images
```python
# Solution: Process in chunks
import rasterio.windows
for window in rasterio.windows.Window.from_bounds(...):
    data = src.read(window=window)
```

### Coordinate System Mismatches
```python
# Solution: Always validate coordinate systems
import pyproj
# Ensure WGS84 (EPSG:4326) for lat/lon data
```

## Code Quality Standards

### Documentation Requirements
- **Module Level**: Purpose, usage examples, dependencies
- **Class Level**: Responsibilities, key methods, usage patterns
- **Method Level**: Parameters, return values, side effects
- **Complex Logic**: Inline comments explaining algorithms

### Testing Requirements
- **Coverage**: Aim for >80% test coverage
- **Edge Cases**: Test boundary conditions and error cases
- **Integration**: Test module interactions
- **Performance**: Benchmark critical path operations

This guide provides Claude Code with comprehensive context for effective assistance with the ArcticShadowTracker project, enabling informed suggestions and maintaining consistency with the project's educational goals and technical architecture.