#!/usr/bin/env python3
"""
Arctic Shadow Tracker - Simple Streaming System
Based on barentswatch_test_v2.ipynb notebook

Continuously monitors Arctic waters for foreign vessels, dark vessel detection,
and submarine cable proximity monitoring.
"""

import yaml
import requests
import json
import pandas as pd
import folium
import time
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from math import radians, cos, sin, asin, sqrt

# Configuration
DATA_DIR = Path('arctic_intelligence')
DATA_DIR.mkdir(parents=True, exist_ok=True)

# MMSI to Country mapping (International standard)
MMSI_COUNTRY_MAP = {
    '201': 'Albania', '202': 'Andorra', '203': 'Austria', '204': 'Azores', '205': 'Belgium',
    '206': 'Belarus', '207': 'Bulgaria', '208': 'Vatican', '209': 'Cyprus', '210': 'Cyprus',
    '211': 'Germany', '212': 'Cyprus', '213': 'Georgia', '214': 'Moldova', '215': 'Malta',
    '216': 'Armenia', '218': 'Germany', '219': 'Denmark', '220': 'Denmark', '224': 'Spain',
    '225': 'Spain', '226': 'France', '227': 'France', '228': 'France', '229': 'Malta',
    '230': 'Finland', '231': 'Faroe Islands', '232': 'United Kingdom', '233': 'United Kingdom',
    '234': 'United Kingdom', '235': 'United Kingdom', '236': 'Gibraltar', '237': 'Greece',
    '238': 'Croatia', '239': 'Greece', '240': 'Greece', '241': 'Greece', '242': 'Morocco',
    '243': 'Hungary', '244': 'Netherlands', '245': 'Netherlands', '246': 'Netherlands',
    '247': 'Italy', '248': 'Malta', '249': 'Malta', '250': 'Ireland', '251': 'Iceland',
    '252': 'Liechtenstein', '253': 'Luxembourg', '254': 'Monaco', '255': 'Madeira',
    '256': 'Malta', '257': 'Norway', '258': 'Norway', '259': 'Norway', '261': 'Poland',
    '262': 'Montenegro', '263': 'Portugal', '264': 'Romania', '265': 'Sweden', '266': 'Sweden',
    '267': 'Slovakia', '268': 'San Marino', '269': 'Switzerland', '270': 'Czech Republic',
    '271': 'Turkey', '272': 'Ukraine', '273': 'Russia', '274': 'North Macedonia',
    '275': 'Latvia', '276': 'Estonia', '277': 'Lithuania', '278': 'Slovenia',
    '301': 'Anguilla', '303': 'Alaska', '304': 'Antigua and Barbuda', '305': 'Antigua and Barbuda',
    '306': 'Netherlands Antilles', '307': 'Aruba', '308': 'Bahamas', '309': 'Bahamas',
    '310': 'Bermuda', '311': 'Bahamas', '312': 'Belize', '314': 'Barbados', '316': 'Canada',
    '319': 'Cayman Islands', '321': 'Costa Rica', '323': 'Cuba', '325': 'Dominica',
    '327': 'Dominican Republic', '329': 'Guadeloupe', '330': 'Grenada', '331': 'Greenland',
    '332': 'Guatemala', '334': 'Honduras', '336': 'Haiti', '338': 'United States',
    '339': 'Jamaica', '341': 'Saint Kitts and Nevis', '343': 'Saint Lucia',
    '345': 'Mexico', '347': 'Martinique', '348': 'Montserrat', '350': 'Nicaragua',
    '351': 'Panama', '352': 'Panama', '353': 'Panama', '354': 'Panama', '355': 'Panama',
    '356': 'Panama', '357': 'Panama', '358': 'Puerto Rico', '359': 'El Salvador',
    '361': 'Saint Pierre and Miquelon', '362': 'Trinidad and Tobago',
    '364': 'Turks and Caicos Islands', '366': 'United States', '367': 'United States',
    '368': 'United States', '369': 'United States', '370': 'Panama', '371': 'Panama',
    '372': 'Panama', '373': 'Panama', '374': 'Panama', '375': 'Saint Vincent and the Grenadines',
    '376': 'Saint Vincent and the Grenadines', '377': 'Saint Vincent and the Grenadines',
    '378': 'British Virgin Islands', '379': 'United States Virgin Islands',
    '401': 'Afghanistan', '403': 'Saudi Arabia', '405': 'Bangladesh', '408': 'Bahrain',
    '410': 'Bhutan', '412': 'China', '413': 'China', '414': 'China', '416': 'Taiwan',
    '417': 'Sri Lanka', '419': 'India', '422': 'Iran', '423': 'Azerbaijan', '425': 'Iraq',
    '428': 'Israel', '431': 'Japan', '432': 'Japan', '434': 'Turkmenistan', '436': 'Kazakhstan',
    '437': 'Uzbekistan', '438': 'Jordan', '440': 'South Korea', '441': 'South Korea',
    '443': 'Palestine', '445': 'North Korea', '447': 'Kuwait', '450': 'Lebanon',
    '451': 'Kyrgyzstan', '453': 'Macao', '455': 'Maldives', '457': 'Mongolia',
    '459': 'Nepal', '461': 'Oman', '463': 'Pakistan', '466': 'Qatar', '468': 'Syria',
    '470': 'United Arab Emirates', '472': 'Tajikistan', '473': 'Yemen', '475': 'Yemen',
    '477': 'Hong Kong', '478': 'Bosnia and Herzegovina', '501': 'Adelie Land',
    '503': 'Australia', '506': 'Myanmar', '508': 'Brunei', '510': 'Micronesia',
    '511': 'Palau', '512': 'New Zealand', '514': 'Cambodia', '515': 'Cambodia',
    '516': 'Christmas Island', '518': 'Cook Islands', '520': 'Fiji', '523': 'Cocos Islands',
    '525': 'Indonesia', '529': 'Kiribati', '531': 'Laos', '533': 'Malaysia', '536': 'Northern Mariana Islands',
    '538': 'Marshall Islands', '540': 'New Caledonia', '542': 'Niue', '544': 'Nauru',
    '546': 'French Polynesia', '548': 'Philippines', '553': 'Papua New Guinea',
    '555': 'Pitcairn Island', '557': 'Solomon Islands', '559': 'American Samoa',
    '561': 'Samoa', '563': 'Singapore', '564': 'Singapore', '565': 'Singapore',
    '566': 'Singapore', '567': 'Thailand', '570': 'Tonga', '572': 'Tuvalu',
    '574': 'Vietnam', '576': 'Vanuatu', '577': 'Vanuatu', '578': 'Wallis and Futuna',
    '601': 'South Africa', '603': 'Angola', '605': 'Algeria', '607': 'Saint Paul and Amsterdam Islands',
    '608': 'Ascension Island', '609': 'Burundi', '610': 'Benin', '611': 'Botswana',
    '612': 'Central African Republic', '613': 'Cameroon', '615': 'Congo', '616': 'Comoros',
    '617': 'Cape Verde', '618': 'Crozet Archipelago', '619': 'Ivory Coast', '620': 'Comoros',
    '621': 'Djibouti', '622': 'Egypt', '624': 'Ethiopia', '625': 'Eritrea', '626': 'Gabonese Republic',
    '627': 'Ghana', '629': 'Gambia', '630': 'Guinea-Bissau', '631': 'Equatorial Guinea',
    '632': 'Guinea', '633': 'Burkina Faso', '634': 'Kenya', '635': 'Kerguelen Islands',
    '636': 'Liberia', '637': 'Liberia', '638': 'South Sudan', '642': 'Libya',
    '644': 'Lesotho', '645': 'Mauritius', '647': 'Madagascar', '649': 'Mali',
    '650': 'Mozambique', '654': 'Mauritania', '655': 'Malawi', '656': 'Niger',
    '657': 'Nigeria', '659': 'Namibia', '660': 'Reunion', '661': 'Rwanda', '662': 'Sudan',
    '663': 'Senegal', '664': 'Seychelles', '665': 'Saint Helena', '666': 'Somalia',
    '667': 'Sierra Leone', '668': 'Sao Tome and Principe', '669': 'Swaziland',
    '670': 'Chad', '671': 'Togo', '672': 'Tunisia', '674': 'Tanzania', '675': 'Uganda',
    '676': 'Democratic Republic of the Congo', '677': 'Tanzania', '678': 'Zambia',
    '679': 'Zimbabwe', '701': 'Argentina', '710': 'Brazil', '720': 'Bolivia',
    '725': 'Chile', '730': 'Colombia', '735': 'Ecuador', '740': 'Falkland Islands',
    '745': 'Guiana', '750': 'Guyana', '755': 'Paraguay', '760': 'Peru', '765': 'Suriname',
    '770': 'Uruguay', '775': 'Venezuela'
}

