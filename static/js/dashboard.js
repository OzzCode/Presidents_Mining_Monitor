// === Dashboard: supports both farm-wide and single-miner modes ===
const POLL_INTERVAL = 30;
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

// ---- controls state ----
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
        if (document.getElementById('ctl-active-only') && ao !== null) document.getElementById('ctl-active-only').checked = ao === '1';
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

// Humanize seconds as d h m s
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

// ----- Cards -----
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
            .forEach(id => {
                const el = document.getElementById(id);
                if (!el) console.warn(`Missing element: ${id}`);
                setText(id, '—');
            });
    }
}

// ----- Charts -----
let charts = {};

function ensureCharts() {
    const ctxHash = document.getElementById("chart-hashrate")?.getContext("2d");
    const ctxPower = document.getElementById("chart-power")?.getContext("2d");
    const ctxTempFan = document.getElementById("chart-tempfan")?.getContext("2d");

    if (!charts.hash && ctxHash) {
        charts.hash = new Chart(ctxHash, {
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
    if (!charts.power && ctxPower) {
        charts.power = new Chart(ctxPower, {
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
    if (!charts.tempfan && ctxTempFan) {
        charts.tempfan = new Chart(ctxTempFan, {
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
        params.set('ip', QS_IP); // single-miner raw series
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
        // single-miner: plot raw series
        const labels = rows.map(r => r.timestamp);
        const hash = rows.map(r => Number(r.hashrate_ths || 0));
        const power = rows.map(r => Number(r.power_w || 0));
        const temp = rows.map(r => Number(r.avg_temp_c || 0));
        const fan = rows.map(r => Number(r.avg_fan_rpm || 0));

        // noinspection DuplicatedCode
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

        // noinspection DuplicatedCode
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

// ----- Table -----
async function fillTable() {
    const tbody = $('#stats-log');
    if (!tbody) return;

    if (QS_IP) {
        // single-miner: last ≤6h (keep table tight)
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
        // farm: one latest row per miner
        async function fetchCurrent(activeOnly, freshMins) {
            const params = new URLSearchParams({
                active_only: activeOnly ? 'true' : 'false',
                fresh_within: String(freshMins())
            });
            const res = await fetch(`/api/miners/current?${params.toString()}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const rows = await res.json();
            return Array.isArray(rows) ? rows : [];
        }

        let rows = [];
        try {
            // first, respect the UI window
            rows = await fetchCurrent(uiActiveOnly(), uiFreshMins());
            // if nothing, relax active_only only (do NOT change the freshness text)
            if (!rows.length && uiActiveOnly()) {
                rows = await fetchCurrent(false, uiFreshMins());
            }
        } catch (e) {
            console.warn('miners/current fetch failed', e);
            rows = [];
        }

        tbody.textContent = '';
        if (!rows.length) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="6">No miners found in the selected window.</td>`;
            tbody.appendChild(tr);
            return;
        }

        rows.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
      <td>${r.last_seen || '—'}</td>
      <td><a href="/dashboard/?ip=${encodeURIComponent(r.ip)}" class="link-ip">${r.ip}</a></td>
      <td>${fmt(r.hashrate_ths, 3)}</td>
      <td>${fmt0(r.power_w)}</td>
      <td>${fmt(r.avg_temp_c, 1)}</td>
      <td>${fmt0(r.avg_fan_rpm)}</td> `;
            tbody.appendChild(tr);
        });
    }
}

// ----- Boot -----
document.addEventListener('DOMContentLoaded', () => {
    loadPrefs();

    // Hide farm-only controls on a single-miner page if you want
    if (QS_IP) {
        const ao = document.getElementById('ctl-active-only');
        const fm = document.getElementById('ctl-fresh-mins');
        if (ao) ao.closest('label').style.display = 'none';
        if (fm) fm.closest('label').style.display = 'none';
    }

    // First render
    fillCards();
    fillCharts();
    fillTable();
    updateFiltersBadge();

    // React to control changes
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

    // Auto-refresh
    setInterval(() => {
        fillCards();
        fillCharts();
        fillTable();
        updateFiltersBadge();
    }, POLL_INTERVAL * 1000);
});
