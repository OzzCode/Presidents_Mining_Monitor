// Overview charts — farm-wide
const OV_REFRESH = 15; // seconds

let ovCharts = {};
// AbortControllers to cancel in-flight requests when new ones start
let ovAbortControllers = {summary: null, aggregate: null, miners: null};
// Debounce handle for user-triggered refresh
let ovRefreshTimeout = null;

function getFreshWithin() {
    const sel = document.getElementById('fresh-within');
    if (!sel) return 30;
    const val = parseInt(sel.value, 10);
    return Number.isFinite(val) ? val : 30;
}

function getActiveOnly() {
    const cb = document.getElementById('active-only');
    return cb ? !!cb.checked : true;
}

function saveFreshPrefs() {
    try {
        localStorage.setItem('ov_fresh_within', String(getFreshWithin()));
        localStorage.setItem('ov_active_only', getActiveOnly() ? '1' : '0');
    } catch (e) {
        // Log error but don't break the app
        console.warn('Failed to save preferences to localStorage:', e);
    }
}

function loadFreshPrefs() {
    try {
        const fw = localStorage.getItem('ov_fresh_within');
        const ao = localStorage.getItem('ov_active_only');
        if (fw && document.getElementById('fresh-within')) {
            document.getElementById('fresh-within').value = fw;
        }
        if (ao && document.getElementById('active-only')) {
            document.getElementById('active-only').checked = ao === '1';
        }
    } catch (e) {
        console.warn('Failed to load preferences from localStorage:', e);
    }
}

function updateActiveWindowBadge() {
    const el = document.getElementById('active-window-badge');
    if (!el) return;
    const mins = Math.max(getFreshWithin(), 30); // reflect the effective window used for API
    el.textContent = `Active window: last ${mins} min`;
}

function ensureOvCharts() {
    // Check if charts already exist before creating new ones
    if (!ovCharts.hash) {
        const hashCtx = document.getElementById('overview-hash');
        if (hashCtx) {
            ovCharts.hash = new Chart(hashCtx, {
                type: 'line',
                data: {labels: [], datasets: [{label: 'TH/s', data: [], tension: 0.2, fill: false}]},
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {x: {type: 'time', time: {unit: 'hour'}}, y: {beginAtZero: true}},
                    plugins: {legend: {display: false}}
                }
            });
        }
    }
    if (!ovCharts.power) {
        const powerCtx = document.getElementById('overview-power');
        if (powerCtx) {
            ovCharts.power = new Chart(powerCtx, {
                type: 'line',
                data: {labels: [], datasets: [{label: 'W', data: [], tension: 0.2, fill: false}]},
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {x: {type: 'time', time: {unit: 'hour'}}, y: {beginAtZero: true}},
                    plugins: {legend: {display: false}}
                }
            });
        }
    }
    if (!ovCharts.tempfan) {
        const tempfanCtx = document.getElementById('overview-tempfan');
        if (tempfanCtx) {
            ovCharts.tempfan = new Chart(tempfanCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {label: 'Temp (°C)', data: [], yAxisID: 'y', tension: 0.2, fill: false},
                        {label: 'Fan RPM', data: [], yAxisID: 'y1', tension: 0.2, fill: false}
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        x: {type: 'time', time: {unit: 'hour'}},
                        y: {beginAtZero: true, position: 'left', title: {display: true, text: '°C'}},
                        y1: {
                            beginAtZero: true,
                            position: 'right',
                            grid: {drawOnChartArea: false},
                            title: {display: true, text: 'RPM'}
                        }
                    },
                    plugins: {legend: {display: false}}
                }
            });
        }
    }
}

function fmt(n, d = 3) {
    const v = Number(n);
    return Number.isFinite(v) ? v.toFixed(d) : '0';
}

function fmt0(n) {
    const v = Number(n);
    return Number.isFinite(v) ? Math.round(v).toString() : '0';
}