# Vessel types that are buoys or non-ship objects (based on AIS ship type codes)
BUOY_VESSEL_TYPES = {
    0: 'Not available',  # Sometimes buoys
    8: 'Sailing',  # Sometimes incorrectly used for buoys
    9: 'Pleasure Craft',  # Sometimes incorrectly used for buoys
    50: 'Pilot Vessel',
    51: 'Search and Rescue vessel',
    52: 'Tug',
    53: 'Port Tender',
    54: 'Anti-pollution equipment',
    55: 'Law Enforcement',
    56: 'Spare - Local Vessel',
    57: 'Spare - Local Vessel',
    58: 'Medical Transport',
    59: 'Non-combatant ship'
}

# Common buoy name patterns (expanded with international patterns)
BUOY_NAME_PATTERNS = [
    'BUOY', 'BOUY', 'BEACON', 'MARKER', 'LIGHT', 'PLATFORM', 'RIG', 'STATION',
    'WEATHER', 'METEO', 'OCEANOGRAPHIC', 'MONITORING', 'RESEARCH PLATFORM',
    'LANBY', 'FAIRWAY', 'CARDINAL', 'LATERAL', 'SAFE WATER', 'SPECIAL MARK',
    'LIGHTHOUSE', 'LIGHTSHIP', 'TOWER', 'PILE', 'SPAR', 'CAN', 'CONICAL',
    'SPHERICAL', 'PILLAR', 'FLOAT', 'MOORING', 'ANCHOR', 'WRECK', 'OBSTRUCTION',
    'DRILLING', 'PRODUCTION', 'FPSO', 'FSO', 'FLNG', 'SEMI-SUB', 'JACK-UP',
    'SEMISUBMERSIBLE', 'EXPLORATION', 'WELLHEAD', 'MANIFOLD',
    # Norwegian/Nordic patterns
    'BØYE', 'BÅKE', 'FYR', 'LYSKULL', 'MERKE', 'VARDØ', 'LEIDEMERK',
    # Russian patterns  
    'БУЙ', 'БУЙ', 'БУЕК', 'ПЛАВУЧА', 'СТВОРНЫЙ', 'МАЯК',
    # Common buoy code patterns
    'BUSINKA', 'BUSIN', 'CARDINAL', 'ISOLATED DANGER', 'NORTH CARDINAL',
    'SOUTH CARDINAL', 'EAST CARDINAL', 'WEST CARDINAL', 'PORT HAND', 'STARBOARD HAND'
]

