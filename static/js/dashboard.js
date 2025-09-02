// === Dashboard: supports both farm-wide and single-miner modes ===
const POLL_INTERVAL = 30;
const qs = new URLSearchParams(location.search);
const QS_IP = qs.get('ip'); // if set -> single-miner mode
const FARM_ACTIVE_ONLY = true;
const FARM_FRESH_MIN = 30;   // minutes
const CHART_WINDOW_HRS = 24;   // chart lookback window
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

    // build chips safely (avoid innerHTML with QS_IP)
    el.textContent = '';
    const addChip = (text) => {
        const span = document.createElement('span');
        span.className = 'chip';
        span.textContent = text;
        el.appendChild(span);
    };

    if (QS_IP) {
        addChip(`Miner ${QS_IP}`);
        addChip(`Window ${CHART_WINDOW_HRS} h`);
    } else {
        addChip(FARM_ACTIVE_ONLY ? 'Active-only' : 'All miners');
        addChip(`Last ${FARM_FRESH_MIN} min`);
        addChip(`Charts ${CHART_WINDOW_HRS} h`);
    }
}

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

        // Optional: show which miner on single-miner page (if you have a title spot)
        const title = $('#page-title');
        if (title && QS_IP) title.textContent = `Miner ${QS_IP}`;
    } catch (e) {
        console.warn('summary failed', e);
        ['total-power', 'total-hashrate', 'total-uptime', 'avg-temp', 'avg-fan-speed', 'total-workers'].forEach(id => setText(id, '—'));
    }
}

// ----- Charts -----
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
    const windowMs = CHART_WINDOW_HRS * 60 * 60 * 1000;
    const since = new Date(Date.now() - windowMs).toISOString();
    // Approximate max rows by client poll interval
    const limit = String(Math.ceil(windowMs / (POLL_INTERVAL * 1000)) + 200); // small headroom
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
        rows = await res.json();
        if (!Array.isArray(rows)) rows = [];
    } catch (e) {
        rows = [];
    }

    if (!rows.length) {
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

            if (charts.hash) {
                charts.hash.data.labels = labels;
                charts.hash.data.datasets[0].data = hash;
                charts.hash.update();
            }
            if (charts.power) {
                charts.power.data.labels = labels;
                charts.power.data.datasets[0].data = power;
                charts.power.update();
            }
            if (charts.tempfan) {
                charts.tempfan.data.labels = labels;
                charts.tempfan.data.datasets[0].data = temp;
                charts.tempfan.data.datasets[1].data = fan;
                charts.tempfan.update();
            }
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

            if (charts.hash) {
                charts.hash.data.labels = labels;
                charts.hash.data.datasets[0].data = hash;
                charts.hash.update();
            }
            if (charts.power) {
                charts.power.data.labels = labels;
                charts.power.data.datasets[0].data = power;
                charts.power.update();
            }
            if (charts.tempfan) {
                charts.tempfan.data.labels = labels;
                charts.tempfan.data.datasets[0].data = temp;
                charts.tempfan.data.datasets[1].data = fan;
                charts.tempfan.update();
            }
        }
    }
}

// ----- Table -----
async function fillTable() {
    const tbody = $('#stats-log');
    if (!tbody) return;

    if (QS_IP) {
        // single-miner: show recent samples (last 2h)
        const since = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
        const params = new URLSearchParams({
            active_only: uiActiveOnly() ? 'true' : 'false',
            fresh_within: String(uiFreshMins())
        });
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
            const td = document.createElement('td');
            td.colSpan = 6;
            td.textContent = `No recent data for ${QS_IP}.`;
            tr.appendChild(td);
            tbody.appendChild(tr);
            return;
        }

        rows.slice(-200).forEach(r => {
            const tr = document.createElement('tr');
            const cells = [
                r.timestamp,
                r.ip || QS_IP,
                fmt(r.hashrate_ths, 3),
                fmt0(r.power_w),
                fmt(r.avg_temp_c, 1),
                fmt0(r.avg_fan_rpm),
            ];
            cells.forEach((val) => {
                const td = document.createElement('td');
                td.textContent = String(val ?? '—');
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    } else {
        // farm: one latest row per miner
        const params = new URLSearchParams({
            active_only: String(!!FARM_ACTIVE_ONLY),
            fresh_within: String(FARM_FRESH_MIN)
        });
        let rows = [];
        try {
            const res = await fetch(`/api/miners/current?${params.toString()}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            rows = await res.json();
            if (!Array.isArray(rows)) rows = [];
        } catch (e) {
            console.warn('miners/current fetch failed', e);
            rows = [];
        }

        tbody.textContent = '';
        if (!rows.length) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 6;
            td.textContent = `No active miners in the last ${FARM_FRESH_MIN} minutes.`;
            tr.appendChild(td);
            tbody.appendChild(tr);
            return;
        }

        rows.forEach(r => {
            const tr = document.createElement('tr');

            const tdLast = document.createElement('td');
            tdLast.textContent = r.last_seen || '—';
            tr.appendChild(tdLast);

            const tdIp = document.createElement('td');
            const a = document.createElement('a');
            a.href = `/dashboard/?ip=${encodeURIComponent(r.ip)}`;
            a.className = 'link-ip';
            a.textContent = r.ip;
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

            tbody.appendChild(tr);
        });
    }
}

// ----- Boot -----
document.addEventListener('DOMContentLoaded', () => {
    loadPrefs();

    // Hide farm-only controls on single-miner page if you want
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
    const ctlA = document.getElementById('ctl-active-only');
    const ctlF = document.getElementById('ctl-fresh-mins');
    const ctlC = document.getElementById('ctl-chart-hours');
    if (ctlA) ctlA.addEventListener('change', onChange);
    if (ctlF) ctlF.addEventListener('change', onChange);
    if (ctlC) ctlC.addEventListener('change', onChange);

    // Auto-refresh (still useful)
    setInterval(() => {
        fillCards();
        fillCharts();
        fillTable();
        updateFiltersBadge();
    }, POLL_INTERVAL * 1000);
});
