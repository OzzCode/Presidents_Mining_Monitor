// Poll every 30s
const POLL_INTERVAL = 30;

const qs = new URLSearchParams(location.search);
const QS_IP = qs.get('ip');

const summaryUrl = QS_IP ? `/api/summary?ip=${encodeURIComponent(QS_IP)}` : '/api/summary';

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

        setText('total-power', `${num(data.total_power, 1)} W`);
        setText('total-hashrate', `${num(data.total_hashrate, 3)} TH/s`);
        setText('total-uptime', `${num(data.total_uptime)} s`);
        setText('avg-temp', `${num(data.avg_temp, 1)} °C`);
        setText('avg-fan-speed', `${num(data.avg_fan_speed)} RPM`);
        setText('total-workers', `${num(data.total_workers)}`);

        const stamp = $('last-update');
        if (stamp) stamp.textContent = `Last update: ${new Date().toLocaleString()}`;
        const fromServer = $('server-update');
        if (fromServer && data.last_updated) {
            fromServer.textContent = `Server time: ${new Date(data.last_updated).toLocaleString()}`;
        }
    } catch (err) {
        console.warn('summary fetch failed', err);
        ['total-power', 'total-hashrate', 'total-uptime', 'avg-temp', 'avg-fan-speed', 'total-workers']
            .forEach(id => setText(id, '—'));
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchSummaryAndFillCards();
    setInterval(fetchSummaryAndFillCards, POLL_INTERVAL * 1000);
});

const ipParam = typeof MINER_IP !== 'undefined' ? MINER_IP : null;

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
                scales: {x: {type: 'time', time: {unit: 'hour'}}, y: {beginAtZero: true}},
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
                scales: {x: {type: 'time', time: {unit: 'hour'}}, y: {beginAtZero: true}},
                plugins: {legend: {display: false}}
            }
        });
    }
    if (!charts.tempfan) {
        charts.tempfan = new Chart(document.getElementById('chart-tempfan'), {
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

function setNoData(chart, msg) {
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
}

async function fillStatsLogFromMetrics() {
    const qs = new URLSearchParams(location.search);
    const ip = qs.get('ip') || '';
    const since = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    const params = new URLSearchParams({since, limit: '500'});
    if (ip) params.set('ip', ip);

    let rows = [];
    try {
        const res = await fetch(`/api/metrics?${params.toString()}`);
        rows = await res.json();
        if (!Array.isArray(rows)) rows = [];
    } catch (e) {
        console.warn('metrics fetch for stats log failed', e);
        rows = [];
    }

    const tbody = document.getElementById('stats-log');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!rows.length) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td colspan="3">No recent data.</td>`;
        tbody.appendChild(tr);
        return;
    }

    rows.slice(-100).forEach(r => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${r.timestamp}</td> <td>${r.ip || '—'}</td> <td>${Number(r.hashrate_ths || 0).toFixed(3)} TH/s</td>`;
        tbody.appendChild(tr);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    loadAndRender();
    fillStatsLogFromMetrics();
    setInterval(loadAndRender, POLL_INTERVAL * 1000);
});