# CSV Files
VESSEL_POSITIONS_CSV = DATA_DIR / 'vessel_positions.csv'
DARK_VESSELS_CSV = DATA_DIR / 'dark_vessels.csv'
CABLE_ALERTS_CSV = DATA_DIR / 'cable_alerts.csv'
DAILY_SUMMARY_CSV = DATA_DIR / 'daily_summary.csv'

# Logging setup - ensure directory exists
log_file = DATA_DIR / 'streaming.log'
log_file.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Arctic regions and submarine cables (from notebook)
ARCTIC_REGIONS = {
    'svalbard': {'bbox': [10.0, 76.0, 35.0, 81.0], 'priority': 'HIGH'},
    'north_norway': {'bbox': [15.0, 68.0, 32.0, 71.5], 'priority': 'HIGH'},
    'barents_sea': {'bbox': [20.0, 72.0, 40.0, 76.0], 'priority': 'CRITICAL'}
}

SUBMARINE_CABLES = {
    'svalbard_cable': {
        'name': 'Svalbard Undersea Cable System',
        'coordinates': [[78.9, 11.9], [71.0, 25.8]],
        'alert_distance_km': 10
    },
    'lofoten_vesteralen': {
        'name': 'Lofoten-Vesterålen Cable',
        'coordinates': [[68.8, 13.6], [69.3, 16.0]],
        'alert_distance_km': 5
    },
    'norway_uk': {
        'name': 'Norway-UK Cable (Arctic Section)',
        'coordinates': [[70.0, 23.0], [69.0, 18.0]],
        'alert_distance_km': 8
    }
}

