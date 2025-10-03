"""
Focus Mode Map Generator
Creates interactive Folium maps with tier-based track visualization:
  - High-risk vessels: Full tracks (all tiers)
  - Medium/low-risk vessels: Strategic tier only
  - Click vessel to focus (shows all tiers)
"""

import folium
from datetime import datetime, timezone

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

    # Add each vessel
    for mmsi, track_data in vessel_tracks.items():
        risk_level = track_data['risk_level']
        risk_counts[risk_level] += 1

        # Add vessel marker and tracks
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
    risk_level = track_data['risk_level']
    tiers = track_data['tiers']

    # Get current position (most recent point across all tiers)
    current_pos = get_current_position(tiers)
    if not current_pos:
        return  # No position data

    # Color scheme by risk
    colors = {
        'high': '#d32f2f',      # Red
        'medium': '#ffa726',    # Orange
        'low': '#9e9e9e'        # Gray
    }
    color = colors[risk_level]

    # Add track lines (tier-dependent visibility)
    add_track_lines(map_obj, mmsi, tiers, risk_level, color)

    # Add event markers (strategic tier only)
    add_event_markers(map_obj, mmsi, tiers.get('strategic', []), color)

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

def add_track_lines(map_obj, mmsi, tiers, risk_level, color):
    """
    Add tiered track lines to map

    Track visibility by default:
    - High-risk: Tier 1 + Tier 2 + Tier 3
    - Medium/low-risk: Tier 3 only
    """
    # Tier 1 (Realtime): Solid thick line (high-risk only by default)
    realtime = tiers.get('realtime', [])
    if realtime and len(realtime) > 1:
        coords = [[p['lat'], p['lon']] for p in realtime]
        visible = risk_level == 'high'

        folium.PolyLine(
            coords,
            color=color,
            weight=4,
            opacity=0.9 if visible else 0,
            popup=f"Real-time track ({len(coords)} points)",
            className=f"vessel-{mmsi} tier-realtime" + (" high-risk" if risk_level == 'high' else "")
        ).add_to(map_obj)

    # Tier 2 (Tactical): Dashed medium line (high-risk only by default)
    tactical = tiers.get('tactical', [])
    if tactical and len(tactical) > 1:
        coords = [[p['lat'], p['lon']] for p in tactical]
        visible = risk_level == 'high'

        folium.PolyLine(
            coords,
            color=color,
            weight=3,
            opacity=0.7 if visible else 0,
            dash_array='10, 5',
            popup=f"Tactical track ({len(coords)} points)",
            className=f"vessel-{mmsi} tier-tactical" + (" high-risk" if risk_level == 'high' else "")
        ).add_to(map_obj)

    # Tier 3 (Strategic): Dotted thin line (always visible for all vessels)
    strategic = tiers.get('strategic', [])
    if strategic and len(strategic) > 1:
        coords = [[p['lat'], p['lon']] for p in strategic]

        folium.PolyLine(
            coords,
            color=color,
            weight=2,
            opacity=0.5,
            dash_array='3, 10',
            popup=f"Strategic track ({len(coords)} points)",
            className=f"vessel-{mmsi} tier-strategic"
        ).add_to(map_obj)

def add_event_markers(map_obj, mmsi, strategic_positions, color):
    """Add event markers for strategic tier positions"""
    for pos in strategic_positions:
        if 'event' in pos:
            icon_map = {
                'stop': 'pause',
                'resume': 'play',
                'course_change': 'arrow-turn-right',
                'speed_change': 'gauge-high',
                'day_start': 'circle',
                'day_end': 'circle'
            }

            icon = icon_map.get(pos['event'], 'info')

            # Only show prominent events (skip day bookends)
            if pos['event'] in ['stop', 'resume', 'course_change', 'speed_change']:
                event_label = pos['event'].replace('_', ' ').title()
                delta_info = f" ({pos.get('delta', '')})" if 'delta' in pos else ""

                folium.Marker(
                    location=[pos['lat'], pos['lon']],
                    icon=folium.Icon(color='lightgray', icon=icon, prefix='fa'),
                    popup=f"{event_label}{delta_info}",
                    className=f"vessel-{mmsi} event-marker"
                ).add_to(map_obj)

def add_vessel_marker(map_obj, mmsi, track_data, current_pos, color):
    """Add current position marker for vessel"""
    risk_icons = {
        'high': 'ship',
        'medium': 'ship',
        'low': 'ship'
    }

    popup_html = f"""
    <div style="min-width: 200px;">
        <h4>{track_data['name']}</h4>
        <table>
            <tr><td><b>MMSI:</b></td><td>{mmsi}</td></tr>
            <tr><td><b>Country:</b></td><td>{track_data['country']}</td></tr>
            <tr><td><b>Type:</b></td><td>{track_data['ship_type']}</td></tr>
            <tr><td><b>Speed:</b></td><td>{current_pos['speed']:.1f} kts</td></tr>
            <tr><td><b>Course:</b></td><td>{current_pos['course']:.0f}°</td></tr>
            <tr><td><b>Risk:</b></td><td>{track_data['risk_level'].upper()}</td></tr>
        </table>
        <p style="font-size: 10px; color: gray;">
            Click to focus on this vessel
        </p>
    </div>
    """

    folium.Marker(
        location=[current_pos['lat'], current_pos['lon']],
        icon=folium.Icon(
            color='red' if track_data['risk_level'] == 'high' else 'orange' if track_data['risk_level'] == 'medium' else 'gray',
            icon=risk_icons[track_data['risk_level']],
            prefix='fa'
        ),
        popup=folium.Popup(popup_html, max_width=300),
        tooltip=track_data['name'],
        className=f"vessel-marker"
    ).add_to(map_obj).add_child(folium.Element(f'<script>this.options.vesselMmsi = "{mmsi}";</script>'))

def add_legend(map_obj, risk_counts, total_vessels):
    """Add legend and statistics to map"""
    legend_html = f"""
    <div style="position: fixed; top: 10px; right: 10px; z-index: 9999;
                background-color: white; padding: 15px; border: 2px solid #333;
                border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.3);">
        <h4 style="margin: 0 0 10px 0;">Arctic Intelligence</h4>
        <p style="margin: 5px 0;"><span style="color: #d32f2f;">●</span> High Risk: {risk_counts['high']} (Russia/China)</p>
        <p style="margin: 5px 0;"><span style="color: #ffa726;">●</span> Medium Risk: {risk_counts['medium']}</p>
        <p style="margin: 5px 0;"><span style="color: #9e9e9e;">●</span> Low Risk: {risk_counts['low']} (Norwegian)</p>
        <hr style="margin: 10px 0;">
        <p style="margin: 5px 0; font-size: 12px;"><b>Total Vessels:</b> {total_vessels}</p>
        <p style="margin: 5px 0; font-size: 11px; color: #666;">
            Last update: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
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
