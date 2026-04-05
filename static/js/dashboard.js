/* ==========================================================================
   Arctic Shadow Tracker — Dashboard JS
   Modules: Stats, MapBridge, AnomalyFeed, Resizer, AutoRefresh
   ========================================================================== */
(function () {
  'use strict';

  const REFRESH_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

  // Shared HTML-escaping helper used by any module that interpolates
  // user/API-supplied strings into innerHTML.
  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // --------------------------------------------------------------------------
  // StaleBanner — show/hide + update message based on stats payload
  // --------------------------------------------------------------------------
  const StaleBanner = (function () {
    const el = document.getElementById('stale-banner');
    const detail = document.getElementById('stale-banner-detail');

    function render(stats) {
      if (!el) return;
      if (stats && stats.is_stale) {
        el.hidden = false;
        if (detail) {
          detail.textContent = stats.stale_reason ||
            ('Last update ' + (stats.last_update || 'unknown'));
        }
      } else {
        el.hidden = true;
      }
    }

    return { render };
  })();

  // --------------------------------------------------------------------------
  // MapBridge — iframe + postMessage + skeleton loader
  // --------------------------------------------------------------------------
  const MapBridge = (function () {
    const frame = document.getElementById('map-frame');
    const loading = document.getElementById('map-loading');

    function hideLoading() {
      if (loading) loading.hidden = true;
    }

    function reload() {
      if (!frame) return;
      if (loading) loading.hidden = false;
      frame.src = '/api/map?' + Date.now();
    }

    function focusVessel(mmsi, lat, lon) {
      if (!frame || !frame.contentWindow) {
        console.error('[MapBridge] iframe not ready');
        return;
      }
      frame.contentWindow.postMessage(
        { type: 'clickVessel', mmsi: mmsi, lat: lat, lon: lon },
        '*'
      );
    }

    if (frame) {
      frame.addEventListener('load', hideLoading);
    }

    return { reload, focusVessel };
  })();

  // --------------------------------------------------------------------------
  // SatelliteViewer — slide-in panel showing recent Sentinel-1 SAR tiles.
  // Fetches /api/satellite-tiles on open, renders thumbnail grid, auto-updates
  // the nav badge with the current tile count.
  // --------------------------------------------------------------------------
  const SatelliteViewer = (function () {
    const toggleBtn = document.getElementById('sat-toggle');
    const panel = document.getElementById('sat-panel');
    const backdrop = document.getElementById('sat-backdrop');
    const closeBtn = document.getElementById('sat-close');
    const body = document.getElementById('sat-panel-body');
    const subtitle = document.getElementById('sat-panel-subtitle');
    const badge = document.getElementById('sat-count-badge');
    const analysisBtn = document.getElementById('nav-open-analysis');
    const analysisOverlay = document.getElementById('analysis-overlay');
    const analysisFrame = document.getElementById('analysis-frame');
    let analysisLoaded = false;

    let lastFetchAt = 0;
    let currentTiles = [];
    const REFRESH_COOLDOWN_MS = 10 * 1000; // don't re-fetch more than once per 10s

    function isOpen() {
      return panel && !panel.hidden;
    }

    function open() {
      if (!panel) return;
      panel.hidden = false;
      if (backdrop) backdrop.hidden = false;
      if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
      // Refresh on open (cheap, cached server-side by mtime)
      if (Date.now() - lastFetchAt > REFRESH_COOLDOWN_MS) {
        fetchAndRender();
      }
    }

    function close() {
      if (!panel) return;
      panel.hidden = true;
      if (backdrop) backdrop.hidden = true;
      if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
    }

    function toggle() {
      if (isOpen()) close();
      else open();
    }

    function isAnalysisOpen() {
      return analysisOverlay && !analysisOverlay.hidden;
    }

    function openAnalysis() {
      if (!analysisOverlay || !analysisFrame) return;
      if (!analysisLoaded) {
        analysisFrame.src = '/analysis-view';
        analysisLoaded = true;
      }
      analysisOverlay.hidden = false;
      document.body.style.overflow = 'hidden';
    }

    function closeAnalysis() {
      if (!analysisOverlay) return;
      analysisOverlay.hidden = true;
      document.body.style.overflow = '';
    }

    function formatTileTime(isoTs) {
      if (!isoTs) return 'Unknown time';
      try {
        const d = new Date(isoTs);
        if (isNaN(d.getTime())) return isoTs;
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        const mon = months[d.getUTCMonth()];
        const day = String(d.getUTCDate()).padStart(2, '0');
        const hh = String(d.getUTCHours()).padStart(2, '0');
        const mm = String(d.getUTCMinutes()).padStart(2, '0');
        return `${mon} ${day}, ${hh}:${mm} UTC`;
      } catch (e) {
        return isoTs;
      }
    }

    function formatBbox(bbox) {
      if (!bbox || bbox.length !== 4) return '';
      const [minLon, minLat, maxLon, maxLat] = bbox;
      return `lon ${minLon.toFixed(1)}°–${maxLon.toFixed(1)}° · lat ${minLat.toFixed(1)}°–${maxLat.toFixed(1)}°`;
    }

    function renderTiles(tiles) {
      if (!body) return;
      if (!tiles || tiles.length === 0) {
        body.innerHTML = '<div class="sat-panel__empty">No satellite tiles collected yet. The daily workflow will populate this on its next run.</div>';
        return;
      }
      const cards = tiles.map(t => {
        const thumb = t.thumbnail_url
          ? `<img class="sat-tile__img" src="${escapeHtml(t.thumbnail_url)}" alt="Sentinel-1 SAR tile ${escapeHtml(t.id || '')}" loading="lazy">`
          : `<div class="sat-tile__img sat-tile__img--missing">No thumbnail</div>`;
        const time = formatTileTime(t.datetime);
        const bbox = formatBbox(t.bbox);
        const mode = t.instrument_mode || 'IW';
        return `
          <article class="sat-tile">
            ${thumb}
            <div class="sat-tile__meta">
              <div class="sat-tile__time">${escapeHtml(time)}</div>
              <div class="sat-tile__bbox">${escapeHtml(bbox)}</div>
              <div class="sat-tile__mode">Sentinel-1 ${escapeHtml(mode)}</div>
            </div>
          </article>`;
      }).join('');
      body.innerHTML = `<div class="sat-tile-grid">${cards}</div>`;
    }

    function updateBadge(count) {
      if (!badge) return;
      if (count > 0) {
        badge.textContent = String(count);
        badge.hidden = false;
      } else {
        badge.hidden = true;
      }
    }

    async function fetchAndRender() {
      lastFetchAt = Date.now();
      if (body && currentTiles.length === 0) {
        body.innerHTML = '<div class="sat-panel__empty">Loading satellite tiles…</div>';
      }
      try {
        const res = await fetch('/api/satellite-tiles');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        currentTiles = data.tiles || [];
        updateBadge(currentTiles.length);
        if (subtitle) {
          if (currentTiles.length > 0) {
            subtitle.textContent = `${currentTiles.length} tile${currentTiles.length !== 1 ? 's' : ''} · last ${data.history_window_days || 14} days`;
          } else {
            subtitle.textContent = 'No tiles available yet';
          }
        }
        renderTiles(currentTiles);
      } catch (err) {
        console.error('[SatelliteViewer] fetch failed:', err);
        if (body) {
          body.innerHTML = '<div class="sat-panel__empty">Failed to load satellite tiles. Check console for details.</div>';
        }
      }
    }

    function init() {
      if (toggleBtn) toggleBtn.addEventListener('click', toggle);
      if (closeBtn) closeBtn.addEventListener('click', close);
      if (backdrop) backdrop.addEventListener('click', close);
      if (analysisBtn) analysisBtn.addEventListener('click', openAnalysis);
      document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        if (isAnalysisOpen()) { closeAnalysis(); return; }
        if (isOpen()) close();
      });
      // Listen for close messages posted from the analysis iframe.
      window.addEventListener('message', (e) => {
        if (e && e.data && e.data.type === 'close-analysis') closeAnalysis();
      });
      // Prefetch once on boot so the nav badge shows a count without needing
      // the user to open the panel first.
      fetchAndRender();
    }

    return { init, open, close, fetchAndRender, openAnalysis, closeAnalysis };
  })();

  // --------------------------------------------------------------------------
  // Stats — fetch vessel stats and update KPI cards
  // --------------------------------------------------------------------------
  const Stats = (function () {
    let activeController = null;

    const FIELDS = [
      'total', 'russian', 'shadow_fleet', 'suspected_shadow',
      'chinese', 'norwegian', 'norwegian_military', 'other', 'buoy'
    ];

    function update(stats) {
      FIELDS.forEach(f => {
        const el = document.getElementById('stat-' + f);
        if (el && stats[f] !== undefined) el.textContent = stats[f];
      });
      const updateEl = document.getElementById('last-update');
      if (updateEl && stats.last_update) {
        updateEl.textContent = 'Updated ' + stats.last_update;
        updateEl.classList.toggle('nav__status--stale', !!stats.is_stale);
      }
      StaleBanner.render(stats);
    }

    async function fetchAndRender() {
      if (activeController) activeController.abort();
      activeController = new AbortController();
      try {
        const res = await fetch('/api/vessels', { signal: activeController.signal });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        if (data.stats) update(data.stats);
        return data;
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('[Stats] fetch failed:', err);
        }
        throw err;
      }
    }

    return { update, fetchAndRender };
  })();

  // --------------------------------------------------------------------------
  // AnomalyFeed — fetch, filter, sort, render
  // --------------------------------------------------------------------------
  const AnomalyFeed = (function () {
    const listEl = document.getElementById('anomaly-list');
    const countEl = document.getElementById('anomaly-count');

    const TYPE_LABELS = {
      transmission_gap: 'AIS Gap',
      impossible_speed: 'Impossible Speed',
      loitering: 'Loitering',
      rendezvous: 'Rendezvous',
      left_coverage: 'Left Coverage',
      dark_vessel: 'Dark Vessel',
    };
    const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };
    const SEVERITIES = ['critical', 'high', 'medium', 'low'];
    const TYPES = ['transmission_gap', 'impossible_speed', 'loitering', 'rendezvous', 'left_coverage', 'dark_vessel'];

    let all = [];
    let currentSort = 'newest';
    let activeController = null;

    function formatType(type) {
      return TYPE_LABELS[type] || (type || '').replace(/_/g, ' ');
    }

    function formatCoords(lat, lon) {
      if (lat === undefined || lon === undefined) return 'unknown location';
      const latDir = lat >= 0 ? 'N' : 'S';
      const lonDir = lon >= 0 ? 'E' : 'W';
      return `${Math.abs(lat).toFixed(2)}°${latDir}, ${Math.abs(lon).toFixed(2)}°${lonDir}`;
    }

    function describe(a) {
      const d = a.details || {};
      switch (a.anomaly_type) {
        case 'dark_vessel': {
          const det = d.detection || {};
          const conf = det.confidence_db != null ? `${det.confidence_db.toFixed(1)}σ` : 'unknown σ';
          const len = det.estimated_length_m != null ? `~${det.estimated_length_m}m` : 'unknown size';
          return `SAR detection with no AIS match — confidence ${conf}, ${len}`;
        }
        case 'left_coverage':
          return `Vessel left BarentsWatch coverage area after ${Math.round(d.gap_duration_minutes || 0)} minutes of silence (expected)`;
        case 'transmission_gap':
          return `AIS signal lost for ${Math.round(d.gap_duration_minutes || 0)} minutes` +
                 (d.near_border ? ' near Norwegian border' : '');
        case 'impossible_speed':
          return `Traveled at ${Math.round(d.calculated_speed_knots || 0)} knots ` +
                 `(max ${d.max_allowed_knots || 0} for ${d.vessel_type || 'vessel type'})`;
        case 'loitering':
          return `Stayed within ${d.radius_km || 0}km for ${Math.round(d.duration_hours || 0)} hours at ` +
                 (d.center_position ? formatCoords(d.center_position.lat, d.center_position.lon) : 'unknown location');
        case 'rendezvous':
          return `Met with ${d.vessel2 ? d.vessel2.name : 'unknown vessel'} within ${d.distance_km || 0}km`;
        default:
          return 'Suspicious activity detected';
      }
    }

    function updateCounts(anomalies) {
      const sev = { critical: 0, high: 0, medium: 0, low: 0 };
      const typ = {
        transmission_gap: 0,
        impossible_speed: 0,
        loitering: 0,
        rendezvous: 0,
        left_coverage: 0,
        dark_vessel: 0,
      };
      anomalies.forEach(a => {
        if (sev[a.severity] !== undefined) sev[a.severity]++;
        if (typ[a.anomaly_type] !== undefined) typ[a.anomaly_type]++;
      });
      Object.keys(sev).forEach(k => {
        const el = document.getElementById('count-' + k);
        if (el) el.textContent = sev[k];
      });
      Object.keys(typ).forEach(k => {
        const el = document.getElementById('count-' + k);
        if (el) el.textContent = typ[k];
      });
    }

    function getSelected(keys) {
      return keys.filter(k => {
        const el = document.getElementById('filter-' + k);
        return el && el.checked;
      });
    }

    function sort(list, mode) {
      const sorted = [...list];
      if (mode === 'newest') {
        sorted.sort((a, b) => (b.detected_at || '').localeCompare(a.detected_at || ''));
      } else if (mode === 'oldest') {
        sorted.sort((a, b) => (a.detected_at || '').localeCompare(b.detected_at || ''));
      } else if (mode === 'severity') {
        sorted.sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
      }
      return sorted;
    }

    // Format a signed time delta in minutes as a human "+45m" / "-2.3h" string.
    function formatRelativeDelta(minutes) {
      if (minutes == null || isNaN(minutes)) return '';
      const abs = Math.abs(minutes);
      const sign = minutes >= 0 ? '+' : '-';
      if (abs < 60) return `${sign}${Math.round(abs)}m`;
      const h = Math.round((abs / 60) * 10) / 10;  // one decimal
      return `${sign}${h}h`;
    }

    // Render a Sentinel-1 coverage chip if any nearby SAR passes exist.
    // Shows the nearest pass; tooltip lists all passes in the window.
    function renderSarChip(sarCoverage) {
      if (!sarCoverage || sarCoverage.length === 0) return '';
      const nearest = sarCoverage[0];
      const rel = formatRelativeDelta(nearest.delta_minutes);
      const tooltipLines = sarCoverage.map(p =>
        `${p.datetime} (${formatRelativeDelta(p.delta_minutes)})`
      );
      const title = 'Sentinel-1 passes nearby:\n' + tooltipLines.join('\n');
      return `<div class="sar-chip" title="${escapeHtml(title)}">SAR pass ${escapeHtml(rel)}</div>`;
    }

    // Pull the best-available (lat, lon) out of an anomaly's details blob.
    // Different anomaly types store position in different keys; rendezvous has none.
    function extractPosition(a) {
      const d = (a && a.details) || {};
      if (d.last_position && d.last_position.lat != null) {
        return { lat: d.last_position.lat, lon: d.last_position.lon };
      }
      if (d.center_position && d.center_position.lat != null) {
        return { lat: d.center_position.lat, lon: d.center_position.lon };
      }
      if (Array.isArray(d.positions) && d.positions.length) {
        const p = d.positions[d.positions.length - 1];
        if (p && p.lat != null) return { lat: p.lat, lon: p.lon };
      }
      return { lat: null, lon: null };
    }

    function render(list) {
      if (!listEl) return;
      if (!list || list.length === 0) {
        listEl.innerHTML = '<div class="anomaly-feed__empty">No anomalies match your filters</div>';
        if (countEl) countEl.textContent = '0 detections';
        return;
      }
      if (countEl) countEl.textContent = `${list.length} detection${list.length !== 1 ? 's' : ''}`;

      // Index anomalies by primary MMSI so click handlers can look up position
      const byMmsi = Object.create(null);

      const html = list.map(a => {
        const mmsiList = (a.mmsi || '').toString().split(',');
        const primary = mmsiList[0].trim();
        byMmsi[primary] = a;
        const clickable = mmsiList.length === 1;
        const vessel = escapeHtml(a.vessel_name || 'Unknown');
        const country = escapeHtml(a.country || 'Unknown');
        const time = escapeHtml(a.formatted_time || 'Unknown');
        const sev = escapeHtml(a.severity || 'low');
        const type = escapeHtml(formatType(a.anomaly_type));
        const desc = escapeHtml(describe(a));
        const sarChip = renderSarChip(a.sar_coverage);
        return `
          <article class="anomaly-card ${clickable ? 'is-clickable' : ''}" data-mmsi="${escapeHtml(primary)}" data-type="${escapeHtml(a.anomaly_type || '')}" ${clickable ? 'tabindex="0" role="button"' : ''}>
            <div class="anomaly-card__head">
              <div class="anomaly-card__meta">
                <span class="badge badge--${sev}">${sev}</span>
                <span class="anomaly-card__type">${type}</span>
              </div>
              <span class="anomaly-card__time">${time}</span>
            </div>
            <div class="anomaly-card__body">
              <span class="anomaly-card__vessel">${vessel}</span>
              <span class="anomaly-card__country">(${country})</span>
              <div>${desc}</div>
              ${sarChip}
            </div>
          </article>`;
      }).join('');

      listEl.innerHTML = html;

      function focusFromCard(el) {
        const mmsi = el.dataset.mmsi.trim();
        const pos = extractPosition(byMmsi[mmsi]);
        // 1. Scroll the map into view if it isn't already. `block: 'nearest'`
        //    is a no-op when the element is already visible, so this is safe
        //    on the desktop sidebar layout and useful on mobile where the map
        //    may have scrolled off-screen above the anomaly drawer.
        const mapEl = document.querySelector('.map-wrapper');
        if (mapEl) {
          mapEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
        // 2. Pan/zoom map + highlight marker (via iframe postMessage bridge)
        MapBridge.focusVessel(mmsi, pos.lat, pos.lon);
      }

      listEl.querySelectorAll('.anomaly-card.is-clickable').forEach(el => {
        el.addEventListener('click', () => focusFromCard(el));
        el.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            focusFromCard(el);
          }
        });
      });
    }

    function applyFilters() {
      const sev = getSelected(SEVERITIES);
      const typ = getSelected(TYPES);
      const filtered = all.filter(a => sev.includes(a.severity) && typ.includes(a.anomaly_type));
      render(sort(filtered, currentSort));
    }

    function setSort(mode) {
      currentSort = mode;
      document.querySelectorAll('.sort-row').forEach(el => {
        el.classList.toggle('is-active', el.dataset.sort === mode);
      });
      applyFilters();
    }

    async function fetchAndRender() {
      if (activeController) activeController.abort();
      activeController = new AbortController();
      try {
        const res = await fetch('/api/anomalies', { signal: activeController.signal });
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const data = await res.json();
        all = data.anomalies || [];
        updateCounts(all);
        applyFilters();
      } catch (err) {
        if (err.name === 'AbortError') return;
        console.error('[AnomalyFeed] fetch failed:', err);
        if (listEl) {
          listEl.innerHTML = '<div class="anomaly-feed__empty">Failed to load anomaly detections</div>';
        }
        if (countEl) countEl.textContent = 'Error';
      }
    }

    function init() {
      SEVERITIES.forEach(k => {
        const el = document.getElementById('filter-' + k);
        if (el) el.addEventListener('change', applyFilters);
      });
      TYPES.forEach(k => {
        const el = document.getElementById('filter-' + k);
        if (el) el.addEventListener('change', applyFilters);
      });
      document.querySelectorAll('.sort-row').forEach(el => {
        el.addEventListener('click', () => setSort(el.dataset.sort));
        el.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setSort(el.dataset.sort);
          }
        });
      });
    }

    return { init, fetchAndRender };
  })();

  // --------------------------------------------------------------------------
  // FilterSheet — on mobile, the filter panel is a slide-up bottom sheet
  // triggered by a "Filters" button. No-op on desktop.
  // --------------------------------------------------------------------------
  const FilterSheet = (function () {
    const toggleBtn = document.getElementById('filter-toggle');
    const panel = document.getElementById('filter-panel');
    const backdrop = document.getElementById('filter-backdrop');

    function isOpen() {
      return panel && panel.classList.contains('filter-panel--open');
    }

    function open() {
      if (!panel) return;
      panel.classList.add('filter-panel--open');
      if (backdrop) backdrop.hidden = false;
      if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
    }

    function close() {
      if (!panel) return;
      panel.classList.remove('filter-panel--open');
      if (backdrop) backdrop.hidden = true;
      if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
    }

    function toggle() {
      if (isOpen()) close();
      else open();
    }

    function init() {
      if (toggleBtn) toggleBtn.addEventListener('click', toggle);
      if (backdrop) backdrop.addEventListener('click', close);
      // Esc closes the sheet
      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && isOpen()) close();
      });
      // Also close if user resizes to desktop width
      window.addEventListener('resize', () => {
        if (window.innerWidth >= 768 && isOpen()) close();
      });
    }

    return { init, open, close };
  })();

  // --------------------------------------------------------------------------
  // Resizer — drag + keyboard resize of feed area
  // --------------------------------------------------------------------------
  const Resizer = (function () {
    const handle = document.getElementById('resizer');
    const feed = document.getElementById('feed');
    if (!handle || !feed) return { init() {} };

    function getMin() { return window.innerWidth < 768 ? 180 : 260; }
    function getMax() { return Math.round(window.innerHeight * 0.75); }

    let dragging = false;
    let startY = 0;
    let startH = 0;

    function setHeight(h) {
      const clamped = Math.max(getMin(), Math.min(h, getMax()));
      feed.style.minHeight = clamped + 'px';
      feed.style.maxHeight = clamped + 'px';
    }

    // Normalize mouse and touch events to a single clientY value
    function coordY(e) {
      if (e.touches && e.touches.length) return e.touches[0].clientY;
      if (e.changedTouches && e.changedTouches.length) return e.changedTouches[0].clientY;
      return e.clientY;
    }

    function onDown(e) {
      dragging = true;
      startY = coordY(e);
      startH = feed.offsetHeight;
      document.body.style.cursor = 'ns-resize';
      e.preventDefault();
    }
    function onMove(e) {
      if (!dragging) return;
      // touchmove must be passive:false to call preventDefault, which we need
      // to stop the page from scrolling while dragging the handle
      if (e.cancelable) e.preventDefault();
      setHeight(startH + (startY - coordY(e)));
    }
    function onUp() {
      if (dragging) {
        dragging = false;
        document.body.style.cursor = '';
      }
    }
    function onKey(e) {
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        e.preventDefault();
        const delta = e.key === 'ArrowUp' ? 24 : -24;
        setHeight(feed.offsetHeight + delta);
      }
    }

    function init() {
      // Mouse
      handle.addEventListener('mousedown', onDown);
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
      // Touch — passive:false so we can preventDefault during drag
      handle.addEventListener('touchstart', onDown, { passive: false });
      document.addEventListener('touchmove', onMove, { passive: false });
      document.addEventListener('touchend', onUp);
      document.addEventListener('touchcancel', onUp);
      // Keyboard
      handle.addEventListener('keydown', onKey);
      // Re-clamp on viewport rotate/resize
      window.addEventListener('resize', () => {
        if (feed.style.minHeight) setHeight(feed.offsetHeight);
      });
    }

    return { init };
  })();

  // --------------------------------------------------------------------------
  // AutoRefresh — interval + visibility-aware
  // --------------------------------------------------------------------------
  const AutoRefresh = (function () {
    let timer = null;

    async function tick() {
      if (document.visibilityState === 'hidden') return;
      try {
        await Stats.fetchAndRender();
        await AnomalyFeed.fetchAndRender();
        MapBridge.reload();
      } catch (_) { /* handled in modules */ }
    }

    function start() {
      stop();
      timer = setInterval(tick, REFRESH_INTERVAL_MS);
    }
    function stop() {
      if (timer) { clearInterval(timer); timer = null; }
    }

    return { start, stop, tick };
  })();

  // --------------------------------------------------------------------------
  // Refresh button
  // --------------------------------------------------------------------------
  function wireRefreshButton() {
    const btn = document.getElementById('refresh-btn');
    if (!btn) return;
    const label = btn.querySelector('.refresh-btn__label') || btn;
    const original = label.textContent;

    btn.addEventListener('click', async () => {
      btn.disabled = true;
      label.textContent = 'Refreshing…';
      try {
        await Stats.fetchAndRender();
        await AnomalyFeed.fetchAndRender();
        MapBridge.reload();
        label.textContent = 'Updated';
        setTimeout(() => { label.textContent = original; btn.disabled = false; }, 1500);
      } catch (_) {
        label.textContent = 'Error';
        setTimeout(() => { label.textContent = original; btn.disabled = false; }, 2500);
      }
    });
  }

  // --------------------------------------------------------------------------
  // Boot
  // --------------------------------------------------------------------------
  function boot() {
    AnomalyFeed.init();
    Resizer.init();
    FilterSheet.init();
    SatelliteViewer.init();
    wireRefreshButton();
    AnomalyFeed.fetchAndRender();
    AutoRefresh.start();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  // Expose for debugging
  window.ASR = { Stats, AnomalyFeed, MapBridge, AutoRefresh };
})();