def get_country_from_mmsi(mmsi):
    """Get country from MMSI prefix"""
    mmsi_str = str(mmsi)
    if len(mmsi_str) >= 3:
        prefix = mmsi_str[:3]
        return MMSI_COUNTRY_MAP.get(prefix, 'Unknown')
    return 'Unknown'

def is_buoy_or_platform(vessel):
    """Check if vessel is likely a buoy or platform"""
    name = vessel.get('name', '').upper()
    vessel_type = vessel.get('shipType', 0)
    speed = vessel.get('speedOverGround')
    
    # Handle None speed values
    if speed is None:
        speed = 0
    
    # PRIMARY FILTER: Most buoys have vessel type 0 (undefined)
    # But we need to be careful not to filter real ships with type 0
    if vessel_type == 0:
        # If type 0 AND any buoy indicators, definitely filter
        if (speed < 3.0 or  # Low speed
            any(pattern in name for pattern in BUOY_NAME_PATTERNS) or
            len(name) <= 5 or  # Short names often buoys
            any(char.isdigit() for char in name)):  # Contains numbers
            return True
    
    # Check explicit buoy name patterns
    if any(pattern in name for pattern in BUOY_NAME_PATTERNS):
        return True
    
    # Check for numbered buoy patterns (e.g., "O BUOY 04", "BUOY 1", "42", etc.)
    import re
    if re.match(r'^[A-Z]*\s*BUOY?\s*\d+$', name) or re.match(r'^\d+$', name):
        return True
    
    # Check for letter-number combinations often used for buoys
    if re.match(r'^[A-Z]{1,3}\s*\d{1,3}$', name) and speed < 2.0:
        return True
    
    # Check for extremely stationary objects with suspicious names
    if speed < 0.1:
        if ('UNKNOWN' in name or len(name) <= 3 or 
            name.count(' ') == 0 and len(name) < 8):
            return True
    
    # Check for weather/monitoring equipment patterns
    weather_patterns = ['WEATHER', 'METEO', 'WIND', 'WAVE', 'CURRENT', 'TIDE']
    if any(pattern in name for pattern in weather_patterns) and speed < 2.0:
        return True
    
    # Check for platform/rig indicators
    platform_indicators = ['PLATFORM', 'RIG', 'DRILLING', 'PRODUCTION', 'WELLHEAD']
    if any(indicator in name for indicator in platform_indicators):
        return True
    
    return False

def load_config():
    """Load API credentials from environment variables or config.yaml"""
    # First, try to get credentials from environment variables (GitHub Actions)
    client_secret = os.getenv('BARENTSWATCH_CLIENT_SECRET')
    if client_secret:
        logger.info("Using BarentsWatch credentials from environment variables")
        return {
            'barentswatch': {
                'client_id': 'henrikformoe@gmail.com:ArcticShadowTrackerAIS',
                'client_secret': client_secret,
                'scope': 'ais'
            }
        }
    
    # Fallback to config.yaml for local development
    try:
        # Try current directory first, then parent directory
        config_paths = ['config.yaml', '../config.yaml']
        for config_path in config_paths:
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info("Using BarentsWatch credentials from config.yaml")
                    return config
            except FileNotFoundError:
                continue
        raise FileNotFoundError("config.yaml not found and BARENTSWATCH_CLIENT_SECRET not set")
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def get_barentswatch_token():
    """Get access token for BarentsWatch API"""
    config = load_config()
    if not config:
        logger.error("No configuration available for BarentsWatch API")
        return None
    
    if 'barentswatch' not in config:
        logger.error("BarentsWatch configuration missing from config")
        return None
    
    token_url = "https://id.barentswatch.no/connect/token"
    data = {
        'client_id': config['barentswatch']['client_id'],
        'client_secret': config['barentswatch']['client_secret'],
        'scope': config['barentswatch']['scope'],
        'grant_type': 'client_credentials'
    }
    
    try:
        logger.info("Requesting BarentsWatch access token...")
        response = requests.post(token_url, data=data, timeout=30)
        response.raise_for_status()
        token = response.json()['access_token']
        logger.info("Successfully obtained BarentsWatch access token")
        return token
    except requests.exceptions.RequestException as e:
        logger.error(f"BarentsWatch token request failed: {e}")
        return None
    except KeyError as e:
        logger.error(f"Unexpected token response format: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting token: {e}")
        return None

