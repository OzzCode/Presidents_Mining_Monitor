// Overview charts — farm-wide
const OV_REFRESH = 30; // seconds

let ovCharts = {};

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
    } catch {
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
    } catch {
    }
}

function updateActiveWindowBadge() {
    const el = document.getElementById('active-window-badge');
    if (!el) return;
    const mins = getFreshWithin();
    el.textContent = `Active window: last ${mins} min`;
}

function ensureOvCharts() {
    if (!ovCharts.hash) {
        ovCharts.hash = new Chart(document.getElementById('overview-hash'), {
            type: 'line',
            data: {labels: [], datasets: [{label: 'TH/s', data: [], tension: 0.2, fill: false}]},
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {x: {type: 'time', time: {unit: 'hour'}}, y: {beginAtZero: true}},
                plugins: {legend: {display: false}}
            }
        });
    }
    if (!ovCharts.power) {
        ovCharts.power = new Chart(document.getElementById('overview-power'), {
            type: 'line',
            data: {labels: [], datasets: [{label: 'W', data: [], tension: 0.2, fill: false}]},
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {x: {type: 'time', time: {unit: 'hour'}}, y: {beginAtZero: true}},
                plugins: {legend: {display: false}}
            }
        });
    }
    if (!ovCharts.tempfan) {
        ovCharts.tempfan = new Chart(document.getElementById('overview-tempfan'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {label: 'Temp (°C)', data: [], yAxisID: 'y', tension: 0.2, fill: false},
                    {label: 'Fan (RPM)', data: [], yAxisID: 'y1', tension: 0.2, fill: false}
                ]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: {
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

async function loadSummaryKPIs() {
    try {
        const res = await fetch('/api/summary');
        const s = await res.json();
        document.getElementById('kpi-hash').textContent = `${s.total_hashrate} TH/s`;
        document.getElementById('kpi-power').textContent = `${s.total_power} W (est.)`;
        document.getElementById('kpi-temp').textContent = `${s.avg_temp} °C`;
        document.getElementById('kpi-workers').textContent = s.total_workers;
    } catch (e) {
        console.warn('summary fetch failed', e);
    } finally {
        updateActiveWindowBadge();
    }
}

async function loadAggregateSeries() {
    const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    const freshWithin = getFreshWithin();
    const activeOnly = getActiveOnly();

    const url = `/api/metrics?since=${encodeURIComponent(since)}&limit=3000`
        + `&active_only=${activeOnly ? 'true' : 'false'}`
        + `&fresh_within=${encodeURIComponent(freshWithin)}`;

    let rows = [];
    try {
        const res = await fetch(url);
        rows = await res.json();
        if (!Array.isArray(rows)) rows = [];
    } catch (e) {
        console.warn('metrics fetch failed', e);
        rows = [];
    }

    if (!rows.length) {
        ['hash', 'power', 'tempfan'].forEach(k => {
            if (ovCharts[k]) {
                ovCharts[k].data.labels = [];
                ovCharts[k].data.datasets.forEach(d => d.data = []);
                ovCharts[k].update();
            }
        });
        return;
    }

    const bins = new Map();
    rows.forEach(r => {
        const key = binTs(r.timestamp, 5);
        if (!key) return;
        const obj = bins.get(key) || {hash: 0, power: 0, temp: 0, fan: 0, count: 0, temp_count: 0, fan_count: 0};
        obj.hash += Number(r.hashrate_ths || 0);
        obj.power += Number(r.power_w || 0);
        const tv = Number(r.avg_temp_c || 0);
        if (tv > 0) {
            obj.temp += tv;
            obj.temp_count += 1;
        }
        const fv = Number(r.avg_fan_rpm || 0);
        if (fv > 0) {
            obj.fan += fv;
            obj.fan_count += 1;
        }
        obj.count += 1;
        bins.set(key, obj);
    });

    const labels = Array.from(bins.keys()).sort();
    const hash = labels.map(k => bins.get(k).hash);
    const power = labels.map(k => bins.get(k).power);
    const temp = labels.map(k => {
        const b = bins.get(k);
        return b.temp_count ? b.temp / b.temp_count : 0;
    });
    const fan = labels.map(k => {
        const b = bins.get(k);
        return b.fan_count ? b.fan / b.fan_count : 0;
    });

    ovCharts.hash.data.labels = labels;
    ovCharts.hash.data.datasets[0].data = hash;
    ovCharts.hash.update();

    ovCharts.power.data.labels = labels;
    ovCharts.power.data.datasets[0].data = power;
    ovCharts.power.update();

    ovCharts.tempfan.data.labels = labels;
    ovCharts.tempfan.data.datasets[0].data = temp;
    ovCharts.tempfan.data.datasets[1].data = fan;
    ovCharts.tempfan.update();
}

function fmt(n, d = 3) {
    const v = Number(n);
    return Number.isFinite(v) ? v.toFixed(d) : '0';
}

function fmt(n, d = 3) {
    const v = Number(n);
    return Number.isFinite(v) ? v.toFixed(d) : '0';
}

function fmt0(n) {
    const v = Number(n);
    return Number.isFinite(v) ? Math.round(v).toString() : '0';
}

async function fillMinersSummaryTable() {
    const tbody = document.getElementById('stats-log');
    if (!tbody) return;

    const windowMin = Math.max(getFreshWithin(), 30);
    const freshWithin = getFreshWithin();
    const activeOnly = getActiveOnly();

    const params = new URLSearchParams({
        window_min: String(windowMin),
        active_only: activeOnly ? 'true' : 'false',
        fresh_within: String(freshWithin),
    });

    let rows = [];
    try {
        const res = await fetch(`/api/miners/summary?${params.toString()}`);
        rows = await res.json();
        if (!Array.isArray(rows)) rows = [];
    } catch (e) {
        console.warn('miners/summary fetch failed', e);
        rows = [];
    }

    tbody.innerHTML = '';
    if (!rows.length) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td colspan="5">No miners in the selected window.</td>`;
        tbody.appendChild(tr);
        return;
    }

    rows.forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${r.last_seen || '—'}</td> <td><a href="/dashboard/?ip=${encodeURIComponent(r.ip)}" class="link-ip">${r.ip}</a></td> <td>${fmt(r.hashrate_ths, 3)}</td> <td>${fmt0(r.power_w)}</td> <td>${fmt(r.avg_temp_c, 1)}</td> <td>${fmt0(r.avg_fan_rpm)}</td> `;
        tbody.appendChild(tr);
    });
}


async function initOverview() {
    ensureOvCharts();
    await loadSummaryKPIs();
    await loadAggregateSeries();
    await fillMinersSummaryTable();
}

document.addEventListener('DOMContentLoaded', () => {
    loadFreshPrefs();
    updateActiveWindowBadge();

    const sel = document.getElementById('fresh-within');
    const cb = document.getElementById('active-only');
    if (sel) sel.addEventListener('change', () => {
        saveFreshPrefs();
        updateActiveWindowBadge();
        loadSummaryKPIs();
        loadAggregateSeries();
        fillMinersSummaryTable();
    });
    if (cb) cb.addEventListener('change', () => {
        saveFreshPrefs();
        updateActiveWindowBadge();
        loadSummaryKPIs();
        loadAggregateSeries();
        fillMinersSummaryTable();
    });

    initOverview();
    setInterval(() => {
        loadSummaryKPIs();
        loadAggregateSeries();
        fillMinersSummaryTable();
    }, OV_REFRESH * 1000);
});
