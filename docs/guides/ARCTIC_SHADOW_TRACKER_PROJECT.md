# Arctic Shadow Tracker Project Documentation

## Overview

The Arctic Shadow Tracker is a maritime surveillance system designed to detect "dark vessels" - ships that have turned off their AIS transponders - in Arctic waters around Norway and Svalbard. The system combines real-time AIS data with satellite imagery to identify vessels that may be operating covertly near critical infrastructure.

## Project Evolution

### Initial Development
The project began with basic satellite imagery fetching capabilities in `barentswatch_test_v1.ipynb`, which focused on:
- Optimized Sentinel-1 SAR and Sentinel-2 optical imagery retrieval
- Enhanced contrast settings for vessel detection
- High-resolution imagery (2500x2000 pixels) for 60m+ vessel detection
- Arctic region coverage (Svalbard, Northern Norway, Kola Peninsula, Barents Sea)

### MVP Development  
The system evolved into a comprehensive MVP in `barentswatch_test_v2.ipynb` with:
- **AIS Temporal Tracking**: Monitors vessel positions over time to detect when ships disappear
- **Submarine Cable Monitoring**: Alerts when vessels approach critical Norwegian infrastructure
- **Dark Vessel Detection**: Identifies vessels that have gone silent for 2-48 hours
- **Satellite Verification**: Uses SAR imagery to potentially spot vessels without AIS
- **Intelligence Data Bank**: Builds historical database for pattern analysis

## Technical Architecture

### Core Components

#### 1. AIS Data Collection (`collect_ais_data()`)
- **Source**: BarentsWatch Norwegian Government API
- **Coverage**: Arctic regions above 65°N
- **Filtering**: Excludes Norwegian vessels (MMSI 257-259, name patterns)
- **Data**: Position, speed, course, vessel type, timestamp

#### 2. Cable Proximity Monitoring (`check_cable_proximity()`)
- **Cables Tracked**:
  - Svalbard Undersea Cable System (10km alert zone)
  - Lofoten-Vesterålen Cable (5km alert zone)  
  - Norway-UK Cable Arctic Section (8km alert zone)
- **Algorithm**: Point-to-line distance calculation using Haversine formula
- **Alerts**: Real-time proximity warnings for vessels near critical infrastructure

#### 3. Dark Vessel Detection (`detect_dark_vessels()`)
- **Method**: Temporal analysis comparing current vs historical AIS positions
- **Threshold**: Vessels missing 2-48 hours after regular reporting
- **Persistence**: Maintains 100-position history per vessel
- **Storage**: JSON-based historical database

#### 4. Satellite Verification (`fetch_satellite_imagery()`)
- **Platform**: Copernicus Sentinel-1 SAR via Sentinel Hub
- **Processing**: Enhanced contrast evalscript optimized for vessel detection
- **Resolution**: 1500x1200 pixels for detailed analysis
- **Enhancement**: Aggressive dB normalization (val + 25)/20 for ship visibility

#### 5. Intelligence Database (`save_intelligence_data()`)
- **Format**: JSON files for easy processing and analysis
- **Structure**: Daily collections, separate dark vessel and alert databases
- **Persistence**: Cumulative data building over time
- **Files**: 
  - `ais_history.json` - Historical vessel tracking
  - `intelligence_YYYYMMDD.json` - Daily intelligence summaries
  - `dark_vessels.json` - Database of vessels that went dark
  - `cable_alerts.json` - Cable proximity incidents

### Data Flow

```
AIS API → Filter (Non-Norwegian) → Historical Comparison → Dark Vessel Detection
    ↓                                                            ↓
Cable Monitoring → Proximity Alerts                    Satellite Verification
    ↓                                                            ↓
Intelligence Database ← Summary Reports ← Visualization Maps
```

### Arctic Regions Monitored

1. **Svalbard Waters** (10-35°E, 76-81°N) - Strategic Arctic location
2. **Northern Norway Coast** (15-32°E, 68-71.5°N) - Heavy maritime traffic
3. **Central Barents Sea** (20-40°E, 72-76°N) - Critical shipping corridor

## Key Technologies Used

### APIs and Data Sources
- **BarentsWatch API**: Official Norwegian government AIS data
- **Sentinel Hub API**: Copernicus satellite imagery access
- **OAuth 2.0**: Secure API authentication

### Python Libraries
- **requests**: HTTP API interactions
- **sentinelhub**: Satellite imagery processing
- **folium**: Interactive map generation
- **matplotlib**: Satellite image visualization
- **yaml**: Configuration file management
- **json**: Data persistence and interchange

### Processing Techniques
- **Haversine Formula**: Great-circle distance calculations
- **Point-to-Line Distance**: Cable proximity algorithms
- **Temporal Analysis**: Time-series vessel tracking
- **SAR Image Enhancement**: Vessel detection optimization

## Configuration Management

### Security Model
- **Credentials**: Stored in `config.yaml` (not committed to version control)
- **API Keys**: Environment variable support
- **Access Control**: OAuth 2.0 with scope-limited permissions

### Configuration Structure
```yaml
sentinel_hub:
  client_id: "your-client-id"
  client_secret: "your-client-secret"
  
barentswatch:
  client_id: "your-client-id"
  client_secret: "your-client-secret" 
  scope: "ais"
```