async function loadSummaryKPIs() {
    try {
        const windowMin = Math.max(getFreshWithin(), 30);
        const freshWithin = getFreshWithin();
        const activeOnly = getActiveOnly();

        // Abort previous in-flight request
        if (ovAbortControllers.summary) ovAbortControllers.summary.abort();
        ovAbortControllers.summary = new AbortController();
        const {signal} = ovAbortControllers.summary;

        const params = new URLSearchParams({
            window_min: String(windowMin),
            active_only: activeOnly ? 'true' : 'false',
            fresh_within: String(freshWithin),
        });

        const response = await fetch(`/api/summary?${params.toString()}`, {signal});
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        // Update KPI values with proper validation (align with /api/summary keys)
        const elHash = document.getElementById('kpi-hash');
        if (elHash) elHash.textContent = fmt(data.total_hashrate);
        const elPower = document.getElementById('kpi-power');
        if (elPower) elPower.textContent = fmt0(data.total_power);
        const elTemp = document.getElementById('kpi-temp');
        if (elTemp) elTemp.textContent = fmt(data.avg_temp, 1);
        const elWorkers = document.getElementById('kpi-workers');
        if (elWorkers) elWorkers.textContent = fmt0(data.total_workers);

    } catch (error) {
        if (error && error.name === 'AbortError') return; // ignore aborted requests
        console.warn('Failed to load summary KPIs:', error);
        // Set default values or show an error message
        const elHash = document.getElementById('kpi-hash');
        if (elHash) elHash.textContent = '0';
        const elPower = document.getElementById('kpi-power');
        if (elPower) elPower.textContent = '0';
        const elTemp = document.getElementById('kpi-temp');
        if (elTemp) elTemp.textContent = '0';
        const elWorkers = document.getElementById('kpi-workers');
        if (elWorkers) elWorkers.textContent = '0';
    } finally {
        ovAbortControllers.summary = null;
    }
}

