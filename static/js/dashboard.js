// === Dashboard: supports both farm-wide and single-miner modes ===
const POLL_INTERVAL = 15; // seconds

const qs = new URLSearchParams(location.search);
const QS_IP = qs.get('ip'); // if set -> single-miner mode

// Persisted settings keys
const LS_ACTIVE_ONLY = 'dash_active_only';
const LS_FRESH_MINS = 'dash_fresh_mins';
const LS_CHART_HOURS = 'dash_chart_hours';

// Defaults
const DEF_ACTIVE_ONLY = true;
const DEF_FRESH_MINS = 30;
const DEF_CHART_HOURS = 24;

// ------------- helpers -------------
function $(sel) {
    return typeof sel === 'string' && sel.startsWith('#')
        ? document.querySelector(sel)
        : document.getElementById(sel);
}

function setText(id, text) {
    const el = $(id);
    if (el) el.textContent = text;
}

function num(n, d = 0) {
    const v = Number(n);
    return Number.isFinite(v) ? (d ? Number(v.toFixed(d)) : Math.round(v)) : 0;
}

function fmt(n, d = 3) {
    const v = Number(n);
    return Number.isFinite(v) ? v.toFixed(d) : '0';
}

function fmt0(n) {
    const v = Number(n);
    return Number.isFinite(v) ? Math.round(v).toString() : '0';
}

function humanDuration(seconds) {
    const s = Math.max(0, Math.floor(Number(seconds) || 0));
    const d = Math.floor(s / 86400);
    const h = Math.floor((s % 86400) / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (d) return `${d}d ${h}h ${m}m`;
    if (h) return `${h}h ${m}m`;
    if (m) return `${m}m ${sec}s`;
    return `${sec}s`;
}

// ------------- controls state -------------
function uiActiveOnly() {
    const el = document.getElementById('ctl-active-only');
    return el ? !!el.checked : DEF_ACTIVE_ONLY;
}

function uiFreshMins() {
    const el = document.getElementById('ctl-fresh-mins');
    const n = el ? parseInt(el.value, 10) : DEF_FRESH_MINS;
    return Number.isFinite(n) ? n : DEF_FRESH_MINS;
}

function uiChartHours() {
    const el = document.getElementById('ctl-chart-hours');
    const n = el ? parseInt(el.value, 10) : DEF_CHART_HOURS;
    return Number.isFinite(n) ? n : DEF_CHART_HOURS;
}

function loadPrefs() {
    try {
        const ao = localStorage.getItem(LS_ACTIVE_ONLY);
        const fm = localStorage.getItem(LS_FRESH_MINS);
        const ch = localStorage.getItem(LS_CHART_HOURS);
        if (document.getElementById('ctl-active-only') && ao !== null) document.getElementById('ctl-active-only').checked = (ao === '1');
        if (document.getElementById('ctl-fresh-mins') && fm) document.getElementById('ctl-fresh-mins').value = fm;
        if (document.getElementById('ctl-chart-hours') && ch) document.getElementById('ctl-chart-hours').value = ch;
    } catch {
    }
}

function savePrefs() {
    try {
        localStorage.setItem(LS_ACTIVE_ONLY, uiActiveOnly() ? '1' : '0');
        localStorage.setItem(LS_FRESH_MINS, String(uiFreshMins()));
        localStorage.setItem(LS_CHART_HOURS, String(uiChartHours()));
    } catch {
    }
}

function updateFiltersBadge() {
    const el = document.getElementById('filters-badge');
    if (!el) return;
    if (QS_IP) {
        el.innerHTML = `<span class="chip">Miner ${QS_IP}</span><span class="chip">Window ${uiChartHours()} h</span>`;
    } else {
        el.innerHTML =
            `<span class="chip">${uiActiveOnly() ? 'Active-only' : 'All miners'}</span>` +
            `<span class="chip">Last ${uiFreshMins()} min</span>` +
            `<span class="chip">Charts ${uiChartHours()} h</span>`;
    }
}

// ------------- cards -------------
async function fillCards() {
    const url = QS_IP ? `/api/summary?ip=${encodeURIComponent(QS_IP)}` : '/api/summary';
    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const s = await res.json();

        setText('total-power', `${num(s.total_power, 1)} W`);
        setText('total-hashrate', `${num(s.total_hashrate, 3)} TH/s`);
        setText('total-uptime', humanDuration(s.total_uptime));
        setText('avg-temp', `${num(s.avg_temp, 1)} °C`);
        setText('avg-fan-speed', `${num(s.avg_fan_speed)} RPM`);
        setText('total-workers', `${num(s.total_workers)}`);

        const stamp = $('#last-update');
        if (stamp) stamp.textContent = `Last update: ${new Date().toLocaleString()}`;
        const srv = $('#server-update');
        if (srv && s.last_updated) {
            const dt = new Date(s.last_updated);
            srv.textContent = `Server time: ${Number.isNaN(dt.getTime()) ? s.last_updated : dt.toLocaleString()}`;
        }
        const title = $('#page-title');
        if (title && QS_IP) title.textContent = `Miner ${QS_IP}`;
    } catch (e) {
        console.warn('summary failed', e);
        ['total-power', 'total-hashrate', 'total-uptime', 'avg-temp', 'avg-fan-speed', 'total-workers']
            .forEach(id => setText(id, '—'));
    }
}