def collect_ais_data():
    """Collect Arctic AIS data (foreign vessels only, excluding buoys)"""
    logger.info("Collecting AIS data from BarentsWatch...")
    
    token = get_barentswatch_token()
    if not token:
        return []
    
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    
    try:
        url = "https://live.ais.barentswatch.no/v1/latest/combined"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        all_vessels = response.json()
        arctic_vessels = []
        norwegian_filtered = 0
        buoys_filtered = 0
        
        for vessel in all_vessels:
            lat = vessel.get('latitude', 0)
            if lat >= 65.0:  # Arctic threshold
                mmsi = str(vessel.get('mmsi', ''))
                name = vessel.get('name', 'Unknown')
                
                # Filter buoys and platforms first
                if is_buoy_or_platform(vessel):
                    buoys_filtered += 1
                    continue
                
                # Filter Norwegian vessels
                is_norwegian = False
                if mmsi.startswith(('257', '258', '259')):
                    is_norwegian = True
                
                norwegian_patterns = [
                    'NORSK', 'BERGEN', 'OSLO', 'STAVANGER', 'TROMSO', 'HAVILA',
                    'HURTIGRUTEN', 'FJORD', 'FISK', 'POLAR', 'SUND', 'VIK'
                ]
                if any(pattern in name.upper() for pattern in norwegian_patterns):
                    is_norwegian = True
                
                if not is_norwegian:
                    # Get country from MMSI
                    country = get_country_from_mmsi(mmsi)
                    
                    vessel_data = {
                        'timestamp': datetime.now().isoformat(),
                        'mmsi': mmsi,
                        'name': name,
                        'country': country,
                        'latitude': lat,
                        'longitude': vessel.get('longitude', 0),
                        'speed': vessel.get('speedOverGround') or 0,
                        'course': vessel.get('courseOverGround') or 0,
                        'vessel_type': vessel.get('shipType', 'Unknown')
                    }
                    arctic_vessels.append(vessel_data)
                else:
                    norwegian_filtered += 1
        
        logger.info(f"Found {len(arctic_vessels)} foreign Arctic vessels")
        logger.info(f"Filtered {norwegian_filtered} Norwegian vessels")
        logger.info(f"Filtered {buoys_filtered} buoys/platforms")
        return arctic_vessels
        
    except Exception as e:
        logger.error(f"AIS collection failed: {e}")
        return []

