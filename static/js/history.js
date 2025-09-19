// Auto-refresh interval (ms)
const HISTORY_INTERVAL_MS = 15000;

let historyChart;
let historyTimer = null;

const loadBtn = document.getElementById('load-history');
const sinceEl = document.getElementById('since-input');
const autoEl = document.getElementById('auto-refresh-history');
const rangeEl = document.getElementById('quick-range');

function startHistoryAuto() {
    if (!historyTimer) historyTimer = setInterval(loadHistory, HISTORY_INTERVAL_MS);
}

function stopHistoryAuto() {
    if (historyTimer) {
        clearInterval(historyTimer);
        historyTimer = null;
    }
}

function setSince(secondsAgo) {
    const d = new Date(Date.now() - secondsAgo * 1000);
    const pad = n => String(n).padStart(2, '0');
    sinceEl.value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// Initialize chart
window.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('history-chart').getContext('2d');
    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [], datasets: [
                {label: 'Hashrate (TH/s)', data: [], tension: 0.1},
                {label: 'Temp (°C)', data: [], tension: 0.1},
                {label: 'Power (W)', data: [], tension: 0.1}
            ]
        },
        options: {scales: {x: {type: 'time', time: {parser: 'ISO'}}}}
    });

    loadBtn?.addEventListener('click', loadHistory);
    autoEl?.addEventListener('change', (e) => {
        if (e.target.checked) {
            if (!sinceEl.value) setSince(3600); // default to last 1h
            loadHistory();
            startHistoryAuto();
        } else {
            stopHistoryAuto();
        }
    });
    rangeEl?.addEventListener('change', () => {
        if (rangeEl.value) {
            setSince(parseInt(rangeEl.value, 10));
            loadHistory();
        }
    });
});

// Stop auto-refresh when leaving the History tab; resume if enabled when entering
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        if (tab.dataset.tab === 'history') {
            if (autoEl?.checked) {
                if (!sinceEl.value) setSince(3600);
                loadHistory();
                startHistoryAuto();
            }
        } else {
            stopHistoryAuto();
        }
    });
});

async function loadHistory() {
    let url = '/api/metrics?limit=500';
    if (typeof MINER_IP !== 'undefined' && MINER_IP) url += `&ip=${encodeURIComponent(MINER_IP)}`;
    if (sinceEl.value) url += `&since=${encodeURIComponent(new Date(sinceEl.value).toISOString())}`;

    const res = await fetch(url);
    const data = await res.json();

    const times = data.map(d => d.timestamp);
    const hashes = data.map(d => d.hashrate_ths);
    const temps = data.map(d => d.avg_temp_c);
    const powers = data.map(d => d.power_w);

    historyChart.data.labels = times;
    historyChart.data.datasets[0].data = hashes;
    historyChart.data.datasets[1].data = temps;
    historyChart.data.datasets[2].data = powers;
    historyChart.update();
}