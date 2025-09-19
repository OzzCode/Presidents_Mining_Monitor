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
                data: {labels: [], datasets: [{label: 'TH/s', data: [], stepped: 'before', tension: 0.2, fill: false}]},
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
        const q = new URLSearchParams({since: sinceIso, limit: '3000'});
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

        // Aggregate into 5-minute bins:
        // For each bin:
        //  - compute per-miner average within the bin
        //  - sum per-miner averages for hashrate/power (farm total)
        //  - average per-miner averages for temp/fan (farm average)
        const BIN_MIN = 5;
        const bins = new Map(); // key -> { miners: Map<ip, {h_sum, h_cnt, p_sum, p_cnt, t_sum, t_cnt, f_sum, f_cnt}> }
        const binKey = (ts) => {
            const d = new Date(ts);
            if (Number.isNaN(d.getTime())) return null;
            const ms = BIN_MIN * 60 * 1000;
            return new Date(Math.floor(d.getTime() / ms) * ms).toISOString();
        };
        for (const r of list) {
            const key = binKey(r.timestamp);
            if (!key) continue;
            const ip = r.ip || r.miner_ip || 'unknown';
            let entry = bins.get(key);
            if (!entry) {
                entry = {miners: new Map()};
                bins.set(key, entry);
            }
            let m = entry.miners.get(ip);
            if (!m) {
                m = {h_sum: 0, h_cnt: 0, p_sum: 0, p_cnt: 0, t_sum: 0, t_cnt: 0, f_sum: 0, f_cnt: 0};
                entry.miners.set(ip, m);
            }
            const h = Number(r.hashrate_ths);
            if (Number.isFinite(h) && h >= 0) {
                m.h_sum += h;
                m.h_cnt++;
            }
            const p = Number(r.power_w);
            if (Number.isFinite(p) && p >= 0) {
                m.p_sum += p;
                m.p_cnt++;
            }
            const t = Number(r.avg_temp_c);
            if (Number.isFinite(t) && t > 0) {
                m.t_sum += t;
                m.t_cnt++;
            }
            const f = Number(r.avg_fan_rpm);
            if (Number.isFinite(f) && f > 0) {
                m.f_sum += f;
                m.f_cnt++;
            }
        }
        const timestamps = Array.from(bins.keys()).sort();
        const hash = timestamps.map(k => {
            const entry = bins.get(k);
            let total = 0;
            entry.miners.forEach(m => {
                const h_avg = m.h_cnt ? m.h_sum / m.h_cnt : 0;
                total += h_avg;
            });
            return total;
        });
        const power = timestamps.map(k => {
            const entry = bins.get(k);
            let total = 0;
            entry.miners.forEach(m => {
                const p_avg = m.p_cnt ? m.p_sum / m.p_cnt : 0;
                total += p_avg;
            });
            return total;
        });
        const temp = timestamps.map(k => {
            const entry = bins.get(k);
            let sum = 0, cnt = 0;
            entry.miners.forEach(m => {
                const t_avg = m.t_cnt ? m.t_sum / m.t_cnt : 0;
                if (t_avg > 0) {
                    sum += t_avg;
                    cnt++;
                }
            });
            return cnt ? (sum / cnt) : 0;
        });
        const fan = timestamps.map(k => {
            const entry = bins.get(k);
            let sum = 0, cnt = 0;
            entry.miners.forEach(m => {
                const f_avg = m.f_cnt ? m.f_sum / m.f_cnt : 0;
                if (f_avg > 0) {
                    sum += f_avg;
                    cnt++;
                }
            });
            return cnt ? (sum / cnt) : 0;
        });

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