def calculate_distance_km(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in kilometers"""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return c * 6371  # Earth radius in km

def point_to_line_distance(px, py, x1, y1, x2, y2):
    """Calculate minimum distance from point to line segment"""
    dx = x2 - x1
    dy = y2 - y1
    
    if dx == 0 and dy == 0:
        return calculate_distance_km(px, py, x1, y1)
    
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    return calculate_distance_km(px, py, closest_x, closest_y)

def check_cable_proximity(vessels):
    """Check vessel proximity to submarine cables"""
    logger.info("Checking submarine cable proximity...")
    
    cable_alerts = []
    
    for vessel in vessels:
        lat, lon = vessel['latitude'], vessel['longitude']
        
        for cable_id, cable in SUBMARINE_CABLES.items():
            coords = cable['coordinates']
            if len(coords) >= 2:
                start_lat, start_lon = coords[0]
                end_lat, end_lon = coords[1]
                
                distance = point_to_line_distance(lat, lon, start_lat, start_lon, end_lat, end_lon)
                
                if distance <= cable['alert_distance_km']:
                    alert = {
                        'timestamp': datetime.now().isoformat(),
                        'vessel_mmsi': vessel['mmsi'],
                        'vessel_name': vessel['name'],
                        'cable_name': cable['name'],
                        'distance_km': round(distance, 2),
                        'latitude': lat,
                        'longitude': lon,
                        'alert_threshold': cable['alert_distance_km']
                    }
                    cable_alerts.append(alert)
    
    logger.info(f"Found {len(cable_alerts)} cable proximity alerts")
    return cable_alerts

def detect_dark_vessels(current_vessels):
    """Detect vessels that have gone dark (turned off AIS)"""
    logger.info("Detecting dark vessels...")
    
    # Load vessel history
    history_file = DATA_DIR / 'vessel_history.json'
    if history_file.exists():
        with open(history_file, 'r') as f:
            history = json.load(f)
    else:
        history = {}
    
    current_time = datetime.now()
    current_mmsis = {v['mmsi'] for v in current_vessels if v['mmsi']}
    dark_vessels = []
    
    # Check for missing vessels
    for mmsi, vessel_history in history.items():
        if mmsi not in current_mmsis:
            positions = vessel_history.get('positions', [])
            if positions:
                last_seen = datetime.fromisoformat(positions[-1]['timestamp'])
                hours_since = (current_time - last_seen).total_seconds() / 3600
                
                if 2 <= hours_since <= 48:
                    last_pos = positions[-1]
                    dark_vessel = {
                        'timestamp': current_time.isoformat(),
                        'mmsi': mmsi,
                        'name': vessel_history.get('name', 'Unknown'),
                        'last_seen': last_seen.isoformat(),
                        'hours_dark': round(hours_since, 1),
                        'last_latitude': last_pos['latitude'],
                        'last_longitude': last_pos['longitude'],
                        'last_speed': last_pos.get('speed', 0)
                    }
                    dark_vessels.append(dark_vessel)
    
    # Update history
    for vessel in current_vessels:
        mmsi = vessel['mmsi']
        if mmsi not in history:
            history[mmsi] = {'name': vessel['name'], 'positions': []}
        
        position = {
            'timestamp': vessel['timestamp'],
            'latitude': vessel['latitude'],
            'longitude': vessel['longitude'],
            'speed': vessel['speed'],
            'course': vessel['course']
        }
        history[mmsi]['positions'].append(position)
        history[mmsi]['positions'] = history[mmsi]['positions'][-50:]  # Keep last 50
        history[mmsi]['name'] = vessel['name']
    
    # Save history
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)
    
    logger.info(f"Detected {len(dark_vessels)} dark vessels")
    return dark_vessels

def save_to_csv(vessels, dark_vessels, cable_alerts):
    """Save data to CSV files"""
    logger.info("Saving data to CSV files...")
    
    # Vessel positions
    if vessels:
        df_vessels = pd.DataFrame(vessels)
        if VESSEL_POSITIONS_CSV.exists():
            df_existing = pd.read_csv(VESSEL_POSITIONS_CSV)
            df_vessels = pd.concat([df_existing, df_vessels], ignore_index=True)
        df_vessels.to_csv(VESSEL_POSITIONS_CSV, index=False)
    
    # Dark vessels
    if dark_vessels:
        df_dark = pd.DataFrame(dark_vessels)
        if DARK_VESSELS_CSV.exists():
            df_existing = pd.read_csv(DARK_VESSELS_CSV)
            df_dark = pd.concat([df_existing, df_dark], ignore_index=True)
        df_dark.to_csv(DARK_VESSELS_CSV, index=False)
    
    # Cable alerts
    if cable_alerts:
        df_cables = pd.DataFrame(cable_alerts)
        if CABLE_ALERTS_CSV.exists():
            df_existing = pd.read_csv(CABLE_ALERTS_CSV)
            df_cables = pd.concat([df_existing, df_cables], ignore_index=True)
        df_cables.to_csv(CABLE_ALERTS_CSV, index=False)
    
    # Daily summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_vessels': len(vessels),
        'dark_vessels': len(dark_vessels),
        'cable_alerts': len(cable_alerts)
    }
    df_summary = pd.DataFrame([summary])
    if DAILY_SUMMARY_CSV.exists():
        df_existing = pd.read_csv(DAILY_SUMMARY_CSV)
        df_summary = pd.concat([df_existing, df_summary], ignore_index=True)
    df_summary.to_csv(DAILY_SUMMARY_CSV, index=False)

def create_interactive_map(vessels, dark_vessels, cable_alerts):
    """Create interactive HTML map"""
    logger.info("Creating interactive map...")
    
    # Center on Arctic Norway
    m = folium.Map(location=[72.0, 25.0], zoom_start=4)
    
    # Add submarine cables
    for cable in SUBMARINE_CABLES.values():
        coords = cable['coordinates']
        if len(coords) >= 2:
            folium.PolyLine(
                locations=coords,
                color='red',
                weight=3,
                opacity=0.8,
                popup=f"🔌 {cable['name']}"
            ).add_to(m)
    
    # Add current vessels with country-based coloring
    for vessel in vessels:  # Show all filtered vessels
        country = vessel.get('country', 'Unknown')
        
        # Color-code by country/region
        if country == 'Russia':
            color = 'red'
            fillColor = 'darkred'
            flag_emoji = '🇷🇺'
        elif country == 'China':
            color = 'orange'
            fillColor = 'orange'
            flag_emoji = '🇨🇳'
        elif country in ['Unknown']:
            color = 'gray'
            fillColor = 'lightgray'
            flag_emoji = '❓'
        else:
            color = 'blue'
            fillColor = 'lightblue'
            flag_emoji = '🌍'
        
        folium.CircleMarker(
            location=[vessel['latitude'], vessel['longitude']],
            radius=6,
            color=color,
            fillColor=fillColor,
            fillOpacity=0.8,
            popup=f"{flag_emoji} {vessel['name']}<br>🌍 Country: {country}<br>📍 MMSI: {vessel['mmsi']}<br>⚡ Speed: {vessel['speed']} knots"
        ).add_to(m)
    
    # Add dark vessels
    for vessel in dark_vessels:
        folium.CircleMarker(
            location=[vessel['last_latitude'], vessel['last_longitude']],
            radius=10,
            color='red',
            fillColor='darkred',
            fillOpacity=0.9,
            popup=f"🌑 DARK VESSEL<br>{vessel['name']}<br>Dark for: {vessel['hours_dark']}h"
        ).add_to(m)
    
    # Add alert counter
    alert_text = f"""
    <div style='position: fixed; top: 10px; right: 10px; background: white; padding: 10px; border: 2px solid blue; border-radius: 5px; z-index: 9999;'>
    <h4>Arctic Intelligence</h4>
    <p>🚢 Vessels: {len(vessels)}</p>
    <p>🌑 Dark: {len(dark_vessels)}</p>
    <p>⚠️ Alerts: {len(cable_alerts)}</p>
    <p>🕐 {datetime.now().strftime('%H:%M:%S')}</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(alert_text))
    
    # Save map
    map_file = DATA_DIR / f"arctic_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    m.save(str(map_file))
    
    # Also save as latest
    latest_map = DATA_DIR / "arctic_dashboard_latest.html"
    m.save(str(latest_map))
    
    logger.info(f"Map saved: {map_file}")
    return map_file