// ------------- charts -------------
let lastMetricsTimestamp = null;

async function pollAndUpdateCharts() {
    // Use single-miner mode if QS_IP is set
    const url = QS_IP ? `/api/metrics?ip=${encodeURIComponent(QS_IP)}&limit=1` : '/api/summary';

    try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        let newPoint;
        if (QS_IP && Array.isArray(data) && data.length > 0) {
            newPoint = data[data.length - 1];
        } else if (data && data.log && data.log.length > 0) {
            newPoint = data.log[data.log.length - 1];
        }

        if (newPoint && newPoint.timestamp !== lastMetricsTimestamp) {
            lastMetricsTimestamp = newPoint.timestamp;

            // Push new data point to each chart
            if (charts.hash) {
                charts.hash.data.labels.push(newPoint.timestamp);
                charts.hash.data.datasets[0].data.push(Number(newPoint.hashrate_ths || newPoint.hash || 0));
                if (charts.hash.data.labels.length > 120) { // limit to 120 points
                    charts.hash.data.labels.shift();
                    charts.hash.data.datasets[0].data.shift();
                }
                charts.hash.update('none');
            }
            if (charts.power) {
                charts.power.data.labels.push(newPoint.timestamp);
                charts.power.data.datasets[0].data.push(Number(newPoint.power_w || 0));
                if (charts.power.data.labels.length > 120) {
                    charts.power.data.labels.shift();
                    charts.power.data.datasets[0].data.shift();
                }
                charts.power.update('none');
            }
            if (charts.tempfan) {
                charts.tempfan.data.labels.push(newPoint.timestamp);
                charts.tempfan.data.datasets[0].data.push(Number(newPoint.avg_temp_c || 0));
                charts.tempfan.data.datasets[1].data.push(Number(newPoint.avg_fan_rpm || 0));
                if (charts.tempfan.data.labels.length > 120) {
                    charts.tempfan.data.labels.shift();
                    charts.tempfan.data.datasets[0].data.shift();
                    charts.tempfan.data.datasets[1].data.shift();
                }
                charts.tempfan.update('none');
            }
        }
    } catch (e) {
        console.warn('Live update failed:', e);
    }
}

let charts = {};

