// Poll every 30s
const POLL_INTERVAL = 30;

// Derive miner IP from querystring if you don't inject MINER_IP from the server
const qs = new URLSearchParams(location.search);
const QS_IP = qs.get('ip');

// Build the summary URL
const summaryUrl = QS_IP ? `/api/summary?ip=${encodeURIComponent(QS_IP)}` : '/api/summary';

// Small helpers
function $(id) {
    return document.getElementById(id);
}

function setText(id, text) {
    const el = $(id);
    if (el) el.textContent = text;
}

function num(n, digits = 0) {
    const v = Number(n);
    if (!Number.isFinite(v)) return 0;
    return digits > 0 ? Number(v.toFixed(digits)) : Math.round(v);
}

async function fetchSummaryAndFillCards() {
    try {
        const res = await fetch(summaryUrl);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // Expected keys from /api/summary:
        // total_power, total_hashrate, total_uptime, avg_temp, avg_fan_speed, total_workers
        setText('total-power', `${num(data.total_power, 1)} W`);        // add "(est.)" if you want
        setText('total-hashrate', `${num(data.total_hashrate, 3)} TH/s`);
        setText('total-uptime', `${num(data.total_uptime)} s`);
        setText('avg-temp', `${num(data.avg_temp, 1)} °C`);
        setText('avg-fan-speed', `${num(data.avg_fan_speed)} RPM`);
        setText('total-workers', `${num(data.total_workers)}`);

        // Optional: show when the page last fetched
        const stamp = $('last-update');
        if (stamp) stamp.textContent = `Last update: ${new Date().toLocaleString()}`;

        // Optional: if you return data.last_updated from the API, you can display it too
        const fromServer = $('server-update');
        if (fromServer && data.last_updated) {
            fromServer.textContent = `Server time: ${new Date(data.last_updated).toLocaleString()}`;
        }
    } catch (err) {
        console.warn('summary fetch failed', err);
        // Show safe placeholders so cards don’t stay blank if a fetch fails
        ['total-power', 'total-hashrate', 'total-uptime', 'avg-temp', 'avg-fan-speed', 'total-workers']
            .forEach(id => setText(id, '—'));
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchSummaryAndFillCards();
    setInterval(fetchSummaryAndFillCards, POLL_INTERVAL * 1000);
});


const ipParam = typeof MINER_IP !== 'undefined' ? MINER_IP : null;

// Build the metrics URL for the last 24 hours
function metricsUrl() {
    const now = new Date();
    const since = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
    const p = new URLSearchParams({since, limit: "3000"});
    if (ipParam) p.set("ip", ipParam);
    return `/api/metrics?${p.toString()}`;
}

let charts = {};

function ensureCharts() {
    if (!charts.hash) {
        charts.hash = new Chart(document.getElementById('chart-hashrate'), {
            type: 'line',
            data: {labels: [], datasets: [{label: 'TH/s', data: [], tension: 0.2, fill: false}]},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {x: {ticks: {maxRotation: 0}, type: 'time', time: {unit: 'hour'}}, y: {beginAtZero: true}},
                plugins: {legend: {display: false}}
            }
        });
    }
    if (!charts.power) {
        charts.power = new Chart(document.getElementById('chart-power'), {
            type: 'line',
            data: {labels: [], datasets: [{label: 'W', data: [], tension: 0.2, fill: false}]},
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {x: {ticks: {maxRotation: 0}, type: 'time', time: {unit: 'hour'}}, y: {beginAtZero: true}},
                plugins: {legend: {display: false}}
            }
        });
    }
    if (!charts.tempfan) {
        charts.tempfan = new Chart(document.getElementById('chart-tempfan'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {label: 'Temp (°C)', data: [], yAxisID: 'y', tension: 0.2, fill: false},
                    {label: 'Fan (RPM)', data: [], yAxisID: 'y1', tension: 0.2, fill: false}
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {ticks: {maxRotation: 0}, type: 'time', time: {unit: 'hour'}},
                    y: {beginAtZero: true, position: 'left'},
                    y1: {beginAtZero: true, position: 'right', grid: {drawOnChartArea: false}}
                }
            }
        });
    }
}

function setNoData(chart, msg) {
    // Optionally you can overlay a message; for simplicity, clear data
    chart.data.labels = [];
    chart.data.datasets.forEach(d => d.data = []);
    chart.update();
    console.warn(msg);
}