def run_surveillance_cycle():
    """Run one complete surveillance cycle"""
    logger.info("=" * 50)
    logger.info("Starting Arctic surveillance cycle")
    
    try:
        # Collect data
        vessels = collect_ais_data()
        cable_alerts = check_cable_proximity(vessels)
        dark_vessels = detect_dark_vessels(vessels)
        
        # Save data
        save_to_csv(vessels, dark_vessels, cable_alerts)
        
        # Create visualization
        map_file = create_interactive_map(vessels, dark_vessels, cable_alerts)
        
        # Summary
        logger.info(f"Cycle complete: {len(vessels)} vessels, {len(dark_vessels)} dark, {len(cable_alerts)} alerts")
        logger.info(f"Dashboard: {map_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Surveillance cycle failed: {e}")
        return False

def main():
    """Main streaming loop"""
    logger.info("🛰️ Arctic Shadow Tracker Streaming Started")
    
    while True:
        try:
            success = run_surveillance_cycle()
            
            if success:
                logger.info("Waiting 30 minutes for next cycle...")
                time.sleep(1800)  # 30 minutes
            else:
                logger.info("Waiting 5 minutes before retry...")
                time.sleep(300)   # 5 minutes on error
                
        except KeyboardInterrupt:
            logger.info("Streaming stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(300)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run single test cycle
        logger.info("Running single test cycle...")
        run_surveillance_cycle()
    else:
        # Run continuous streaming
        main()