async function loadOverviewPools() {
    const container = document.getElementById('overview-pools');
    const statusEl = document.getElementById('overview-pools-status');
    if (!container) return;
    try {
        if (statusEl) statusEl.textContent = 'Loading…';
        container.textContent = '';

        // fetch current miners (respect controls)
        const params = new URLSearchParams({
            active_only: getActiveOnly() ? 'true' : 'false',
            fresh_within: String(getFreshWithin())
        });
        const res = await fetch(`/api/miners/current?${params.toString()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const miners = await res.json().then(d => Array.isArray(d) ? d : []);
        if (!miners.length) {
            container.innerHTML = '<div style="color:#6b7280;">No miners in the selected window.</div>';
            if (statusEl) statusEl.textContent = '';
            return;
        }

        // Limit concurrency to avoid hammering API
        const maxConc = 6;
        const out = [];

        async function fetchPools(ip) {
            try {
                const pr = await fetch(`/api/miners/${encodeURIComponent(ip)}/pools`);
                const data = await pr.json().catch(() => ({}));
                return (data && Array.isArray(data.pools)) ? data.pools : [];
            } catch (e) {
                return [];
            }
        }

        let idx = 0;

        async function runBatch() {
            const batch = [];
            for (let k = 0; k < maxConc && idx < miners.length; k++, idx++) {
                const m = miners[idx];
                batch.push((async () => ({miner: m, pools: await fetchPools(m.ip)}))());
            }
            const results = await Promise.all(batch);
            out.push(...results);
        }

        while (idx < miners.length) {
            // eslint-disable-next-line no-await-in-loop
            await runBatch();
        }

        // Render
        const frag = document.createDocumentFragment();
        out.forEach(({miner, pools}) => {
            const card = document.createElement('div');
            card.className = 'card';
            card.style.padding = '10px';
            card.style.background = 'var(--surface)';
            card.style.border = '1px solid var(--border)';
            card.style.borderRadius = '8px';

            const header = document.createElement('div');
            header.style.display = 'flex';
            header.style.justifyContent = 'space-between';
            header.style.alignItems = 'center';
            const left = document.createElement('div');
            const a = document.createElement('a');
            a.href = `/dashboard/?ip=${encodeURIComponent(miner.ip)}`;
            a.textContent = miner.ip;
            a.className = 'link-ip';
            left.appendChild(a);
            if (miner.model) {
                const span = document.createElement('span');
                span.textContent = ` · ${miner.model}`;
                span.style.color = 'var(--muted)';
                span.style.fontSize = '0.9rem';
                left.appendChild(span);
            }
            header.appendChild(left);
            const kpi = document.createElement('div');
            kpi.style.color = 'var(--muted)';
            kpi.style.fontSize = '0.9rem';
            kpi.textContent = `${fmt(miner.hashrate_ths, 3)} TH/s · ${fmt0(miner.power_w)} W`;
            header.appendChild(kpi);
            card.appendChild(header);

            const list = document.createElement('ul');
            list.style.listStyle = 'none';
            list.style.margin = '8px 0 0 0';
            list.style.padding = '0';
            if (!pools.length) {
                const li = document.createElement('li');
                li.style.color = 'var(--muted)';
                li.textContent = 'No pools configured';
                list.appendChild(li);
            } else {
                pools.forEach(p => {
                    const li = document.createElement('li');
                    li.style.display = 'flex';
                    li.style.alignItems = 'center';
                    li.style.gap = '6px';
                    const dot = document.createElement('span');
                    dot.textContent = '●';
                    const active = (p.stratum_active === true) || (String(p.status || '').toLowerCase().includes('alive'));
                    dot.style.color = active ? '#22c55e' : '#9ca3af';
                    const text = document.createElement('span');
                    const url = p.url ? String(p.url) : '';
                    const user = p.user ? String(p.user) : '';
                    const pr = (p.prio !== undefined && p.prio !== null) ? ` (prio ${p.prio})` : '';
                    text.innerHTML = `${url ? `<code>${url}</code>` : ''} ${user ? `<code>${user}</code>` : ''}${pr}`;
                    li.appendChild(dot);
                    li.appendChild(text);
                    list.appendChild(li);
                });
            }
            card.appendChild(list);
            frag.appendChild(card);
        });
        container.textContent = '';
        container.appendChild(frag);
        if (statusEl) statusEl.textContent = `Updated ${new Date().toLocaleTimeString()}`;
    } catch (e) {
        console.warn('loadOverviewPools failed', e);
        if (statusEl) statusEl.textContent = 'Error';
        if (container && !container.childElementCount) {
            container.innerHTML = '<div style="color:#dc2626;">Failed to load pools.</div>';
        }
    }
}

async function initOverview() {
    try {
        ensureOvCharts();
        await loadSummaryKPIs();
        await loadAggregateSeries();
        await fillMinersSummaryTable();
        await loadOverviewPools();
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
            loadOverviewPools();
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
        loadOverviewPools();
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