async function loadAndRender() {
    ensureCharts();

    let rows = [];
    try {
        const res = await fetch(metricsUrl());
        rows = await res.json();
        if (!Array.isArray(rows)) rows = [];
    } catch (e) {
        console.error('metrics fetch failed', e);
        Object.values(charts).forEach(c => setNoData(c, 'Fetch failed'));
        return;
    }

    if (!rows.length) {
        Object.values(charts).forEach(c => setNoData(c, 'No rows'));
        return;
    }

    // Map fields from API to Chart.js points
    const labels = rows.map(r => r.timestamp);
    const hash = rows.map(r => Number(r.hashrate_ths || 0));
    const power = rows.map(r => Number(r.power_w || 0));
    const temp = rows.map(r => Number(r.avg_temp_c || 0));
    const fan = rows.map(r => Number(r.avg_fan_rpm || 0));

    // Update charts
    charts.hash.data.labels = labels;
    charts.hash.data.datasets[0].data = hash;
    charts.hash.update();

    charts.power.data.labels = labels;
    charts.power.data.datasets[0].data = power;
    charts.power.update();

    charts.tempfan.data.labels = labels;
    charts.tempfan.data.datasets[0].data = temp; // Temp (°C)
    charts.tempfan.data.datasets[1].data = fan;  // RPM
    charts.tempfan.update();
}

document.addEventListener('DOMContentLoaded', () => {
    loadAndRender();
    setInterval(loadAndRender, POLL_INTERVAL * 1000);
});


// // static/js/dashboard.js
// const POWER_EL = document.getElementById('card-power');    // e.g. <div id="card-power">
// const HASH_EL = document.getElementById('card-hash');     // <div id="card-hash">
// const UPTIME_EL = document.getElementById('card-uptime');
// const TEMP_EL = document.getElementById('card-temp');
// const FAN_EL = document.getElementById('card-fan');
// const WORKERS_EL = document.getElementById('card-workers');
// const LOG_TBODY = document.getElementById('stats-tbody');   // <tbody id="stats-tbody">
//
// const REFRESH_MS = 30000;
//
// function fmt(n, unit) {
//     if (n === null || n === undefined) return `-- ${unit || ''}`.trim();
//     const v = (typeof n === 'number') ? n : Number(n);
//     return isNaN(v) ? `-- ${unit || ''}`.trim() : `${v}${unit ? ` ${unit}` : ''}`;
// }
//
// async function fetchSummary() {
//     let url = '/api/summary';
//     if (typeof MINER_IP !== 'undefined' && MINER_IP) url += `?ip=${encodeURIComponent(MINER_IP)}`;
//     console.log('Fetching summary:', url);
//     const res = await fetch(url);
//     if (!res.ok) throw new Error(`summary ${res.status}`);
//     return res.json();
// }
//
// function renderSummary(d) {
//     POWER_EL && (POWER_EL.textContent = fmt(d.total_power?.toFixed?.(1) ?? d.total_power, 'W'));
//     HASH_EL && (HASH_EL.textContent = fmt(d.total_hashrate?.toFixed?.(2) ?? d.total_hashrate, 'TH/s'));
//     UPTIME_EL && (UPTIME_EL.textContent = fmt(d.total_uptime, 's'));
//     TEMP_EL && (TEMP_EL.textContent = fmt(d.avg_temp?.toFixed?.(1) ?? d.avg_temp, '°C'));
//     FAN_EL && (FAN_EL.textContent = fmt(d.avg_fan_speed?.toFixed?.(0) ?? d.avg_fan_speed, 'RPM'));
//
//     // If we're scoped to a single IP, workers == 1; otherwise use API value
//     const workers = (typeof MINER_IP !== 'undefined' && MINER_IP) ? 1 : (d.total_workers ?? '--');
//     WORKERS_EL && (WORKERS_EL.textContent = workers);
//
//     if (LOG_TBODY && Array.isArray(d.log)) {
//         LOG_TBODY.innerHTML = '';
//         d.log.slice(-10).forEach(row => {
//             const tr = document.createElement('tr');
//             tr.innerHTML = `
//         <td>${row.timestamp ?? ''}</td>
//         <td>${row.ip ?? ''}</td>
//         <td>${(row.hash ?? '').toString()}</td>
//       `;
//             LOG_TBODY.appendChild(tr);
//         });
//     }
// }
//
// async function poll() {
//     try {
//         const data = await fetchSummary();
//         renderSummary(data);
//     } catch (e) {
//         console.error('Summary fetch failed:', e);
//         // keep placeholders, don’t crash
//     }
// }
//
// window.addEventListener('DOMContentLoaded', () => {
//     poll();
//     setInterval(poll, REFRESH_MS);
// });