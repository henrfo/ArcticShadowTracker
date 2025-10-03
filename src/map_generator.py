"""
Focus Mode Map Generator
Creates interactive Folium maps with tier-based track visualization:
  - High-risk vessels: Full tracks (all tiers)
  - Medium/low-risk vessels: Strategic tier only
  - Click vessel to focus (shows all tiers)
"""

import folium
from datetime import datetime
from zoneinfo import ZoneInfo

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

    # Count vessels by risk
    risk_counts = {'high': 0, 'medium': 0, 'low': 0}

    # Separate vessels by priority for z-order (render low priority first, then high)
    low_priority_vessels = []
    high_priority_vessels = []

    for mmsi, track_data in vessel_tracks.items():
        priority_level = track_data['priority_level']
        risk_counts[priority_level] += 1

        # Check if it's a regular Norwegian vessel (gray, not military)
        ship_type = track_data['ship_type'].lower()
        is_norwegian_civilian = (track_data['country'] == 'Norway' and
                                 'military' not in ship_type and
                                 'law enforcement' not in ship_type)

        if is_norwegian_civilian:
            low_priority_vessels.append((mmsi, track_data))
        else:
            high_priority_vessels.append((mmsi, track_data))

    # Add vessels in z-order: Norwegian civilians first (bottom), then others (top)
    for mmsi, track_data in low_priority_vessels:
        add_vessel_to_map(m, mmsi, track_data)

    for mmsi, track_data in high_priority_vessels:
        add_vessel_to_map(m, mmsi, track_data)

    # Add legend and focus mode controls
    add_legend(m, risk_counts, len(vessel_tracks))
    add_focus_mode_script(m)

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
    if track_data['country'] == 'Russia':
        color = '#d32f2f'      # Red
    elif track_data['country'] == 'China':
        color = '#ff9800'      # Orange
    elif track_data['country'] == 'Norway':
        # Check if Norwegian military or law enforcement
        ship_type = track_data['ship_type'].lower()
        if 'military' in ship_type or 'law enforcement' in ship_type:
            color = '#000000'  # Black for Norwegian military/law enforcement
        else:
            color = '#888888'  # Gray for other Norwegian vessels
    elif priority_level == 'low':
        color = '#9e9e9e'      # Gray
    else:
        color = '#ffa726'      # Medium orange

    # Add track lines (tier-dependent visibility)
    add_track_lines(map_obj, mmsi, tiers, priority_level, color)

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

def add_track_lines(map_obj, mmsi, tiers, priority_level, color):
    """
    Add tiered track lines to map

    Track visibility by default:
    - High-risk (Russia/China/Norwegian military): Tier 1 + Tier 2 + Tier 3
    - Low-risk (Norwegian civilian): Tier 3 only
    """
    realtime = tiers.get('realtime', [])
    tactical = tiers.get('tactical', [])
    strategic = tiers.get('strategic', [])
    visible = priority_level == 'high'

    # Draw one continuous track sorted chronologically
    # Merge all tiers and render as single connected path
    all_positions = []

    if strategic:
        all_positions.extend([(p, 'strategic') for p in strategic])
    if tactical:
        all_positions.extend([(p, 'tactical') for p in tactical])
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
                'tactical': (3, 0.7 if visible else 0, '10, 5'),
                'realtime': (4, 0.9 if visible else 0, None)
            }[tier_type]

            folium.PolyLine(
                coords,
                color=color,
                weight=weight,
                opacity=opacity,
                dash_array=dash,
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

    # Set opacity and size based on country and ship type
    # Norwegian military/law enforcement: full size with normal opacity
    # Other Norwegian: smaller with lower opacity
    ship_type = track_data['ship_type'].lower()
    is_norwegian_military = (track_data['country'] == 'Norway' and
                             ('military' in ship_type or 'law enforcement' in ship_type))

    if is_norwegian_military:
        fill_opacity = 0.7
        line_opacity = 0.9
        marker_radius = 8
    elif track_data['country'] == 'Norway':
        fill_opacity = 0.3
        line_opacity = 0.4
        marker_radius = 5
    else:
        fill_opacity = 0.7
        line_opacity = 0.9
        marker_radius = 8

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
    """Add legend and statistics to map"""
    legend_html = f"""
    <div style="position: fixed; top: 10px; right: 10px; z-index: 9999;
                background-color: white; padding: 15px; border: 2px solid #333;
                border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 10px 0;">Arctic Intelligence</h4>
        <p style="margin: 5px 0; font-size: 12px;"><b>Total Vessels:</b> {total_vessels}</p>
        <p style="margin: 5px 0; font-size: 11px; color: #666;">
            Last update: {datetime.now(ZoneInfo('Europe/Oslo')).strftime('%Y-%m-%d %H:%M %Z')}
        </p>
        <hr style="margin: 10px 0;">
        <p style="margin: 5px 0; font-size: 10px; color: #999;">
            <b>Track Lines:</b><br>
            ━━━ Real-time (0-2hr)<br>
            ╌╌╌ Tactical (2-48hr)<br>
            ··· Strategic (2-7d)
        </p>
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
