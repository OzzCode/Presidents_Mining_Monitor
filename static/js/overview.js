// Overview charts — farm-wide
const OV_REFRESH = 30; // seconds

let ovCharts = {};

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
    // Bucket an ISO string ts to nearest N-minute boundary
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
    }
}

async function loadAggregateSeries() {
    // last 24h, all miners (no ip filter)
    const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    const url = `/api/metrics?since=${encodeURIComponent(since)}&limit=3000`;

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

    // Aggregate by 5-minute bins across all miners
    const bins = new Map(); // key: binned ISO -> {hash,power,temp,fan,count}
    rows.forEach(r => {
        const key = binTs(r.timestamp, 5);
        if (!key) return;
        const obj = bins.get(key) || {hash: 0, power: 0, temp: 0, fan: 0, count: 0, temp_count: 0, fan_count: 0};
        obj.hash += Number(r.hashrate_ths || 0);
        obj.power += Number(r.power_w || 0);
        // temp/fan are averages per bin — sum and track counts where non-zero
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
    const hash = labels.map(k => bins.get(k).hash);                 // sum TH/s across miners
    const power = labels.map(k => bins.get(k).power);               // sum W across miners
    const temp = labels.map(k => {
        const b = bins.get(k);
        return b.temp_count ? b.temp / b.temp_count : 0;              // avg temp
    });
    const fan = labels.map(k => {
        const b = bins.get(k);
        return b.fan_count ? b.fan / b.fan_count : 0;                 // avg fan
    });

    // Update charts
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

async function initOverview() {
    ensureOvCharts();
    await loadSummaryKPIs();
    await loadAggregateSeries();
}

document.addEventListener('DOMContentLoaded', () => {
    initOverview();
    setInterval(() => {
        loadSummaryKPIs();
        loadAggregateSeries();
    }, OV_REFRESH * 1000);
});