function ensureCharts() {
    const elHash = $('#chart-hashrate');
    const elPower = $('#chart-power');
    const elTempFan = $('#chart-tempfan');

    if (!charts.hash && elHash) {
        charts.hash = new Chart(elHash, {
            type: 'line',
            data: {labels: [], datasets: [{label: 'TH/s', data: [], tension: 0.2, fill: false}]},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {x: {type: 'time', time: {unit: 'hour'}}, y: {beginAtZero: true}},
                plugins: {legend: {display: false}}
            }
        });
    }
    if (!charts.power && elPower) {
        charts.power = new Chart(elPower, {
            type: 'line',
            data: {labels: [], datasets: [{label: 'W', data: [], tension: 0.2, fill: false}]},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {x: {type: 'time', time: {unit: 'hour'}}, y: {beginAtZero: true}},
                plugins: {legend: {display: false}}
            }
        });
    }
    if (!charts.tempfan && elTempFan) {
        charts.tempfan = new Chart(elTempFan, {
            type: 'line',
            data: {
                labels: [], datasets: [
                    {label: 'Temp (°C)', data: [], yAxisID: 'y', tension: 0.2, fill: false},
                    {label: 'Fan (RPM)', data: [], yAxisID: 'y1', tension: 0.2, fill: false}
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false, scales: {
                    x: {type: 'time', time: {unit: 'hour'}},
                    y: {beginAtZero: true, position: 'left'},
                    y1: {beginAtZero: true, position: 'right', grid: {drawOnChartArea: false}}
                }
            }
        });
    }
}

function binTs(ts, minutes = 5) {
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return null;
    const ms = minutes * 60 * 1000;
    return new Date(Math.floor(d.getTime() / ms) * ms).toISOString();
}

