"""
Focus Mode Map Generator
Creates interactive Folium maps with tier-based track visualization:
  - High-risk vessels: Full tracks (all tiers)
  - Medium/low-risk vessels: Strategic tier only
  - Click vessel to focus (shows all tiers)
"""

import folium
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from .airport_loader import load_norwegian_airports

# ============================================================================
# Palette — single source of truth for vessel + layer colors.
# Chosen for maximum distinguishability at small CircleMarker radii on dark tiles.
# ============================================================================
CATEGORY_COLORS = {
    'russia':         '#e53935',   # bright red
    'shadow':         '#b71c1c',   # dark red — distinct from Russia
    'suspected':      '#ffb300',   # amber — distinct from China
    'china':          '#fb8c00',   # deep orange
    'norway_mil':     '#43a047',   # green
    'norway_civ':     '#90a4ae',   # cool grey
    'other':          '#29b6f6',   # sky blue
    'buoy':           '#546e7a',   # dark grey
    'cables':         '#ab47bc',   # purple
    'eez':            '#42a5f5',   # light blue
    'territorial':    '#5c6bc0',   # indigo
    'boundary_200nm': '#1976d2',   # dark blue
}


def _swatch(key):
    """Return an inline HTML colored dot for use in Folium layer control labels.

    Leaflet's L.control.layers renders label names via innerHTML, so HTML
    in a FeatureGroup name= argument is preserved and appears next to the checkbox.
    """
    return (
        f'<span style="display:inline-block;width:10px;height:10px;'
        f'border-radius:50%;background:{CATEGORY_COLORS[key]};'
        f'margin-right:6px;vertical-align:middle;"></span>'
    )


def _vessel_color(track_data):
    """Map a vessel's classification to a CATEGORY_COLORS entry.

    Priority matches app.py _classify_vessels: buoy > shadow > suspected > norway_mil > country.
    """
    if track_data.get('is_buoy'):
        return CATEGORY_COLORS['buoy']
    if track_data.get('is_shadow_fleet'):
        return CATEGORY_COLORS['shadow']
    if track_data.get('is_suspected_shadow'):
        return CATEGORY_COLORS['suspected']
    country = track_data.get('country') or ''
    ship_type = (track_data.get('ship_type') or '').lower()
    if country == 'Norway' and ('military' in ship_type or 'law enforcement' in ship_type):
        return CATEGORY_COLORS['norway_mil']
    if country == 'Russia':
        return CATEGORY_COLORS['russia']
    if country == 'China':
        return CATEGORY_COLORS['china']
    if country == 'Norway':
        return CATEGORY_COLORS['norway_civ']
    return CATEGORY_COLORS['other']

def load_submarine_cables():
    """
    Load submarine cable GeoJSON and filter for Norwegian/Svalbard region

    Returns:
        GeoJSON FeatureCollection with cables in Norwegian sector (lon: 0-35, lat: 58-81)
    """
    try:
        cable_file = Path(__file__).parent / 'cable-geo.json'
        with open(cable_file) as f:
            data = json.load(f)

        # Filter cables in Norwegian sector and Svalbard (lon: 0-35, lat: 58-81)
        norwegian_cables = []
        for feature in data['features']:
            coords = feature['geometry']['coordinates']
            # Check if any segment is in Norwegian region
            for line in coords:
                if any(0 <= point[0] <= 35 and 58 <= point[1] <= 81 for point in line):
                    norwegian_cables.append(feature)
                    break

        return {
            'type': 'FeatureCollection',
            'features': norwegian_cables
        }
    except Exception as e:
        print(f"Warning: Could not load submarine cables: {e}")
        return {'type': 'FeatureCollection', 'features': []}

