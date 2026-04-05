/* ==========================================================================
   Arctic Shadow Tracker — Dashboard JS
   Modules: Stats, MapBridge, AnomalyFeed, Resizer, AutoRefresh
   ========================================================================== */
(function () {
  'use strict';

  const REFRESH_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

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
      rendezvous: 'Rendezvous'
    };
    const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };
    const SEVERITIES = ['critical', 'high', 'medium', 'low'];
    const TYPES = ['transmission_gap', 'impossible_speed', 'loitering', 'rendezvous'];

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

    function escapeHtml(s) {
      return String(s == null ? '' : s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function updateCounts(anomalies) {
      const sev = { critical: 0, high: 0, medium: 0, low: 0 };
      const typ = { transmission_gap: 0, impossible_speed: 0, loitering: 0, rendezvous: 0 };
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
        return `
          <article class="anomaly-card ${clickable ? 'is-clickable' : ''}" data-mmsi="${escapeHtml(primary)}" ${clickable ? 'tabindex="0" role="button"' : ''}>
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
  // Resizer — drag + keyboard resize of feed area
  // --------------------------------------------------------------------------
  const Resizer = (function () {
    const handle = document.getElementById('resizer');
    const feed = document.getElementById('feed');
    if (!handle || !feed) return { init() {} };

    const MIN = 260;
    function getMax() { return Math.round(window.innerHeight * 0.75); }

    let dragging = false;
    let startY = 0;
    let startH = 0;

    function setHeight(h) {
      const clamped = Math.max(MIN, Math.min(h, getMax()));
      feed.style.minHeight = clamped + 'px';
      feed.style.maxHeight = clamped + 'px';
    }

    function onDown(e) {
      dragging = true;
      startY = e.clientY;
      startH = feed.offsetHeight;
      document.body.style.cursor = 'ns-resize';
      e.preventDefault();
    }
    function onMove(e) {
      if (!dragging) return;
      setHeight(startH + (startY - e.clientY));
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
      handle.addEventListener('mousedown', onDown);
      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
      handle.addEventListener('keydown', onKey);
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
