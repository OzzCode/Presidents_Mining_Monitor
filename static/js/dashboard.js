// === Dashboard: supports both farm-wide and single-miner modes ===
const POLL_INTERVAL = 30;

const qs = new URLSearchParams(location.search);
const QS_IP = qs.get('ip'); // if set -> single-miner mode

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

// ----- Cards -----
async function fillCards() {
    const url = QS_IP ? `/api/summary?ip=${encodeURIComponent(QS_IP)}` : '/api/summary';
    try {
        const res = await fetch(url);
        const s = await res.json();

        setText('total-power', `${num(s.total_power, 1)} W`);
        setText('total-hashrate', `${num(s.total_hashrate, 3)} TH/s`);
        setText('total-uptime', `${num(s.total_uptime)} s`);
        setText('avg-temp', `${num(s.avg_temp, 1)} °C`);
        setText('avg-fan-speed', `${num(s.avg_fan_speed)} RPM`);
        setText('total-workers', `${num(s.total_workers)}`);

        const stamp = $('#last-update');
        if (stamp) stamp.textContent = `Last update: ${new Date().toLocaleString()}`;
        const srv = $('#server-update');
        if (srv && s.last_updated) srv.textContent = `Server time: ${new Date(s.last_updated).toLocaleString()}`;

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
    if (!charts.hash) {
        charts.hash = new Chart($('#chart-hashrate'), {
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
        charts.power = new Chart($('#chart-power'), {
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
        charts.tempfan = new Chart($('#chart-tempfan'), {
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
    const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    const params = new URLSearchParams({since, limit: '3000'});
    if (QS_IP) {
        // single-miner
        params.set('ip', QS_IP);
    } else {
        // farm aggregates = active miners only
        params.set('active_only', 'true');
        params.set('fresh_within', '30');
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
        Object.values(charts).forEach(c => {
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
            if (t > 0) {
                o.temp += t;
                o.tc++;
            }
            const f = Number(r.avg_fan_rpm || 0);
            if (f > 0) {
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

// ----- Table -----
async function fillTable() {
    const tbody = $('#stats-log');
    if (!tbody) return;

    if (QS_IP) {
        // single-miner: show recent samples (last 2h)
        const since = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
        const params = new URLSearchParams({since, limit: '500', ip: QS_IP});
        let rows = [];
        try {
            const res = await fetch(`/api/metrics?${params.toString()}`);
            rows = await res.json();
            if (!Array.isArray(rows)) rows = [];
        } catch (e) {
            rows = [];
        }

        tbody.innerHTML = '';
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
        const params = new URLSearchParams({active_only: 'true', fresh_within: '30'});
        let rows = [];
        try {
            const res = await fetch(`/api/miners/current?${params.toString()}`);
            rows = await res.json();
            if (!Array.isArray(rows)) rows = [];
        } catch (e) {
            rows = [];
        }

        tbody.innerHTML = '';
        if (!rows.length) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="6">No active miners in the last 30 minutes.</td>`;
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
        <td>${fmt0(r.avg_fan_rpm)}</td>
      `;
            tbody.appendChild(tr);
        });
    }
}

// ----- Boot -----
document.addEventListener('DOMContentLoaded', () => {
    fillCards();
    fillCharts();
    fillTable();

    setInterval(() => {
        fillCards();
        fillCharts();
        fillTable();
    }, POLL_INTERVAL * 1000);
});