## Intelligence Output

### Real-time Alerts
- **Cable Proximity**: Immediate alerts when vessels approach infrastructure
- **Dark Vessels**: Detection of vessels that stop AIS transmission
- **Foreign Vessels**: Focus on non-Norwegian ships in Norwegian waters

### Data Products
- **Interactive Maps**: HTML visualization with vessel positions and alerts
- **Intelligence Summaries**: JSON reports with vessel statistics
- **Historical Analysis**: Time-series data for pattern recognition
- **SAR Imagery**: High-resolution satellite verification

### Operational Metrics
- **Coverage**: 1,500+ vessels tracked simultaneously
- **Filtering**: ~900+ Norwegian vessels filtered per collection
- **Infrastructure**: 3 critical submarine cable systems monitored
- **Persistence**: 100 historical positions maintained per vessel

## Deployment Architecture

### MVP Characteristics
- **Single Notebook Operation**: Complete system in one Jupyter notebook
- **Minimal Dependencies**: Core Python libraries only
- **Local Storage**: JSON files for data persistence
- **Manual Execution**: Run-on-demand intelligence collection
- **Simple Configuration**: YAML file for credentials

### Scalability Considerations
- **Data Growth**: JSON files will grow over time - consider database migration
- **API Limits**: BarentsWatch and Sentinel Hub have rate limiting
- **Processing Power**: SAR imagery processing is computationally intensive
- **Storage**: Satellite images and historical data require disk space management

## Use Cases

### Primary Applications
1. **Maritime Domain Awareness**: Understanding vessel activity in Norwegian Arctic waters
2. **Infrastructure Protection**: Monitoring submarine cable security
3. **Dark Vessel Detection**: Identifying potentially suspicious vessel behavior
4. **Intelligence Collection**: Building historical patterns of maritime activity

### Secondary Applications
1. **Search and Rescue**: Vessel position tracking for emergency response
2. **Environmental Monitoring**: Shipping traffic impact assessment
3. **Border Security**: Monitoring vessel activity near territorial boundaries
4. **Research**: Arctic shipping pattern analysis

## Limitations and Considerations

### Technical Limitations
- **AIS Dependency**: System relies on vessels voluntarily transmitting AIS
- **Weather Impact**: Arctic conditions affect satellite imagery availability
- **Processing Lag**: Real-time detection limited by API response times
- **False Positives**: Legitimate reasons for AIS gaps (equipment failure, maintenance)

### Operational Constraints
- **Norwegian Vessel Filtering**: May miss relevant Norwegian government/military vessels
- **Geographic Coverage**: Limited to Arctic regions above 65°N
- **Manual Operation**: Requires human intervention to run collections
- **Storage Management**: No automated cleanup of historical data

### Legal and Ethical Considerations
- **Data Privacy**: AIS data is public but vessel tracking raises privacy concerns
- **Territorial Waters**: International law governs surveillance in different maritime zones
- **Data Retention**: Consider policies for historical data management
- **Purpose Limitation**: Ensure use aligns with legitimate maritime security purposes

## Future Development Directions

### Short-term Enhancements (1-3 months)
- **Automated Scheduling**: Cron job or scheduler for regular collections
- **Alert System**: Email/SMS notifications for critical alerts
- **Database Migration**: Move from JSON to proper database (PostgreSQL/MongoDB)
- **Performance Optimization**: Faster processing and reduced memory usage

### Medium-term Additions (3-12 months)
- **Machine Learning**: Anomaly detection for vessel behavior patterns
- **Advanced Analytics**: Predictive modeling for vessel movements
- **Multi-source Integration**: Additional satellite providers and AIS sources
- **Real-time Dashboard**: Web interface for live monitoring

### Long-term Vision (1+ years)
- **Automated Dark Vessel Classification**: AI-powered threat assessment
- **Integration with Maritime Authorities**: Data sharing with relevant agencies
- **Expanded Coverage**: Global maritime surveillance capabilities
- **Advanced Satellite Processing**: Real-time vessel detection from SAR imagery

## Conclusion

The Arctic Shadow Tracker represents a successful proof-of-concept for maritime surveillance in the Arctic region. The system demonstrates the feasibility of combining multiple data sources (AIS and satellite imagery) to create actionable maritime intelligence. The MVP approach allowed for rapid development while maintaining focus on core functionality.

The project showcases the power of combining government APIs, commercial satellite services, and open-source tools to create sophisticated surveillance capabilities with minimal resources. The modular design and simple architecture make it an excellent foundation for future enhancements and operational deployment.

**Key Success Factors:**
1. **Simple MVP Focus**: Avoided over-engineering while delivering working functionality
2. **Real Data Sources**: Used authoritative government and commercial APIs
3. **Modular Design**: Clean separation of concerns enables easy enhancement
4. **Practical Application**: Addresses real-world maritime security challenges
5. **Scalable Architecture**: Foundation supports future operational deployment

The Arctic Shadow Tracker demonstrates that effective maritime surveillance systems can be developed quickly using modern APIs and cloud services, providing valuable capabilities for maritime domain awareness and infrastructure protection.