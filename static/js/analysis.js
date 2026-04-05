/* ==========================================================================
   SAR Analysis View — standalone Leaflet page logic.
   Loaded by templates/analysis.html (served at /analysis-view).

   Fetches SAR tiles + AIS vessels, draws tiles as ImageOverlays at their
   bboxes, overlays AIS markers filtered to ±60 min of any visible tile.
   ========================================================================== */
(function () {
  'use strict';

  const MATCH_WINDOW_MS = 60 * 60 * 1000; // ±60 min around each SAR acquisition
  const ARCTIC_CENTER = [74.0, 20.0];
  const ARCTIC_ZOOM = 4;

  // --------------------------------------------------------------------------
  // Vessel color mapping — port of src/map_generator.py:21-71 (_vessel_color).
  // Keep in sync if the Python logic changes.
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

  const COUNTRY_FLAG = {
    Russia: '🇷🇺', China: '🇨🇳', Norway: '🇳🇴',
  };

  // --------------------------------------------------------------------------
  // Formatting helpers
  // --------------------------------------------------------------------------
  function formatTileTime(iso) {
    if (!iso) return 'Unknown';
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const mon = months[d.getUTCMonth()];
    const day = String(d.getUTCDate()).padStart(2, '0');
    const hh = String(d.getUTCHours()).padStart(2, '0');
    const mm = String(d.getUTCMinutes()).padStart(2, '0');
    return `${mon} ${day}, ${hh}:${mm} UTC`;
  }

  function formatBboxShort(bbox) {
    if (!bbox || bbox.length !== 4) return '';
    const [minLon, minLat, maxLon, maxLat] = bbox;
    return `${minLon.toFixed(1)}°E–${maxLon.toFixed(1)}°E · ${minLat.toFixed(1)}°N–${maxLat.toFixed(1)}°N`;
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
  let vesselLayer;               // L.LayerGroup of current vessel markers
  let vesselsData = {};          // mmsi -> vessel
  let tilesData = [];            // array of tile objects

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
  // Vessel matching + rendering
  // --------------------------------------------------------------------------
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

  /**
   * For a given vessel, return the best-matching position sample within
   * ±MATCH_WINDOW_MS of any visible SAR tile. Returns null if no match.
   * Walks realtime → tactical → strategic tiers.
   */
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
      if (best) break; // prefer higher-fidelity tiers
    }
    return best;
  }

  function renderVessels() {
    if (!vesselLayer) return;
    vesselLayer.clearLayers();
    const tileTimes = visibleTileTimes();
    if (tileTimes.length === 0) return;

    let matchedCount = 0;
    Object.entries(vesselsData).forEach(([mmsi, vessel]) => {
      const match = matchVesselToTiles(vessel, tileTimes);
      if (!match) return;
      matchedCount++;
      const { point, tile } = match;
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
        `<span class="vt-meta">${escapeHtml(vessel.country || '—')} · ${escapeHtml(vessel.ship_type || '')}</span>` +
        `<span class="vt-meta">MMSI ${escapeHtml(mmsi)}</span>` +
        `<span class="vt-meta">AIS ${escapeHtml(formatTileTime(point.timestamp))}</span>` +
        `<span class="vt-meta">${escapeHtml(offsetStr)}</span>`,
        { className: 'vessel-tooltip', direction: 'top', sticky: true }
      );
      marker.addTo(vesselLayer);
    });
    window.__matchedCount = matchedCount; // consumed by updateStats
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
    const matched = window.__matchedCount || 0;
    if (subtitle) {
      subtitle.textContent = `${visibleTiles}/${totalTiles} tiles visible · ${matched} AIS vessel${matched !== 1 ? 's' : ''} matched (±60 min)`;
    }
    if (stats) {
      stats.innerHTML =
        `<span><strong>${visibleTiles}</strong>SAR tiles</span>` +
        `<span><strong>${matched}</strong>matched vessels</span>` +
        `<span><strong>${Object.keys(vesselsData).length}</strong>total tracked</span>`;
    }
  }

  // --------------------------------------------------------------------------
  // Bootstrap
  // --------------------------------------------------------------------------
  async function load() {
    initMap();
    try {
      const [tilesRes, vesselsRes] = await Promise.all([
        fetch('/api/satellite-tiles'),
        fetch('/api/vessels'),
      ]);
      if (!tilesRes.ok) throw new Error('tiles HTTP ' + tilesRes.status);
      if (!vesselsRes.ok) throw new Error('vessels HTTP ' + vesselsRes.status);
      const tilesJson = await tilesRes.json();
      const vesselsJson = await vesselsRes.json();
      tilesData = tilesJson.tiles || [];
      vesselsData = vesselsJson.vessels || {};

      addTileOverlays(tilesData);
      renderTileList(tilesData);
      renderVessels();
      updateStats();
    } catch (err) {
      console.error('[AnalysisView] load failed:', err);
      const subtitle = document.getElementById('analysis-subtitle');
      if (subtitle) subtitle.textContent = 'Failed to load data — see console.';
    }
  }

  // --------------------------------------------------------------------------
  // Event wiring
  // --------------------------------------------------------------------------
  function wireControls() {
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
    const allBtn = document.getElementById('tiles-all');
    const noneBtn = document.getElementById('tiles-none');
    if (allBtn) allBtn.addEventListener('click', () => setAllTilesVisible(true));
    if (noneBtn) noneBtn.addEventListener('click', () => setAllTilesVisible(false));
  }

  document.addEventListener('DOMContentLoaded', () => {
    wireControls();
    load();
  });
})();