async function loadAggregateSeries() {
    try {
        const windowMin = Math.max(getFreshWithin(), 30);

        // Validate that we have chart elements before proceeding
        if (!ovCharts.hash || !ovCharts.power || !ovCharts.tempfan) {
            ensureOvCharts(); // Re-initialize charts if needed
        }

        // Build series from /api/metrics (client-side aggregation)
        const sinceIso = new Date(Date.now() - windowMin * 60 * 1000).toISOString();
        const q = new URLSearchParams({ since: sinceIso, limit: '3000' });
        if (!getActiveOnly()) {
            q.set('active_only', 'false');
        } else {
            q.set('active_only', 'true');
            q.set('fresh_within', String(getFreshWithin()));
        }
        const resp = await fetch(`/api/metrics?${q.toString()}`);
        if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`);
        const rows = await resp.json();
        const list = Array.isArray(rows) ? rows : [];

        // Aggregate into 5-minute bins: sum hash/power, avg temp/fan
        const BIN_MIN = 5;
        const bins = new Map();
        const binKey = (ts) => {
            const d = new Date(ts);
            if (Number.isNaN(d.getTime())) return null;
            const ms = BIN_MIN * 60 * 1000;
            return new Date(Math.floor(d.getTime() / ms) * ms).toISOString();
        };
        for (const r of list) {
            const key = binKey(r.timestamp);
            if (!key) continue;
            const cur = bins.get(key) || { hash: 0, power: 0, temp: 0, fan: 0, tc: 0, fc: 0 };
            cur.hash += Number(r.hashrate_ths || 0);
            cur.power += Number(r.power_w || 0);
            const t = Number(r.avg_temp_c || 0);
            if (Number.isFinite(t) && t > 0) { cur.temp += t; cur.tc++; }
            const f = Number(r.avg_fan_rpm || 0);
            if (Number.isFinite(f) && f > 0) { cur.fan += f; cur.fc++; }
            bins.set(key, cur);
        }
        const timestamps = Array.from(bins.keys()).sort();
        const hash = timestamps.map(k => bins.get(k).hash);
        const power = timestamps.map(k => bins.get(k).power);
        const temp = timestamps.map(k => { const b = bins.get(k); return b.tc ? b.temp / b.tc : 0; });
        const fan = timestamps.map(k => { const b = bins.get(k); return b.fc ? b.fan / b.fc : 0; });

        // Update charts
        if (ovCharts.hash) {
            ovCharts.hash.data.labels = timestamps;
            ovCharts.hash.data.datasets[0].data = hash;
            ovCharts.hash.update();
        }
        if (ovCharts.power) {
            ovCharts.power.data.labels = timestamps;
            ovCharts.power.data.datasets[0].data = power;
            ovCharts.power.update();
        }
        if (ovCharts.tempfan) {
            ovCharts.tempfan.data.labels = timestamps;
            if (ovCharts.tempfan.data.datasets.length >= 2) {
                ovCharts.tempfan.data.datasets[0].data = temp;
                ovCharts.tempfan.data.datasets[1].data = fan;
            }
            ovCharts.tempfan.update();
        }
    } catch (error) {
        console.warn('Failed to load aggregate series:', error);
        // Clear charts if there's an error
        if (ovCharts.hash) {
            ovCharts.hash.data.labels = [];
            ovCharts.hash.data.datasets[0].data = [];
            ovCharts.hash.update();
        }
        if (ovCharts.power) {
            ovCharts.power.data.labels = [];
            ovCharts.power.data.datasets[0].data = [];
            ovCharts.power.update();
        }
        if (ovCharts.tempfan) {
            ovCharts.tempfan.data.labels = [];
            if (ovCharts.tempfan.data.datasets.length >= 2) {
                ovCharts.tempfan.data.datasets[0].data = [];
                ovCharts.tempfan.data.datasets[1].data = [];
            }
            ovCharts.tempfan.update();
        }
    }
}

async function fillMinersSummaryTable() {
    try {
        const tbody = document.getElementById('stats-log');
        if (!tbody) return;

        const windowMin = Math.max(getFreshWithin(), 30);
        const freshWithin = getFreshWithin();
        const activeOnly = getActiveOnly();

        // Abort previous in-flight request
        if (ovAbortControllers.miners) ovAbortControllers.miners.abort();
        ovAbortControllers.miners = new AbortController();
        const {signal} = ovAbortControllers.miners;

        const params = new URLSearchParams({
            window_min: String(windowMin),
            active_only: activeOnly ? 'true' : 'false',
            fresh_within: String(freshWithin),
        });

        const response = await fetch(`/api/miners/summary?${params.toString()}`, {signal});
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        let rows = [];
        try {
            const data = await response.json();
            rows = Array.isArray(data) ? data : [];
        } catch (jsonError) {
            console.warn('Failed to parse miners summary JSON:', jsonError);
            rows = [];
        }

        tbody.innerHTML = '';
        if (!rows.length) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 6;
            td.textContent = 'No miners in the selected window.';
            tr.appendChild(td);
            tbody.appendChild(tr);
            return;
        }

        // Build rows safely without innerHTML to avoid XSS and reduce reflows
        const frag = document.createDocumentFragment();
        rows.forEach(r => {
            const tr = document.createElement('tr');

            const tdLast = document.createElement('td');
            tdLast.textContent = r.last_seen || '—';
            tr.appendChild(tdLast);

            const tdIp = document.createElement('td');
            const a = document.createElement('a');
            a.href = `/dashboard/?ip=${encodeURIComponent(r.ip || '')}`;
            a.className = 'link-ip';
            a.textContent = r.ip || '';
            tdIp.appendChild(a);
            tr.appendChild(tdIp);

            const tdHash = document.createElement('td');
            tdHash.textContent = fmt(r.hashrate_ths, 3);
            tr.appendChild(tdHash);

            const tdPower = document.createElement('td');
            tdPower.textContent = fmt0(r.power_w);
            tr.appendChild(tdPower);

            const tdTemp = document.createElement('td');
            tdTemp.textContent = fmt(r.avg_temp_c, 1);
            tr.appendChild(tdTemp);

            const tdFan = document.createElement('td');
            tdFan.textContent = fmt0(r.avg_fan_rpm);
            tr.appendChild(tdFan);

            frag.appendChild(tr);
        });
        tbody.appendChild(frag);
    } catch (error) {
        if (error && error.name === 'AbortError') return; // ignore aborted requests
        console.warn('Failed to fill miners summary table:', error);
        const tbody = document.getElementById('stats-log');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6">Error loading data</td></tr>';
        }
    } finally {
        ovAbortControllers.miners = null;
    }
}

async function initOverview() {
    try {
        ensureOvCharts();
        await loadSummaryKPIs();
        await loadAggregateSeries();
        await fillMinersSummaryTable();
    } catch (error) {
        console.error('Failed to initialize overview:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadFreshPrefs();
    updateActiveWindowBadge();

    const sel = document.getElementById('fresh-within');
    const cb = document.getElementById('active-only');
    const triggerRefresh = () => {
        if (ovRefreshTimeout) clearTimeout(ovRefreshTimeout);
        ovRefreshTimeout = setTimeout(() => {
            loadSummaryKPIs();
            loadAggregateSeries();
            fillMinersSummaryTable();
        }, 150); // debounce rapid changes
    };
    if (sel) sel.addEventListener('change', () => {
        saveFreshPrefs();
        updateActiveWindowBadge();
        triggerRefresh();
    });
    if (cb) cb.addEventListener('change', () => {
        saveFreshPrefs();
        updateActiveWindowBadge();
        triggerRefresh();
    });

    initOverview();

    setInterval(() => {
        loadSummaryKPIs();
        loadAggregateSeries();
        fillMinersSummaryTable();
    }, OV_REFRESH * 1000);
});

// Destroy charts on page unload to avoid memory leaks on SPA navigations or reloads
window.addEventListener('beforeunload', () => {
    try {
        if (ovCharts) {
            Object.values(ovCharts).forEach(ch => {
                if (ch && typeof ch.destroy === 'function') ch.destroy();
            });
        }
    } catch (e) {
        console.warn('Error during chart destroy:', e);
    } finally {
        ovCharts = {};
    }
});