async function fillCharts() {
    ensureCharts();

    const since = new Date(Date.now() - uiChartHours() * 60 * 60 * 1000).toISOString();
    const params = new URLSearchParams({since, limit: '3000'});
    if (QS_IP) {
        params.set('ip', QS_IP);
    } else {
        params.set('active_only', uiActiveOnly() ? 'true' : 'false');
        params.set('fresh_within', String(uiFreshMins()));
    }

    let rows = [];
    try {
        const res = await fetch(`/api/metrics?${params.toString()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        rows = await res.json();
        if (!Array.isArray(rows)) rows = [];
    } catch (e) {
        console.warn('metrics fetch failed', e);
        rows = [];
    }

    if (!rows.length) {
        Object.values(charts).forEach(c => {
            if (!c) return;
            c.data.labels = [];
            c.data.datasets.forEach(d => d.data = []);
            c.update();
        });
        return;
    }

    if (QS_IP) {
        // single-miner: raw series
        const labels = rows.map(r => r.timestamp);
        const hash = rows.map(r => Number(r.hashrate_ths || 0));
        const power = rows.map(r => Number(r.power_w || 0));
        const temp = rows.map(r => Number(r.avg_temp_c || 0));
        const fan = rows.map(r => Number(r.avg_fan_rpm || 0));

        charts.hash.data.labels = labels;
        charts.hash.data.datasets[0].data = hash;
        charts.hash.update();
        charts.power.data.labels = labels;
        charts.power.data.datasets[0].data = power;
        charts.power.update();
        charts.tempfan.data.labels = labels;
        charts.tempfan.data.datasets[0].data = temp;
        charts.tempfan.data.datasets[1].data = fan;
        charts.tempfan.update();
    } else {
        // farm: aggregate into 5-min bins (sum hash/power, avg temp/fan)
        const bins = new Map();
        rows.forEach(r => {
            const key = binTs(r.timestamp, 5);
            if (!key) return;
            const o = bins.get(key) || {hash: 0, power: 0, temp: 0, fan: 0, tc: 0, fc: 0};
            o.hash += Number(r.hashrate_ths || 0);
            o.power += Number(r.power_w || 0);
            const t = Number(r.avg_temp_c || 0);
            if (Number.isFinite(t) && t > 0) {
                o.temp += t;
                o.tc++;
            }
            const f = Number(r.avg_fan_rpm || 0);
            if (Number.isFinite(f) && f > 0) {
                o.fan += f;
                o.fc++;
            }
            bins.set(key, o);
        });

        const labels = Array.from(bins.keys()).sort();
        const hash = labels.map(k => bins.get(k).hash);
        const power = labels.map(k => bins.get(k).power);
        const temp = labels.map(k => {
            const b = bins.get(k);
            return b.tc ? b.temp / b.tc : 0;
        });
        const fan = labels.map(k => {
            const b = bins.get(k);
            return b.fc ? b.fan / b.fc : 0;
        });

        charts.hash.data.labels = labels;
        charts.hash.data.datasets[0].data = hash;
        charts.hash.update();
        charts.power.data.labels = labels;
        charts.power.data.datasets[0].data = power;
        charts.power.update();
        charts.tempfan.data.labels = labels;
        charts.tempfan.data.datasets[0].data = temp;
        charts.tempfan.data.datasets[1].data = fan;
        charts.tempfan.update();
    }
}

// ------------- table -------------
async function fillTable() {
    const tbody = $('#stats-log');
    if (!tbody) return;

    if (QS_IP) {
        // single-miner: last ≤6h to keep the table readable
        const hours = Math.min(uiChartHours(), 6);
        const since = new Date(Date.now() - hours * 60 * 60 * 1000).toISOString();
        const params = new URLSearchParams({since, limit: '500', ip: QS_IP});

        let rows = [];
        try {
            const res = await fetch(`/api/metrics?${params.toString()}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            rows = await res.json();
            if (!Array.isArray(rows)) rows = [];
        } catch (e) {
            console.warn('metrics(table) fetch failed', e);
            rows = [];
        }

        tbody.textContent = '';
        if (!rows.length) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="6">No recent data for ${QS_IP}.</td>`;
            tbody.appendChild(tr);
            return;
        }

        rows.slice(-200).forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
        <td>${r.model}</td>
        <td>${r.timestamp}</td>
        <td>${r.ip || QS_IP}</td>
        <td>${fmt(r.hashrate_ths, 3)}</td>
        <td>${fmt0(r.power_w)}</td>
        <td>${fmt(r.avg_temp_c, 1)}</td>
        <td>${fmt0(r.avg_fan_rpm)}</td>
      `;
            tbody.appendChild(tr);
        });
    } else {
        // farm: one latest row per miner (strictly follow UI window)
        async function fetchCurrent(activeOnly, freshMinsVal) {
            const min = Number.isFinite(Number(freshMinsVal)) ? Number(freshMinsVal) : 30;
            const params = new URLSearchParams({
                active_only: activeOnly ? 'true' : 'false',
                fresh_within: String(min)
            });
            const res = await fetch(`/api/miners/current?${params.toString()}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            return Array.isArray(data) ? data : [];
        }

        let rows = [];
        try {
            rows = await fetchCurrent(uiActiveOnly(), uiFreshMins());
        } catch (e) {
            console.warn('miners/current fetch failed', e);
            rows = [];
        }

        tbody.textContent = '';
        if (!rows.length) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="7">No miners found in the selected window.</td>`;
            tbody.appendChild(tr);
            return;
        }

        rows.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
        <td>${r.model || '—'}</td>
        <td>${r.last_seen || '—'}</td>
        <td><a href="/dashboard/?ip=${encodeURIComponent(r.ip)}" class="link-ip">${r.ip}</a></td>
        <td>${fmt(r.hashrate_ths, 3)}</td>
        <td>${fmt0(r.power_w)}</td>
        <td>${fmt(r.avg_temp_c, 1)}</td>
        <td>${fmt0(r.avg_fan_rpm)}</td>
      `;
            tbody.appendChild(tr);
        });
    }
}


// ------------- pools (single-miner) -------------
async function loadPools() {
    if (!QS_IP) return;
    const tbody = document.getElementById('pools-tbody');
    const statusEl = document.getElementById('pools-status');
    if (!tbody) return;
    try {
        if (statusEl) statusEl.textContent = 'Loading…';
        const res = await fetch(`/api/miners/${encodeURIComponent(QS_IP)}/pools`);
        const data = await res.json().catch(() => ({}));
        tbody.textContent = '';
        if (!res.ok || !data || !Array.isArray(data.pools)) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="10" style="color:#dc2626;">Failed to load pools.</td>`;
            tbody.appendChild(tr);
            if (statusEl) statusEl.textContent = 'Error';
            return;
        }
        if (data.pools.length === 0) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="10" style="color:#888;">No pools configured.</td>`;
            tbody.appendChild(tr);
        } else {
            data.pools.forEach(p => {
                const tr = document.createElement('tr');
                const pr = (p.prio !== undefined && p.prio !== null) ? p.prio : '';
                const sa = (p.stratum_active === true) ? 'Active' : (p.stratum_active === false ? '—' : '');
                const acc = (typeof p.accepted === 'number') ? p.accepted : (p.accepted ? Number(p.accepted) : 0);
                const rej = (typeof p.rejected === 'number') ? p.rejected : (p.rejected ? Number(p.rejected) : 0);
                const stl = (typeof p.stale === 'number') ? p.stale : (p.stale ? Number(p.stale) : 0);
                const rp = (typeof p.reject_percent === 'number') ? p.reject_percent : (p.reject_percent ? Number(p.reject_percent) : 0);
                tr.innerHTML = `
                    <td>${p.id ?? ''}</td>
                    <td>${p.url ? `<code>${p.url}</code>` : ''}</td>
                    <td>${p.user ? `<code>${p.user}</code>` : ''}</td>
                    <td>${p.status || ''}</td>
                    <td>${pr}</td>
                    <td>${sa}</td>
                    <td>${acc}</td>
                    <td>${rej}</td>
                    <td>${stl}</td>
                    <td>${rp.toFixed ? rp.toFixed(2) : Number(rp).toFixed(2)}%</td>
                `;
                tbody.appendChild(tr);
            });
        }
        if (statusEl) statusEl.textContent = `Updated ${new Date().toLocaleTimeString()}`;
    } catch (e) {
        tbody.textContent = '';
        const tr = document.createElement('tr');
        tr.innerHTML = `<td colspan="10" style="color:#dc2626;">${String(e)}</td>`;
        tbody.appendChild(tr);
        if (statusEl) statusEl.textContent = 'Error';
    }
}

// ------------- live -------------
function pulseLiveIndicator() {
    const el = document.getElementById('live-indicator');
    if (el) {
        el.style.opacity = 1;
        setTimeout(() => {
            el.style.opacity = 0.5;
        }, 400);
    }
}


(function () {
  const KEY = 'theme';
  const root = document.documentElement;
  const getOSPref = () => (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  const apply = (t) => {
    if (t) root.setAttribute('data-theme', t);
    else root.removeAttribute('data-theme'); // fall back to OS
  };

  // Initialize from localStorage or OS
  const saved = localStorage.getItem(KEY);
  apply(saved || null);

  // Keep in sync with OS if user hasn’t chosen
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  mq.addEventListener?.('change', () => {
    if (!localStorage.getItem(KEY)) apply(null);
  });

  // Toggle handler
  const btn = document.getElementById('themeToggle');
  if (btn) {
    btn.addEventListener('click', () => {
      const current = root.getAttribute('data-theme') || (saved ? saved : null) || getOSPref();
      const next = current === 'dark' ? 'light' : 'dark';
      localStorage.setItem(KEY, next);
      apply(next);
    });
  }
})();


// ------------- boot -------------
document.addEventListener('DOMContentLoaded', () => {
    loadPrefs();
    pulseLiveIndicator();

    // Hide farm-only controls on single-miner page (optional)
    if (QS_IP) {
        const ao = document.getElementById('ctl-active-only');
        const fm = document.getElementById('ctl-fresh-mins');
        if (ao) ao.closest('label').style.display = 'none';
        if (fm) fm.closest('label').style.display = 'none';
    }

    const onChange = () => {
        savePrefs();
        fillCharts();
        fillTable();
        updateFiltersBadge();
    };
    ['ctl-active-only', 'ctl-fresh-mins', 'ctl-chart-hours'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', onChange);
    });

    fillCards();
    fillCharts();
    fillTable();
    updateFiltersBadge();

    // Pools UI
    if (QS_IP) {
        const btn = document.getElementById('btn-refresh-pools');
        if (btn) btn.addEventListener('click', () => loadPools());
        loadPools();
        // Optional: refresh pools periodically along with charts/cards
        setInterval(loadPools, POLL_INTERVAL * 2000); // every 30s if POLL_INTERVAL=15
    }

    setInterval(pollAndUpdateCharts,
        POLL_INTERVAL * 1000);
    setInterval(() => {
        fillCards();
        fillCharts();
        fillTable();
        updateFiltersBadge();
    }, POLL_INTERVAL * 1000);
});
