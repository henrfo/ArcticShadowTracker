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

def generate_focused_map(vessel_tracks):
    """
    Generate interactive map with focus mode

    Args:
        vessel_tracks: Dict of vessel track data (from track_manager)

    Returns:
        folium.Map object
    """
    # Center on Arctic region
    m = folium.Map(
        location=[75, 20],
        zoom_start=5,
        tiles='OpenStreetMap'
    )

    # Add Arctic coverage area
    folium.Rectangle(
        bounds=[[65, 0], [82, 40]],
        color='blue',
        fill=False,
        weight=2,
        opacity=0.3,
        popup='Arctic Coverage Area: 65-82°N, 0-40°E'
    ).add_to(m)

    # Create feature groups for toggleable layers
    russia_layer = folium.FeatureGroup(name='Russia', show=True)
    shadow_fleet_layer = folium.FeatureGroup(name='Shadow Fleet', show=True)
    suspected_shadow_layer = folium.FeatureGroup(name='Suspected Shadow Fleet', show=True)
    china_layer = folium.FeatureGroup(name='China', show=True)
    norwegian_military_layer = folium.FeatureGroup(name='Norwegian Military/Law', show=True)
    norway_layer = folium.FeatureGroup(name='Norway (Civilian)', show=True)
    other_layer = folium.FeatureGroup(name='Other Countries', show=True)

    # Add submarine cables layer
    cables_layer = folium.FeatureGroup(name='Submarine Cables', show=True)
    cables_geojson = load_submarine_cables()
    if cables_geojson['features']:
        folium.GeoJson(
            cables_geojson,
            style_function=lambda feature: {
                'color': '#9C27B0',  # Purple for all submarine cables
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

    # Count vessels by risk
    risk_counts = {'high': 0, 'medium': 0, 'low': 0}

    # Separate vessels by priority for z-order (render low priority first, then high)
    # Z-order (bottom to top): Other -> Norway civilians -> Suspected Shadow -> Norwegian Military -> China -> Confirmed Shadow -> Russia
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
        if track_data.get('is_shadow_fleet', False):
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
    # Order matches "By Country" sidebar: Russia, Shadow Fleet, Suspected Shadow Fleet, China, Norwegian Military/Law, Norway, Other
    # Layers added in this order for LayerControl display
    other_layer.add_to(m)
    norway_layer.add_to(m)
    norwegian_military_layer.add_to(m)
    china_layer.add_to(m)
    suspected_shadow_layer.add_to(m)
    shadow_fleet_layer.add_to(m)
    russia_layer.add_to(m)

    # Add focus mode controls
    add_focus_mode_script(m)

    # Add layer control to toggle all categories
    folium.LayerControl(position='topright', collapsed=False).add_to(m)

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

    # Color scheme by priority and country
    if track_data.get('is_shadow_fleet', False):
        color = '#c62828'      # Dark red for confirmed shadow fleet
    elif track_data.get('is_suspected_shadow', False):
        color = '#ff5722'      # Orange-red for suspected shadow fleet
    elif track_data['country'] == 'Russia':
        color = '#d32f2f'      # Red
    elif track_data['country'] == 'China':
        color = '#ff9800'      # Orange
    elif track_data['country'] == 'Norway':
        # Check if Norwegian military or law enforcement
        ship_type = track_data['ship_type'].lower()
        if 'military' in ship_type or 'law enforcement' in ship_type:
            color = '#2E7D32'  # Dark green for Norwegian military/law enforcement
        else:
            color = '#888888'  # Gray for other Norwegian vessels
    elif priority_level == 'low':
        color = '#9e9e9e'      # Gray
    else:
        color = '#2196F3'      # Blue for "Other" countries

    # Check if Norwegian civilian (no tracks for these)
    ship_type = track_data['ship_type'].lower()
    is_norwegian_civilian = (track_data['country'] == 'Norway' and
                            'military' not in ship_type and
                            'law enforcement' not in ship_type)

    # Add track lines (tier-dependent visibility)
    add_track_lines(map_obj, mmsi, tiers, priority_level, color, is_norwegian_civilian)

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

def add_track_lines(map_obj, mmsi, tiers, priority_level, color, is_norwegian_civilian=False):
    """
    Add tiered track lines to map

    Track visibility by default:
    - High-risk (Russia/China/Norwegian military/Shadow fleet): Tier 1 + Tier 2 + Tier 3
    - Low-risk (Norwegian civilian): NO TRACKS
    - Medium-risk (Other countries): Tier 3 only
    """
    # Skip tracks entirely for Norwegian civilian vessels
    if is_norwegian_civilian:
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
                'strategic': (2, 0.5, '3, 10'),
                'tactical': (3, 0.7, '10, 5'),
                'realtime': (4, 0.9, None)
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

    popup_html = f"""
    <div style="min-width: 200px;">
        <h4>{flag} {track_data['name']}</h4>
        <table>
            <tr><td><b>MMSI:</b></td><td>{mmsi}</td></tr>
            <tr><td><b>Country:</b></td><td>{track_data['country']}</td></tr>
            <tr><td><b>Type:</b></td><td>{track_data['ship_type']}</td></tr>
            <tr><td><b>Speed:</b></td><td>{current_pos['speed']:.1f} kts</td></tr>
            <tr><td><b>Course:</b></td><td>{current_pos['course']:.0f}°</td></tr>
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
        fill_opacity = 0.8
        line_opacity = 0.95
        marker_radius = 8
    elif track_data.get('is_suspected_shadow', False):
        # Suspected shadow fleet (medium priority)
        fill_opacity = 0.6
        line_opacity = 0.75
        marker_radius = 6
    elif track_data['country'] == 'Norway':
        # Norwegian civilians
        fill_opacity = 0.25
        line_opacity = 0.35
        marker_radius = 5
    else:
        # Other countries (foreign vessels)
        fill_opacity = 0.3
        line_opacity = 0.4
        marker_radius = 5

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
        className=f"vessel-marker"
    ).add_to(map_obj).add_child(folium.Element(f'<script>this.options.vesselMmsi = "{mmsi}";</script>'))

def add_legend(map_obj, risk_counts, total_vessels):
    """Add legend and statistics to map (left sidebar, scrollable)"""
    legend_html = f"""
    <div style="position: fixed;
                top: 10px;
                left: 10px;
                bottom: 10px;
                width: 250px;
                z-index: 9999;
                background-color: white;
                padding: 15px;
                border: 2px solid #333;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.3);
                overflow-y: auto;
                overflow-x: hidden;">
        <h4 style="margin: 0 0 10px 0;">Arctic Intelligence</h4>
        <p style="margin: 5px 0; font-size: 12px;"><b>Total Vessels:</b> {total_vessels}</p>
        <p style="margin: 5px 0; font-size: 11px; color: #666;">
            Last update: {datetime.now(ZoneInfo('Europe/Oslo')).strftime('%Y-%m-%d %H:%M %Z')}
        </p>
        <hr style="margin: 10px 0;">
        <h5 style="margin: 10px 0 5px 0; font-size: 13px;">Data Tiers</h5>
        <p style="margin: 3px 0; font-size: 11px; line-height: 1.6;">
            <span style="color: #333; font-weight: bold;">━━━</span> Realtime (0-2hr)<br>
            <span style="color: #333; font-weight: bold;">╌╌╌</span> Tactical (2-48hr)<br>
            <span style="color: #333; font-weight: bold;">···</span> Strategic (2-7d)<br>
            <span style="color: #9C27B0; font-weight: bold;">━ ━</span> Submarine Cables
        </p>
        <hr style="margin: 10px 0;">
        <p style="margin: 10px 0 5px 0; font-size: 10px; color: #999;">
            💡 Click vessel to focus
        </p>
    </div>
    """

    map_obj.get_root().html.add_child(folium.Element(legend_html))

def add_focus_mode_script(map_obj):
    """Add JavaScript for vessel focus mode"""
    focus_script = """
    <script>
    // Focus mode: Click vessel to highlight and show all tiers
    let focusedVessel = null;

    // Wait for map to load
    setTimeout(function() {
        // Add click handlers to all vessel markers
        document.querySelectorAll('.leaflet-marker-icon').forEach(function(marker) {
            marker.addEventListener('click', function(e) {
                // Get MMSI from marker (injected in add_vessel_marker)
                const vesselMmsi = this.vesselMmsi || null;

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

        // Double-click map to unfocus all
        document.querySelector('.leaflet-container').addEventListener('dblclick', function(e) {
            if (focusedVessel) {
                unfocusAll();
                e.preventDefault();
            }
        });
    }, 1000);

    function focusVessel(mmsi) {
        console.log('Focusing vessel:', mmsi);

        // Unfocus previous vessel
        if (focusedVessel) {
            unfocusAll();
        }

        focusedVessel = mmsi;

        // Fade all other vessels
        document.querySelectorAll('.leaflet-interactive').forEach(function(el) {
            const className = el.getAttribute('class') || '';

            if (!className.includes('vessel-' + mmsi)) {
                // Not the focused vessel - fade it
                el.style.opacity = '0.15';
                el.style.strokeOpacity = '0.15';
                el.style.fillOpacity = '0.15';
            } else {
                // Focused vessel - highlight it
                el.style.opacity = '1.0';
                el.style.strokeOpacity = '1.0';
                el.style.fillOpacity = '1.0';
                el.style.strokeWidth = '4';
                el.style.zIndex = '1000';
            }
        });
    }

    function unfocusAll() {
        console.log('Unfocusing all vessels');

        focusedVessel = null;

        // Restore all elements to default opacity
        document.querySelectorAll('.leaflet-interactive').forEach(function(el) {
            el.style.opacity = '';
            el.style.strokeOpacity = '';
            el.style.fillOpacity = '';
            el.style.strokeWidth = '';
            el.style.zIndex = '';
        });
    }
    </script>
    """

    map_obj.get_root().html.add_child(folium.Element(focus_script))