def load_200nm_boundary():
    """Load 200 nautical mile boundary (most visible)"""
    try:
        file_path = Path(__file__).parent / 'marine_border' / 'norway_200nm_boundary.json'
        with open(file_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load 200nm boundary: {e}")
        return {'type': 'FeatureCollection', 'features': []}

def load_eez_zone():
    """Load Norwegian Economic Zone (semi-transparent)"""
    try:
        file_path = Path(__file__).parent / 'marine_border' / 'norway_eez.json'
        with open(file_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load EEZ zone: {e}")
        return {'type': 'FeatureCollection', 'features': []}

def load_territorial_waters():
    """Load territorial waters (most transparent)"""
    try:
        file_path = Path(__file__).parent / 'marine_border' / 'norway_territorial_waters.json'
        with open(file_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load territorial waters: {e}")
        return {'type': 'FeatureCollection', 'features': []}

def calculate_opacity_multiplier(hours_since_signal):
    """
    Calculate opacity multiplier based on time since last AIS signal

    Rules:
    - 0-24 hours: Full opacity (1.0)
    - 24-168 hours: Linear fade from 100% to 10%
    - 168+ hours: Minimal opacity (will be removed by retention policy)

    Args:
        hours_since_signal: Hours since vessel's last AIS transmission

    Returns:
        Opacity multiplier (0.1 to 1.0)
    """
    if hours_since_signal <= 24:
        return 1.0  # Full opacity for recent signals
    elif hours_since_signal >= 168:
        return 0.1  # Almost invisible (vessel will be removed anyway)
    else:
        # Linear fade from 100% at 24h to 10% at 168h
        # Formula: 1.0 - ((hours - 24) / 144) * 0.9
        fade_progress = (hours_since_signal - 24) / 144  # 0.0 to 1.0
        return max(0.1, 1.0 - (fade_progress * 0.9))

def calculate_coverage_boundary(vessel_tracks):
    """
    Calculate dynamic coverage area from actual vessel positions

    Args:
        vessel_tracks: Dict of vessel track data

    Returns:
        GeoJSON Feature with polygon showing actual data coverage
    """
    lats, lons = [], []

    for track in vessel_tracks.values():
        # Get current position from most recent tier
        tiers = track.get('tiers', {})
        pos = None

        if tiers.get('realtime'):
            pos = tiers['realtime'][-1]
        elif tiers.get('tactical'):
            pos = tiers['tactical'][-1]
        elif tiers.get('strategic'):
            pos = tiers['strategic'][-1]

        if pos:
            lats.append(pos['lat'])
            lons.append(pos['lon'])

    if not lats:
        return None

    # Add 2-degree buffer
    buffer = 2.0
    min_lat, max_lat = min(lats) - buffer, max(lats) + buffer
    min_lon, max_lon = min(lons) - buffer, max(lons) + buffer

    # Create polygon (GeoJSON format: [lon, lat])
    bounds = [
        [min_lon, min_lat],  # SW corner
        [max_lon, min_lat],  # SE corner
        [max_lon, max_lat],  # NE corner
        [min_lon, max_lat],  # NW corner
        [min_lon, min_lat]   # Close polygon
    ]

    return {
        'type': 'Feature',
        'geometry': {
            'type': 'Polygon',
            'coordinates': [bounds]
        },
        'properties': {
            'name': 'AIS Data Coverage',
            'bounds': f'{min_lat:.1f}-{max_lat:.1f}°N, {min_lon:.1f}-{max_lon:.1f}°E',
            'vessels': len(lats)
        }
    }

def generate_focused_map(vessel_tracks):
    """
    Generate interactive map with focus mode

    Args:
        vessel_tracks: Dict of vessel track data (from track_manager)

    Returns:
        folium.Map object
    """
    # Center on Norway (mid-country)
    m = folium.Map(
        location=[68, 15],
        zoom_start=5,
        tiles='OpenStreetMap'
    )

    # Add Norwegian maritime zones (3 layers with different visibility)
    # Layer 1: Territorial Waters (12nm) - Most transparent, hidden by default
    territorial_waters = load_territorial_waters()
    if territorial_waters['features']:
        territorial_layer = folium.FeatureGroup(name=_swatch('territorial') + 'Territorial Waters (12nm)', show=False)
        folium.GeoJson(
            territorial_waters,
            style_function=lambda feature: {
                'color': '#64B5F6',      # Light blue
                'weight': 1,
                'opacity': 0.2,
                'fillOpacity': 0,
                'dashArray': '2, 4'      # Fine dashed line
            }
        ).add_to(territorial_layer)
        territorial_layer.add_to(m)

    # Layer 2: Norwegian Economic Zone (EEZ) - Semi-transparent
    eez_zone = load_eez_zone()
    if eez_zone['features']:
        eez_layer = folium.FeatureGroup(name=_swatch('eez') + 'Norwegian EEZ', show=True)
        folium.GeoJson(
            eez_zone,
            style_function=lambda feature: {
                'color': '#2196F3',      # Blue
                'weight': 2,
                'opacity': 0.3,
                'fillOpacity': 0,
                'dashArray': '5, 5'      # Dashed line
            }
        ).add_to(eez_layer)
        eez_layer.add_to(m)

    # Layer 3: 200 Nautical Mile Boundary - Most visible (primary border)
    boundary_200nm = load_200nm_boundary()
    if boundary_200nm['features']:
        boundary_layer = folium.FeatureGroup(name=_swatch('boundary_200nm') + '200nm Boundary', show=False)
        folium.GeoJson(
            boundary_200nm,
            style_function=lambda feature: {
                'color': '#1976D2',      # Dark blue
                'weight': 3,
                'opacity': 0.8,
                'fillOpacity': 0
            }
        ).add_to(boundary_layer)
        boundary_layer.add_to(m)

    # Create feature groups for toggleable layers (HTML swatches render via Leaflet innerHTML)
    russia_layer             = folium.FeatureGroup(name=_swatch('russia')     + 'Russia', show=True)
    shadow_fleet_layer       = folium.FeatureGroup(name=_swatch('shadow')     + 'Shadow Fleet', show=True)
    suspected_shadow_layer   = folium.FeatureGroup(name=_swatch('suspected')  + 'Suspected Shadow Fleet', show=True)
    china_layer              = folium.FeatureGroup(name=_swatch('china')      + 'China', show=True)
    norwegian_military_layer = folium.FeatureGroup(name=_swatch('norway_mil') + 'Norwegian Military/Law', show=False)
    norway_layer             = folium.FeatureGroup(name=_swatch('norway_civ') + 'Norway (Civilian)', show=False)
    other_layer              = folium.FeatureGroup(name=_swatch('other')      + 'Other Countries', show=False)
    buoy_layer               = folium.FeatureGroup(name=_swatch('buoy')       + 'Buoys', show=False)

    # Add submarine cables layer
    cables_layer = folium.FeatureGroup(name=_swatch('cables') + 'Submarine Cables', show=True)
    cables_geojson = load_submarine_cables()
    if cables_geojson['features']:
        folium.GeoJson(
            cables_geojson,
            style_function=lambda feature: {
                'color': CATEGORY_COLORS['cables'],
                'weight': 2,
                'opacity': 0.7,
                'dashArray': '5, 5',  # Dashed line for cables
                'fillOpacity': 0
            },
            tooltip=folium.GeoJsonTooltip(
                fields=['name', 'id'],
                aliases=['Cable:', 'ID:'],
                localize=True
            ),
            smooth_factor=0  # Preserve exact coordinates
        ).add_to(cables_layer)
    cables_layer.add_to(m)

    # Add airports layer
    airports_layer = folium.FeatureGroup(name='Airports & Heliports', show=False)
    airports = load_norwegian_airports()
    for airport in airports:
        # Determine icon based on airport type
        airport_type = airport['type']
        if airport_type == 'large_airport':
            icon_html = '<div style="font-size: 30px;">✈️</div>'
            icon_size = (30, 30)
        elif airport_type == 'medium_airport':
            icon_html = '<div style="font-size: 24px;">🛩️</div>'
            icon_size = (24, 24)
        elif airport_type == 'small_airport':
            icon_html = '<div style="font-size: 18px;">🛫</div>'
            icon_size = (18, 18)
        elif airport_type == 'heliport':
            icon_html = '<div style="font-size: 18px;">🚁</div>'
            icon_size = (18, 18)
        else:
            icon_html = '<div style="font-size: 15px;">🛬</div>'
            icon_size = (15, 15)

        # Create tooltip text
        tooltip_text = f"{airport['name']}"
        if airport['icao_code']:
            tooltip_text += f" ({airport['icao_code']})"
        tooltip_text += f"<br>Type: {airport_type.replace('_', ' ').title()}"
        if airport['municipality']:
            tooltip_text += f"<br>Location: {airport['municipality']}"

        # Add marker
        folium.Marker(
            location=[airport['latitude'], airport['longitude']],
            icon=folium.DivIcon(html=icon_html, icon_size=icon_size),
            tooltip=tooltip_text
        ).add_to(airports_layer)

    airports_layer.add_to(m)

    # Count vessels by risk
    risk_counts = {'high': 0, 'medium': 0, 'low': 0}

    # Separate vessels by priority for z-order (render low priority first, then high)
    # Z-order (bottom to top): Buoys -> Other -> Norway civilians -> Suspected Shadow -> Norwegian Military -> China -> Confirmed Shadow -> Russia
    buoy_vessels = []
    other_vessels = []
    norwegian_civilian_vessels = []
    suspected_shadow_vessels = []
    confirmed_shadow_vessels = []
    high_priority_vessels = []  # Russia, China, Norwegian Military

    for mmsi, track_data in vessel_tracks.items():
        priority_level = track_data['priority_level']
        risk_counts[priority_level] += 1

        # Check if it's a regular Norwegian vessel (gray, not military)
        ship_type = track_data['ship_type'].lower()
        is_norwegian_civilian = (track_data['country'] == 'Norway' and
                                 'military' not in ship_type and
                                 'law enforcement' not in ship_type)

        # Categorize for z-order
        if track_data.get('is_buoy', False):
            # Buoys (lowest priority)
            buoy_vessels.append((mmsi, track_data))
        elif track_data.get('is_shadow_fleet', False):
            # Confirmed shadow fleet (top priority)
            confirmed_shadow_vessels.append((mmsi, track_data))
        elif track_data.get('is_suspected_shadow', False):
            # Suspected shadow fleet (medium priority)
            suspected_shadow_vessels.append((mmsi, track_data))
        elif priority_level == 'high':
            # Russia, China, Norwegian Military
            high_priority_vessels.append((mmsi, track_data))
        elif is_norwegian_civilian:
            # Norwegian civilians
            norwegian_civilian_vessels.append((mmsi, track_data))
        else:
            # Other countries (foreign vessels)
            other_vessels.append((mmsi, track_data))

    # Add vessels in z-order (bottom to top)
    # Assign each vessel to its appropriate layer
    for mmsi, track_data in buoy_vessels:
        add_vessel_to_map(buoy_layer, mmsi, track_data)

    for mmsi, track_data in other_vessels:
        add_vessel_to_map(other_layer, mmsi, track_data)

    for mmsi, track_data in norwegian_civilian_vessels:
        add_vessel_to_map(norway_layer, mmsi, track_data)

    for mmsi, track_data in suspected_shadow_vessels:
        add_vessel_to_map(suspected_shadow_layer, mmsi, track_data)

    for mmsi, track_data in high_priority_vessels:
        # Determine which high-priority layer (Russia, China, Norwegian Military)
        if track_data['country'] == 'Russia':
            target_layer = russia_layer
        elif track_data['country'] == 'China':
            target_layer = china_layer
        else:  # Norwegian military/law
            target_layer = norwegian_military_layer
        add_vessel_to_map(target_layer, mmsi, track_data)

    for mmsi, track_data in confirmed_shadow_vessels:
        add_vessel_to_map(shadow_fleet_layer, mmsi, track_data)

    # Add all layers to map
    # Order matches "By Country" sidebar: Russia, Shadow Fleet, Suspected Shadow Fleet, China, Other, Norwegian Military/Law, Norway, Buoy
    # Layers added in this order for LayerControl display
    buoy_layer.add_to(m)
    norway_layer.add_to(m)
    norwegian_military_layer.add_to(m)
    other_layer.add_to(m)
    china_layer.add_to(m)
    suspected_shadow_layer.add_to(m)
    shadow_fleet_layer.add_to(m)
    russia_layer.add_to(m)

    # Add focus mode controls
    add_focus_mode_script(m, vessel_tracks)

    # Add layer control to toggle all categories
    folium.LayerControl(position='topright', collapsed=True).add_to(m)

    # Add JavaScript for cross-iframe communication (clicking anomalies)
    vessel_click_js = """
    <script>
    // Listen for messages from parent window (dashboard)
    window.addEventListener('message', function(event) {
        console.log('=== MAP IFRAME: PostMessage received ===');
        console.log('Event origin:', event.origin);
        console.log('Event data:', JSON.stringify(event.data));

        if (event.data && event.data.type === 'clickVessel') {
            const mmsi = event.data.mmsi;
            const hintLat = event.data.lat;  // optional — from anomaly.details
            const hintLon = event.data.lon;  // optional — from anomaly.details
            console.log('clickVessel received. mmsi:', mmsi, 'hint:', hintLat, hintLon);

            if (typeof focusVessel === 'function') {
                focusVessel(mmsi, hintLat, hintLon);
            } else {
                // Fallback: focus mode script may not be loaded yet
                setTimeout(function() {
                    if (typeof focusVessel === 'function') {
                        focusVessel(mmsi, hintLat, hintLon);
                    } else {
                        console.error('focusVessel still not available after retry');
                    }
                }, 500);
            }
        } else {
            console.log('Message ignored (not clickVessel type)');
        }
    });

    console.log('=== MAP IFRAME: PostMessage listener registered ===');
    </script>
    """

    # Inject JavaScript into map HTML
    m.get_root().html.add_child(folium.Element(vessel_click_js))

    return m

def add_vessel_to_map(map_obj, mmsi, track_data):
    """
    Add vessel marker and track lines to map

    Args:
        map_obj: folium.Map object
        mmsi: Vessel MMSI
        track_data: Vessel track data with tiers
    """
    priority_level = track_data['priority_level']
    tiers = track_data['tiers']

    # Get current position (most recent point across all tiers)
    current_pos = get_current_position(tiers)
    if not current_pos:
        return  # No position data

    # Unified palette lookup (see CATEGORY_COLORS at top of module)
    color = _vessel_color(track_data)

    # Check if Norwegian civilian or buoy (no tracks for these)
    ship_type = track_data['ship_type'].lower()
    is_norwegian_civilian = (track_data['country'] == 'Norway' and
                            'military' not in ship_type and
                            'law enforcement' not in ship_type)
    is_buoy = track_data.get('is_buoy', False)
    skip_tracks = is_norwegian_civilian or is_buoy

    # Add track lines (tier-dependent visibility)
    add_track_lines(map_obj, mmsi, tiers, priority_level, color, skip_tracks)

    # Add vessel marker (current position)
    add_vessel_marker(map_obj, mmsi, track_data, current_pos, color)

def get_current_position(tiers):
    """Get most recent position across all tiers"""
    all_positions = (
        tiers.get('realtime', []) +
        tiers.get('tactical', []) +
        tiers.get('strategic', [])
    )

    if not all_positions:
        return None

    # Sort by timestamp and get latest
    all_positions.sort(key=lambda p: p['timestamp'], reverse=True)
    return all_positions[0]

def add_track_lines(map_obj, mmsi, tiers, priority_level, color, skip_tracks=False):
    """
    Add tiered track lines to map

    Track visibility by default:
    - High-risk (Russia/China/Norwegian military/Shadow fleet): Tier 1 + Tier 2 + Tier 3
    - Low-risk (Norwegian civilian, Buoys): NO TRACKS
    - Medium-risk (Other countries): Tier 3 only
    """
    # Skip tracks entirely for Norwegian civilian vessels and buoys
    if skip_tracks:
        return

    realtime = tiers.get('realtime', [])
    tactical = tiers.get('tactical', [])
    strategic = tiers.get('strategic', [])
    visible = priority_level == 'high'

    # Draw one continuous track sorted chronologically
    # Merge all tiers and render as single connected path
    # Skip bridge duplicates: tactical[0] = realtime[-1], strategic[0] = tactical[-1]
    all_positions = []

    if strategic:
        # Skip strategic[0] if it's a bridge duplicate from tactical
        strat_start = 1 if (tactical and len(strategic) > 0) else 0
        all_positions.extend([(p, 'strategic') for p in strategic[strat_start:]])

    if tactical:
        # Skip tactical[0] if it's a bridge duplicate from realtime
        tac_start = 1 if (realtime and len(tactical) > 0) else 0
        all_positions.extend([(p, 'tactical') for p in tactical[tac_start:]])

    if realtime:
        all_positions.extend([(p, 'realtime') for p in realtime])

    # Sort chronologically
    all_positions.sort(key=lambda x: x[0]['timestamp'])

    if len(all_positions) < 2:
        return

    # Build continuous track with style changes at tier boundaries
    i = 0
    while i < len(all_positions):
        tier_type = all_positions[i][1]
        segment = [all_positions[i][0]]

        # Collect all consecutive points of same tier
        j = i + 1
        while j < len(all_positions) and all_positions[j][1] == tier_type:
            segment.append(all_positions[j][0])
            j += 1

        # If next segment exists, include its first point for continuity
        if j < len(all_positions):
            segment.append(all_positions[j][0])

        # Draw segment with appropriate style
        if len(segment) > 1:
            coords = [[p['lat'], p['lon']] for p in segment]
            weight, opacity, dash = {
                'strategic': (2, 0.3, '3, 10'),
                'tactical': (3, 0.5, '10, 5'),
                'realtime': (4, 0.7, None)
            }[tier_type]

            folium.PolyLine(
                coords,
                color=color,
                weight=weight,
                opacity=opacity,
                dash_array=dash,
                smooth_factor=0,  # Disable smoothing to preserve exact connection points
                className=f"vessel-{mmsi} tier-{tier_type}"
            ).add_to(map_obj)

        i = j

def add_vessel_marker(map_obj, mmsi, track_data, current_pos, color):
    """Add current position marker for vessel"""

    # Country flag emojis
    country_flags = {
        'Russia': '🇷🇺',
        'China': '🇨🇳',
        'Norway': '🇳🇴'
    }
    flag = country_flags.get(track_data['country'], '🏴')

    # Calculate time since last AIS signal
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    signal_time = datetime.fromisoformat(current_pos['timestamp'].replace('Z', '')).replace(tzinfo=timezone.utc)
    time_diff = now - signal_time

    # Calculate hours since last signal for fade-out
    hours_since_signal = time_diff.total_seconds() / 3600

    # Format as human-readable time ago
    total_seconds = time_diff.total_seconds()
    if total_seconds < 60:
        last_signal = f"{int(total_seconds)} sec ago"
    elif total_seconds < 3600:
        last_signal = f"{int(total_seconds / 60)} min ago"
    elif total_seconds < 86400:
        last_signal = f"{int(total_seconds / 3600)} hr ago"
    else:
        last_signal = f"{int(total_seconds / 86400)} days ago"

    popup_html = f"""
    <div style="min-width: 200px;">
        <h4>{flag} {track_data['name']}</h4>
        <table>
            <tr><td><b>MMSI:</b></td><td>{mmsi}</td></tr>
            <tr><td><b>Country:</b></td><td>{track_data['country']}</td></tr>
            <tr><td><b>Type:</b></td><td>{track_data['ship_type']}</td></tr>
            <tr><td><b>Speed:</b></td><td>{current_pos['speed']:.1f} kts</td></tr>
            <tr><td><b>Course:</b></td><td>{current_pos['course']:.0f}°</td></tr>
            <tr><td><b>Last Signal:</b></td><td>{last_signal}</td></tr>
            <tr><td><b>Priority:</b></td><td>{track_data['priority_level'].upper()}</td></tr>
        </table>
        <p style="font-size: 10px; color: gray;">
            Click to focus on this vessel
        </p>
    </div>
    """

    # Set opacity and size based on priority level
    # Confirmed shadow fleet: highest opacity (same as Russia/China)
    # Suspected shadow fleet: medium opacity
    # High priority (Russia/China/Norwegian Military): full opacity, larger markers
    # Norwegian civilians: low opacity, smaller markers
    # Other countries: low opacity, smaller markers
    priority_level = track_data['priority_level']

    if priority_level == 'high' or track_data.get('is_shadow_fleet', False):
        # Russia, China, Confirmed Shadow Fleet, Norwegian Military
        base_fill_opacity = 0.8
        base_line_opacity = 0.95
        marker_radius = 8
    elif track_data.get('is_suspected_shadow', False):
        # Suspected shadow fleet (medium priority)
        base_fill_opacity = 0.6
        base_line_opacity = 0.75
        marker_radius = 6
    elif track_data['country'] == 'Norway':
        # Norwegian civilians
        base_fill_opacity = 0.25
        base_line_opacity = 0.35
        marker_radius = 5
    else:
        # Other countries (foreign vessels)
        base_fill_opacity = 0.3
        base_line_opacity = 0.4
        marker_radius = 5

    # Apply time-based fade-out (0-24h = full opacity, 24-168h = fade to 10%)
    fade_multiplier = calculate_opacity_multiplier(hours_since_signal)
    fill_opacity = base_fill_opacity * fade_multiplier
    line_opacity = base_line_opacity * fade_multiplier

    folium.CircleMarker(
        location=[current_pos['lat'], current_pos['lon']],
        radius=marker_radius,
        color=color,
        fill=True,
        fillColor=color,
        fillOpacity=fill_opacity,
        weight=2,
        opacity=line_opacity,
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=f"{flag} {track_data['name']}",
        className=f"vessel-marker vessel-{mmsi}"
    ).add_to(map_obj)

def add_focus_mode_script(map_obj, vessel_tracks):
    """Add JavaScript for vessel focus mode"""

    # Build vessel data map for JavaScript
    import json
    vessel_data_map = {}

    for mmsi, track_data in vessel_tracks.items():
        tiers = track_data['tiers']
        current_pos = get_current_position(tiers)

        if not current_pos:
            continue

        # Calculate time since last AIS signal
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        signal_time = datetime.fromisoformat(current_pos['timestamp'].replace('Z', '')).replace(tzinfo=timezone.utc)
        time_diff = now - signal_time

        total_seconds = time_diff.total_seconds()
        if total_seconds < 60:
            last_signal = f"{int(total_seconds)} sec ago"
        elif total_seconds < 3600:
            last_signal = f"{int(total_seconds / 60)} min ago"
        elif total_seconds < 86400:
            last_signal = f"{int(total_seconds / 3600)} hr ago"
        else:
            last_signal = f"{int(total_seconds / 86400)} days ago"

        # Get flag emoji
        country_flags = {'Russia': '🇷🇺', 'China': '🇨🇳', 'Norway': '🇳🇴'}
        flag = country_flags.get(track_data['country'], '🏴')

        vessel_data_map[mmsi] = {
            'name': f"{flag} {track_data['name']}",
            'mmsi': mmsi,
            'country': track_data['country'],
            'type': track_data['ship_type'],
            'speed': f"{current_pos['speed']:.1f} kts",
            'course': f"{current_pos['course']:.0f}°",
            'lastSignal': last_signal,
            'priority': track_data['priority_level'].upper(),
            'lat': current_pos['lat'],
            'lon': current_pos['lon'],
        }

    vessel_data_json = json.dumps(vessel_data_map)

    focus_script = """
    <!-- Vessel Info Panel (center-left, initially hidden) -->
    <div id="vessel-info-panel" style="display: none; position: fixed; top: 50%; left: 10px; transform: translateY(-50%); width: 250px; z-index: 10000; background-color: white; padding: 15px; border: 2px solid #333; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.3);">
        <h4 id="vessel-info-name" style="margin: 0 0 10px 0;"></h4>
        <table style="width: 100%; font-size: 12px;">
            <tr><td><b>MMSI:</b></td><td id="vessel-info-mmsi"></td></tr>
            <tr><td><b>Country:</b></td><td id="vessel-info-country"></td></tr>
            <tr><td><b>Type:</b></td><td id="vessel-info-type"></td></tr>
            <tr><td><b>Speed:</b></td><td id="vessel-info-speed"></td></tr>
            <tr><td><b>Course:</b></td><td id="vessel-info-course"></td></tr>
            <tr><td><b>Last Signal:</b></td><td id="vessel-info-signal"></td></tr>
            <tr><td><b>Priority:</b></td><td id="vessel-info-priority"></td></tr>
        </table>
        <p style="font-size: 10px; color: gray; margin-top: 10px;">
            Click map or vessel to close
        </p>
    </div>

    <script>
    // Vessel data map (generated from Python)
    const vesselDataMap = """ + vessel_data_json + """;

    // Focus mode: Click vessel to highlight and show all tiers
    let focusedVessel = null;

    // Locate the Leaflet map instance that Folium creates as window.map_<hash>
    function getLeafletMap() {
        try {
            const key = Object.keys(window).find(function (k) {
                return k.startsWith('map_') && window[k] instanceof L.Map;
            });
            return key ? window[key] : null;
        } catch (e) {
            console.warn('getLeafletMap failed:', e);
            return null;
        }
    }

    // Pan and zoom the map to a given lat/lon with a smooth animation
    function panMapTo(lat, lon, zoom) {
        const mapInstance = getLeafletMap();
        if (mapInstance && lat != null && lon != null) {
            mapInstance.flyTo([lat, lon], zoom || 9, { duration: 0.8 });
            console.log('Map flying to', lat, lon);
        } else {
            console.warn('panMapTo skipped — map or coords missing', {mapInstance: !!mapInstance, lat, lon});
        }
    }

    // Define focus/unfocus functions in global scope (so postMessage can access them)
    // Optional hintLat/hintLon come from the parent dashboard (from anomaly details); if
    // absent, fall back to vesselDataMap. Handles rendezvous anomalies gracefully.
    function focusVessel(mmsi, hintLat, hintLon) {
        console.log('=== FOCUS VESSEL CALLED ===');
        console.log('MMSI:', mmsi, 'hint:', hintLat, hintLon);

        // Unfocus previous vessel
        if (focusedVessel) {
            console.log('Unfocusing previous vessel:', focusedVessel);
            unfocusAll();
        }

        focusedVessel = mmsi;
        console.log('Set focusedVessel to:', focusedVessel);

        // Get vessel data from vessel data map
        console.log('Looking up vessel data in vesselDataMap...');
        console.log('vesselDataMap keys sample:', Object.keys(vesselDataMap).slice(0, 5));
        console.log('Looking for key:', mmsi);

        const vData = vesselDataMap[mmsi];
        console.log('Vessel data lookup result:', vData ? 'FOUND' : 'NOT FOUND');

        if (vData) {
            console.log('Vessel data:', vData);
            // Populate info panel
            document.getElementById('vessel-info-name').textContent = vData.name;
            document.getElementById('vessel-info-mmsi').textContent = vData.mmsi;
            document.getElementById('vessel-info-country').textContent = vData.country;
            document.getElementById('vessel-info-type').textContent = vData.type;
            document.getElementById('vessel-info-speed').textContent = vData.speed;
            document.getElementById('vessel-info-course').textContent = vData.course;
            document.getElementById('vessel-info-signal').textContent = vData.lastSignal;
            document.getElementById('vessel-info-priority').textContent = vData.priority;

            // Show info panel
            document.getElementById('vessel-info-panel').style.display = 'block';
            console.log('Info panel displayed');
        } else {
            console.warn('⚠️ Vessel data not found for MMSI:', mmsi);
            console.log('Available MMSI keys:', Object.keys(vesselDataMap));
        }

        // Pan/zoom the map to the vessel. Prefer hint coordinates from the parent
        // (which come from anomaly.details.last_position etc.); fall back to the
        // vessel's current position in vesselDataMap. Rendezvous anomalies lack
        // position data, so the fallback keeps click-to-navigate working.
        const panLat = (hintLat != null) ? hintLat : (vData ? vData.lat : null);
        const panLon = (hintLon != null) ? hintLon : (vData ? vData.lon : null);
        panMapTo(panLat, panLon, 9);

        // Collect focused vessel's track lines for reordering
        const focusedTracks = [];

        console.log('Searching for DOM elements with class: vessel-' + mmsi);
        const allInteractive = document.querySelectorAll('.leaflet-interactive');
        console.log('Total .leaflet-interactive elements:', allInteractive.length);

        let matchedCount = 0;

        // Fade all other vessels and collect focused tracks
        document.querySelectorAll('.leaflet-interactive').forEach(function(el) {
            // Skip elements that are hidden by layer control
            const computedStyle = window.getComputedStyle(el);
            if (computedStyle.display === 'none') {
                return; // Skip hidden elements
            }

            const className = el.getAttribute('class') || '';

            if (!className.includes('vessel-' + mmsi)) {
                // Not the focused vessel - fade it (but keep visible)
                el.style.opacity = '0.4';
                el.style.strokeOpacity = '0.4';
                el.style.fillOpacity = '0.4';
            } else {
                // Focused vessel - highlight it with !important to override layer styles
                matchedCount++;
                console.log('✓ Matched element ' + matchedCount + ':', el.tagName, 'className:', className);

                el.style.setProperty('opacity', '1.0', 'important');
                el.style.setProperty('stroke-opacity', '1.0', 'important');
                el.style.setProperty('fill-opacity', '1.0', 'important');

                // For track lines (path elements), make them bolder
                if (el.tagName.toLowerCase() === 'path') {
                    // Store original weight if not already stored
                    if (!el.getAttribute('data-original-stroke-width')) {
                        const currentWeight = el.getAttribute('stroke-width') || '3';
                        el.setAttribute('data-original-stroke-width', currentWeight);
                    }

                    // Make track bolder (increase by 2)
                    const originalWeight = parseFloat(el.getAttribute('data-original-stroke-width') || '3');
                    el.setAttribute('stroke-width', (originalWeight + 2).toString());

                    // Collect for DOM reordering
                    focusedTracks.push(el);
                } else {
                    // For marker (circle), increase size
                    el.style.strokeWidth = '4';
                    el.style.zIndex = '1000';
                }
            }
        });

        // Bring focused vessel's tracks to front by re-appending them
        // This moves them to the end of the SVG container, rendering on top
        focusedTracks.forEach(function(track) {
            if (track.parentNode) {
                track.parentNode.appendChild(track);
            }
        });

        console.log('=== FOCUS VESSEL COMPLETE ===');
        console.log('Total matched elements:', matchedCount);
        console.log('Vessel data found:', vData ? 'YES' : 'NO');
        console.log('=============================');
    }

    function unfocusAll() {
        console.log('Unfocusing all vessels');

        focusedVessel = null;

        // Hide info panel
        document.getElementById('vessel-info-panel').style.display = 'none';

        // Restore all elements to default opacity and weights
        document.querySelectorAll('.leaflet-interactive').forEach(function(el) {
            el.style.opacity = '';
            el.style.strokeOpacity = '';
            el.style.fillOpacity = '';
            el.style.strokeWidth = '';
            el.style.zIndex = '';

            // Restore original track line weight
            if (el.tagName.toLowerCase() === 'path') {
                const originalWeight = el.getAttribute('data-original-stroke-width');
                if (originalWeight) {
                    el.setAttribute('stroke-width', originalWeight);
                }
            }
        });
    }

    // Wait for map to load
    setTimeout(function() {
        // Add click handlers to all vessel markers (CircleMarkers render as .vessel-marker)
        document.querySelectorAll('.vessel-marker').forEach(function(marker) {
            marker.addEventListener('click', function(e) {
                // Extract MMSI from className (e.g., "vessel-marker vessel-258123000")
                const classes = (this.getAttribute('class') || '').split(' ');
                const vesselClass = classes.find(c => c.startsWith('vessel-') && c !== 'vessel-marker');
                const vesselMmsi = vesselClass ? vesselClass.replace('vessel-', '') : null;

                if (!vesselMmsi) return;

                if (focusedVessel === vesselMmsi) {
                    // Unfocus if clicking same vessel
                    unfocusAll();
                } else {
                    // Focus on new vessel
                    focusVessel(vesselMmsi);
                }

                e.stopPropagation();
            });
        });

        // Add click handlers to track polylines (paths with vessel-{mmsi} className)
        document.querySelectorAll('path[class*="vessel-"]').forEach(function(track) {
            const className = track.getAttribute('class') || '';

            // Skip if it's a marker (already handled above)
            if (className.includes('vessel-marker')) return;

            // Extract MMSI from vessel-{mmsi} class (e.g., "vessel-258123000 tier-tactical")
            const classes = className.split(' ');
            const vesselClass = classes.find(c => /^vessel-\d+$/.test(c));
            if (!vesselClass) return;

            track.addEventListener('click', function(e) {
                const vesselMmsi = vesselClass.replace('vessel-', '');

                if (focusedVessel === vesselMmsi) {
                    // Unfocus if clicking same vessel's track
                    unfocusAll();
                } else {
                    // Focus on vessel
                    focusVessel(vesselMmsi);
                }

                e.stopPropagation();
            });
        });

        // Click map to unfocus all
        document.querySelector('.leaflet-container').addEventListener('click', function(e) {
            // Only unfocus if clicking on the map itself (not a marker or track)
            const isVesselElement = e.target.classList.contains('vessel-marker') ||
                                   (e.target.getAttribute('class') || '').includes('vessel-');
            if (focusedVessel && !isVesselElement) {
                unfocusAll();
            }
        });
    }, 1000);
    </script>
    """

    map_obj.get_root().html.add_child(folium.Element(focus_script))
