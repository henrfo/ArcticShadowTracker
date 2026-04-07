/* ==========================================================================
   SAR Analysis View — standalone Leaflet page logic.
   Loaded by templates/analysis.html (served at /analysis-view).

   Fetches SAR tiles + AIS vessels + CFAR detections, draws tiles as
   ImageOverlays, overlays AIS markers (±60 min), and renders CFAR
   detections as color-coded circle markers with bounding boxes.
   ========================================================================== */
(function () {
  'use strict';

  const MATCH_WINDOW_MS = 60 * 60 * 1000; // ±60 min around each SAR acquisition
  const ARCTIC_CENTER = [74.0, 20.0];
  const ARCTIC_ZOOM = 4;

  // --------------------------------------------------------------------------
  // Vessel color mapping — port of src/map_generator.py:21-71
  // --------------------------------------------------------------------------
  function vesselColor(v) {
    if (!v) return '#2196F3';
    if (v.is_buoy) return '#616161';
    if (v.is_shadow_fleet) return '#c62828';
    if (v.is_suspected_shadow) return '#ff5722';
    const country = v.country || '';
    const shipType = (v.ship_type || '').toLowerCase();
    if (country === 'Norway' && (shipType.includes('military') || shipType.includes('law enforcement'))) {
      return '#2E7D32';
    }
    if (country === 'Russia') return '#d32f2f';
    if (country === 'China') return '#ff9800';
    if (country === 'Norway') return '#888888';
    return '#2196F3';
  }

  function vesselRadius(v) {
    if (!v) return 5;
    if (v.is_shadow_fleet || v.country === 'Russia' || v.country === 'China') return 7;
    if (v.is_suspected_shadow) return 6;
    return 5;
  }

  function vesselCategory(v) {
    if (!v) return 'other';
    if (v.is_buoy) return 'buoy';
    if (v.is_shadow_fleet) return 'shadow_fleet';
    if (v.is_suspected_shadow) return 'suspected_shadow';
    const country = v.country || '';
    const shipType = (v.ship_type || '').toLowerCase();
    if (country === 'Norway' && (shipType.includes('military') || shipType.includes('law enforcement'))) return 'norway_mil';
    if (country === 'Russia') return 'russia';
    if (country === 'China') return 'china';
    if (country === 'Norway') return 'norway';
    return 'other';
  }

  const COUNTRY_FLAG = { Russia: '\u{1F1F7}\u{1F1FA}', China: '\u{1F1E8}\u{1F1F3}', Norway: '\u{1F1F3}\u{1F1F4}' };

  // --------------------------------------------------------------------------
  // Detection color logic
  // --------------------------------------------------------------------------
  function detectionRadius(det) {
    return 12 + (det.confidence_db || 0) * 0.5;
  }

  // --------------------------------------------------------------------------
  // Formatting helpers
  // --------------------------------------------------------------------------
  function formatTileTime(iso) {
    if (!iso) return 'Unknown';
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[d.getUTCMonth()]} ${String(d.getUTCDate()).padStart(2,'0')}, ${String(d.getUTCHours()).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')} UTC`;
  }

  function formatBboxShort(bbox) {
    if (!bbox || bbox.length !== 4) return '';
    const [minLon, minLat, maxLon, maxLat] = bbox;
    return `${minLon.toFixed(1)}\u00B0E\u2013${maxLon.toFixed(1)}\u00B0E \u00B7 ${minLat.toFixed(1)}\u00B0N\u2013${maxLat.toFixed(1)}\u00B0N`;
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function minutesDiff(isoA, isoB) {
    const a = new Date(isoA).getTime();
    const b = new Date(isoB).getTime();
    if (isNaN(a) || isNaN(b)) return null;
    return Math.round((a - b) / 60000);
  }

  // --------------------------------------------------------------------------
  // State
  // --------------------------------------------------------------------------
  let map;
  let tileLayers = new Map();   // tile.id -> { tile, layer, visible }
  let vesselLayer;               // L.LayerGroup — AIS markers
  let detectionLayer;            // L.LayerGroup — dark vessel markers only
  let bboxLayer;                 // L.LayerGroup — detection bounding boxes
  let connectionLayer;           // L.LayerGroup — lines connecting detections to matched AIS
  let vesselsData = {};          // mmsi -> vessel
  let tilesData = [];            // tile objects from /api/satellite-tiles
  let detectionsRaw = [];        // tile records from /api/satellite-detections
  let allDetections = [];        // flattened detection list
  let vesselPositions = {};      // mmsi -> [lat, lon] of rendered AIS position

  // --------------------------------------------------------------------------
  // Map init
  // --------------------------------------------------------------------------
  function initMap() {
    map = L.map('analysis-map', {
      center: ARCTIC_CENTER,
      zoom: ARCTIC_ZOOM,
      zoomControl: true,
      preferCanvas: true,
      worldCopyJump: false,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 19,
    }).addTo(map);

    vesselLayer = L.layerGroup().addTo(map);
    detectionLayer = L.layerGroup().addTo(map);
    bboxLayer = L.layerGroup(); // starts hidden
    connectionLayer = L.layerGroup(); // starts hidden
  }

  // --------------------------------------------------------------------------
  // Tile overlays
  // --------------------------------------------------------------------------
  function addTileOverlays(tiles) {
    tileLayers.clear();
    const allBounds = [];
    tiles.forEach(t => {
      if (!t.bbox || t.bbox.length !== 4 || !t.thumbnail_url) return;
      const [minLon, minLat, maxLon, maxLat] = t.bbox;
      const bounds = L.latLngBounds([minLat, minLon], [maxLat, maxLon]);
      const layer = L.imageOverlay(t.thumbnail_url, bounds, {
        opacity: 0.7,
        interactive: false,
        className: 'sar-tile-overlay',
      });
      layer.addTo(map);
      tileLayers.set(t.id, { tile: t, layer, visible: true });
      allBounds.push(bounds);
    });
    if (allBounds.length > 0) {
      const combined = allBounds.reduce((acc, b) => acc.extend(b), L.latLngBounds(allBounds[0].getSouthWest(), allBounds[0].getNorthEast()));
      map.fitBounds(combined, { padding: [40, 40], maxZoom: 7 });
    }
  }

  function setTileVisible(tileId, visible) {
    const entry = tileLayers.get(tileId);
    if (!entry) return;
    if (visible && !entry.visible) {
      entry.layer.addTo(map);
      entry.visible = true;
    } else if (!visible && entry.visible) {
      map.removeLayer(entry.layer);
      entry.visible = false;
    }
    renderVessels();
    renderDetections();
    updateStats();
  }

  function setAllTilesVisible(visible) {
    tileLayers.forEach((entry, tileId) => {
      if (entry.visible !== visible) setTileVisible(tileId, visible);
      const cb = document.querySelector(`input[data-tile-id="${CSS.escape(tileId)}"]`);
      if (cb) cb.checked = visible;
      const row = cb ? cb.closest('.tile-row') : null;
      if (row) row.classList.toggle('tile-row--off', !visible);
    });
  }

  // --------------------------------------------------------------------------
  // Visible tile IDs
  // --------------------------------------------------------------------------
  function visibleTileIds() {
    const ids = new Set();
    tileLayers.forEach((entry, tileId) => {
      if (entry.visible) ids.add(tileId);
    });
    return ids;
  }

  function visibleTileTimes() {
    const times = [];
    tileLayers.forEach(entry => {
      if (entry.visible && entry.tile.datetime) {
        const t = new Date(entry.tile.datetime).getTime();
        if (!isNaN(t)) times.push({ t, tile: entry.tile });
      }
    });
    return times;
  }

  // --------------------------------------------------------------------------
  // Vessel matching + rendering
  // --------------------------------------------------------------------------
  function matchVesselToTiles(vessel, tileTimes) {
    if (!vessel || !vessel.tiers || tileTimes.length === 0) return null;
    let best = null;
    for (const tierName of ['realtime', 'tactical', 'strategic']) {
      const pts = vessel.tiers[tierName] || [];
      for (const pt of pts) {
        if (!pt.timestamp || pt.lat == null || pt.lon == null) continue;
        const pTime = new Date(pt.timestamp).getTime();
        if (isNaN(pTime)) continue;
        for (const { t, tile } of tileTimes) {
          const diff = Math.abs(pTime - t);
          if (diff <= MATCH_WINDOW_MS) {
            if (!best || diff < best.diff) {
              best = { point: pt, tile, diff };
            }
          }
        }
      }
      if (best) break;
    }
    return best;
  }

  function getAisFilterState() {
    const cats = {};
    document.querySelectorAll('[data-ais-cat]').forEach(cb => {
      cats[cb.getAttribute('data-ais-cat')] = cb.checked;
    });
    return cats;
  }

  function renderVessels() {
    if (!vesselLayer) return;
    vesselLayer.clearLayers();
    const tileTimes = visibleTileTimes();
    if (tileTimes.length === 0) return;

    const aisCats = getAisFilterState();
    vesselPositions = {};
    let matchedCount = 0;
    Object.entries(vesselsData).forEach(([mmsi, vessel]) => {
      const cat = vesselCategory(vessel);
      if (aisCats[cat] === false) return;
      const match = matchVesselToTiles(vessel, tileTimes);
      if (!match) return;
      matchedCount++;
      const { point, tile } = match;
      vesselPositions[mmsi] = [point.lat, point.lon];
      const color = vesselColor(vessel);
      const radius = vesselRadius(vessel);
      const marker = L.circleMarker([point.lat, point.lon], {
        radius,
        fillColor: color,
        color: '#000',
        weight: 1,
        fillOpacity: 0.9,
        opacity: 1,
      });
      const flag = COUNTRY_FLAG[vessel.country] || '';
      const offset = minutesDiff(point.timestamp, tile.datetime);
      const offsetStr = offset == null ? '' :
        (offset === 0 ? 'at SAR pass' : (offset > 0 ? `+${offset} min after SAR` : `${Math.abs(offset)} min before SAR`));
      marker.bindTooltip(
        `<b>${escapeHtml(vessel.name || mmsi)}</b> ${flag}` +
        `<span class="vt-meta">${escapeHtml(vessel.country || '\u2014')} \u00B7 ${escapeHtml(vessel.ship_type || '')}</span>` +
        `<span class="vt-meta">MMSI ${escapeHtml(mmsi)}</span>` +
        `<span class="vt-meta">AIS ${escapeHtml(formatTileTime(point.timestamp))}</span>` +
        `<span class="vt-meta">${escapeHtml(offsetStr)}</span>`,
        { className: 'vessel-tooltip', direction: 'top', sticky: true }
      );
      marker.addTo(vesselLayer);
    });
    window.__matchedVesselCount = matchedCount;
  }

  // --------------------------------------------------------------------------
  // CFAR detection rendering
  // --------------------------------------------------------------------------
  function getFilterState() {
    const showMatched = document.getElementById('filter-matched');
    const showDark = document.getElementById('filter-dark');
    const confSlider = document.getElementById('filter-confidence');
    return {
      showMatched: showMatched ? showMatched.checked : true,
      showDark: showDark ? showDark.checked : true,
      minConfidence: confSlider ? Number(confSlider.value) : 4,
    };
  }

  function renderDetections() {
    if (!detectionLayer || !bboxLayer || !connectionLayer) return;
    detectionLayer.clearLayers();
    bboxLayer.clearLayers();
    connectionLayer.clearLayers();

    const visible = visibleTileIds();
    const filters = getFilterState();
    let totalVisible = 0;
    let matchedVisible = 0;
    let darkVisible = 0;

    allDetections.forEach(det => {
      if (!visible.has(det.tile_id)) return;
      if (det.confidence_db < filters.minConfidence) return;
      if (det.matched_ais && !filters.showMatched) return;
      if (!det.matched_ais && !filters.showDark) return;

      totalVisible++;
      const isDark = !det.matched_ais;
      if (isDark) darkVisible++;
      else matchedVisible++;

      // Bounding box rectangle for all detections
      if (det.bbox_geo && det.bbox_geo.length === 4) {
        const [minLon, minLat, maxLon, maxLat] = det.bbox_geo;
        const bboxColor = '#6a6a6a';
        const rect = L.rectangle(
          [[minLat, minLon], [maxLat, maxLon]],
          { color: bboxColor, weight: 1.5, fill: false, dashArray: '4,4', interactive: false }
        );
        rect.addTo(bboxLayer);
      }

      if (isDark) {
        // Hollow dashed circle — analyst sees SAR imagery inside
        const radius = detectionRadius(det);
        const strokeColor = det.confidence_db >= 15 ? '#8a8a8a' : '#6a6a6a';
        const marker = L.circleMarker([det.lat, det.lon], {
          radius,
          color: strokeColor,
          weight: det.confidence_db >= 15 ? 2.5 : 1.5,
          fillOpacity: 0,
          opacity: 0.9,
          dashArray: '4,3',
        });
        marker.bindPopup(buildDetectionPopup(det), { className: 'det-popup-wrap' });
        marker.addTo(detectionLayer);
      } else {
        // Matched detection: connection line to AIS vessel (no dot)
        const mmsi = det.matched_vessel ? det.matched_vessel.mmsi : null;
        const vPos = mmsi ? vesselPositions[mmsi] : null;
        if (vPos) {
          const line = L.polyline([[det.lat, det.lon], vPos], {
            color: '#888',
            weight: 1,
            dashArray: '2,4',
            opacity: 0.6,
            interactive: false,
          });
          line.addTo(connectionLayer);
        }
      }
    });

    window.__detStats = { totalVisible, matchedVisible, darkVisible };
  }

  function buildDetectionPopup(det) {
    const conf = det.confidence_db != null ? det.confidence_db.toFixed(1) : '?';
    const sev = escapeHtml(det.severity || 'unknown');
    const length = det.estimated_length_m != null ? `~${Math.round(det.estimated_length_m)} m` : 'unknown';
    const blob = det.blob_size_pixels || '?';
    const tile = formatTileTime(det.tile_datetime);
    const zone = det.tile_zone ? escapeHtml(det.tile_zone.replace(/_/g, ' ')) : '';

    const statusHtml = `<div class="det-popup__status det-popup__status--dark">DARK VESSEL \u2014 no AIS within 2 km</div>`;

    return `<div class="det-popup">` +
      `<div class="det-popup__title">CFAR Detection</div>` +
      `<div class="det-popup__row">Confidence: <strong>${conf}\u03C3</strong> (${sev})</div>` +
      `<div class="det-popup__row">Est. length: ${length}</div>` +
      `<div class="det-popup__row">Blob: ${blob} px</div>` +
      `<div class="det-popup__row">Tile: ${escapeHtml(tile)}</div>` +
      (zone ? `<div class="det-popup__row">Zone: ${zone}</div>` : '') +
      statusHtml +
      `</div>`;
  }

  // --------------------------------------------------------------------------
  // Sidebar tile list
  // --------------------------------------------------------------------------
  function renderTileList(tiles) {
    const listEl = document.getElementById('tile-list');
    if (!listEl) return;
    if (!tiles || tiles.length === 0) {
      listEl.innerHTML = '<li class="tile-list__empty">No tiles available.</li>';
      return;
    }
    const sorted = tiles.slice().sort((a, b) => (b.datetime || '').localeCompare(a.datetime || ''));
    listEl.innerHTML = sorted.map(t => {
      const time = formatTileTime(t.datetime);
      const bbox = formatBboxShort(t.bbox);
      const zone = t.zone ? `<span class="tile-row__zone">${escapeHtml(t.zone.replace(/_/g, ' '))}</span>` : '';
      const thumb = t.thumbnail_url
        ? `<img class="tile-row__thumb" src="${escapeHtml(t.thumbnail_url)}" alt="SAR tile ${escapeHtml(t.id || '')}" loading="lazy">`
        : '<div class="tile-row__thumb"></div>';
      return `
        <li>
          <label class="tile-row">
            <input type="checkbox" data-tile-id="${escapeHtml(t.id)}" checked>
            ${thumb}
            <div class="tile-row__meta">
              <div class="tile-row__time">${escapeHtml(time)}</div>
              ${zone}
              <div class="tile-row__bbox">${escapeHtml(bbox)}</div>
            </div>
          </label>
        </li>`;
    }).join('');

    listEl.querySelectorAll('input[type="checkbox"][data-tile-id]').forEach(cb => {
      cb.addEventListener('change', (e) => {
        const id = e.target.getAttribute('data-tile-id');
        const row = e.target.closest('.tile-row');
        if (row) row.classList.toggle('tile-row--off', !e.target.checked);
        setTileVisible(id, e.target.checked);
      });
    });
  }

  // --------------------------------------------------------------------------
  // Stats + subtitle
  // --------------------------------------------------------------------------
  function updateStats() {
    const subtitle = document.getElementById('analysis-subtitle');
    const stats = document.getElementById('analysis-stats');
    let visibleTiles = 0;
    tileLayers.forEach(e => { if (e.visible) visibleTiles++; });
    const totalTiles = tileLayers.size;
    const vesselMatched = window.__matchedVesselCount || 0;
    const ds = window.__detStats || { totalVisible: 0, matchedVisible: 0, darkVisible: 0 };
    if (subtitle) {
      subtitle.textContent = `${visibleTiles}/${totalTiles} tiles \u00B7 ${allDetections.length} detections \u00B7 ${ds.darkVisible} dark`;
    }
    if (stats) {
      stats.innerHTML =
        `<span><strong>${visibleTiles}</strong> tiles</span>` +
        `<span><strong>${ds.totalVisible}</strong> detections</span>` +
        `<span><strong>${ds.matchedVisible}</strong> matched</span>` +
        `<span><strong>${ds.darkVisible}</strong> dark</span>` +
        `<span><strong>${vesselMatched}</strong> AIS</span>`;
    }
  }

  // --------------------------------------------------------------------------
  // Bootstrap
  // --------------------------------------------------------------------------
  async function load() {
    initMap();
    try {
      const [tilesRes, vesselsRes, detectionsRes] = await Promise.all([
        fetch('/api/satellite-tiles'),
        fetch('/api/vessels'),
        fetch('/api/satellite-detections'),
      ]);
      if (!tilesRes.ok) throw new Error('tiles HTTP ' + tilesRes.status);
      if (!vesselsRes.ok) throw new Error('vessels HTTP ' + vesselsRes.status);
      const tilesJson = await tilesRes.json();
      const vesselsJson = await vesselsRes.json();
      tilesData = tilesJson.tiles || [];
      vesselsData = vesselsJson.vessels || {};

      // Flatten detections from tiles[] → detections[] structure
      if (detectionsRes.ok) {
        const dJson = await detectionsRes.json();
        detectionsRaw = dJson.tiles || [];
        allDetections = [];
        detectionsRaw.forEach(tr => {
          (tr.detections || []).forEach(d => allDetections.push(d));
        });
      }

      addTileOverlays(tilesData);
      renderTileList(tilesData);
      renderVessels();
      renderDetections();
      updateStats();
    } catch (err) {
      console.error('[AnalysisView] load failed:', err);
      const subtitle = document.getElementById('analysis-subtitle');
      if (subtitle) subtitle.textContent = 'Failed to load data \u2014 see console.';
    }
  }

  // --------------------------------------------------------------------------
  // Layer toggle helpers
  // --------------------------------------------------------------------------
  function toggleLayerGroup(group, visible) {
    if (!group || !map) return;
    if (visible && !map.hasLayer(group)) group.addTo(map);
    if (!visible && map.hasLayer(group)) map.removeLayer(group);
  }

  function toggleAllTileOverlays(visible) {
    tileLayers.forEach(entry => {
      if (visible && !entry.visible) {
        entry.layer.addTo(map);
        entry.visible = true;
      } else if (!visible && entry.visible) {
        map.removeLayer(entry.layer);
        entry.visible = false;
      }
    });
  }

  // --------------------------------------------------------------------------
  // Event wiring
  // --------------------------------------------------------------------------
  function wireControls() {
    // Close
    const closeBtn = document.getElementById('analysis-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => {
        try { window.parent.postMessage({ type: 'close-analysis' }, '*'); } catch (e) {}
      });
    }
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        try { window.parent.postMessage({ type: 'close-analysis' }, '*'); } catch (err) {}
      }
    });

    // Tile all/none
    const allBtn = document.getElementById('tiles-all');
    const noneBtn = document.getElementById('tiles-none');
    if (allBtn) allBtn.addEventListener('click', () => setAllTilesVisible(true));
    if (noneBtn) noneBtn.addEventListener('click', () => setAllTilesVisible(false));

    // Layer toggles
    const layerTiles = document.getElementById('layer-tiles');
    const layerVessels = document.getElementById('layer-vessels');
    const layerDetections = document.getElementById('layer-detections');
    const layerBboxes = document.getElementById('layer-bboxes');

    if (layerTiles) layerTiles.addEventListener('change', (e) => toggleAllTileOverlays(e.target.checked));
    if (layerVessels) layerVessels.addEventListener('change', (e) => toggleLayerGroup(vesselLayer, e.target.checked));
    if (layerDetections) layerDetections.addEventListener('change', (e) => toggleLayerGroup(detectionLayer, e.target.checked));
    if (layerBboxes) layerBboxes.addEventListener('change', (e) => toggleLayerGroup(bboxLayer, e.target.checked));
    const layerConns = document.getElementById('layer-connections');
    if (layerConns) layerConns.addEventListener('change', (e) => toggleLayerGroup(connectionLayer, e.target.checked));

    // Detection filter controls
    const filterMatched = document.getElementById('filter-matched');
    const filterDark = document.getElementById('filter-dark');
    const confSlider = document.getElementById('filter-confidence');
    const confValue = document.getElementById('confidence-value');

    function onDetectionFilterChange() {
      renderDetections();
      updateStats();
    }
    if (filterMatched) filterMatched.addEventListener('change', onDetectionFilterChange);
    if (filterDark) filterDark.addEventListener('change', onDetectionFilterChange);
    if (confSlider) {
      confSlider.addEventListener('input', () => {
        if (confValue) confValue.textContent = confSlider.value + '\u03C3+';
        onDetectionFilterChange();
      });
    }

    // AIS category filter checkboxes
    function onAisFilterChange() {
      renderVessels();
      updateStats();
    }
    document.querySelectorAll('[data-ais-cat]').forEach(cb => {
      cb.addEventListener('change', onAisFilterChange);
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    wireControls();
    load();
  });
})();
