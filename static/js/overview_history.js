// Render 3 small hashrate charts on the Overview tab: 10m, 1h, 1d
// Requires Chart.js and a global MINER_IP (can be null for all miners)

const OVERVIEW_HISTORY_REFRESH_MS = 30000; // refresh every 60s
const INTERVALS = [
    {id: 'chart-10m', label: 'Hashrate (TH/s)', seconds: 600, limit: 200},
    {id: 'chart-1h', label: 'Hashrate (TH/s)', seconds: 3600, limit: 1000},
    {id: 'chart-1d', label: 'Hashrate (TH/s)', seconds: 86400, limit: 3000},
];

const overviewCharts = {};

function buildSinceISO(secondsAgo) {
    return new Date(Date.now() - secondsAgo * 1000).toISOString();
}

async function fetchMetrics(secondsAgo, limit) {
    let url = `/api/metrics?limit=${limit}`;
    if (typeof MINER_IP !== 'undefined' && MINER_IP) url += `&ip=${encodeURIComponent(MINER_IP)}`;
    url += `&since=${encodeURIComponent(buildSinceISO(secondsAgo))}`;
    const res = await fetch(url);
    return res.json();
}

function ensureChart(canvasId, label) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;
    if (overviewCharts[canvasId]) return overviewCharts[canvasId];
    const ctx = canvas.getContext('2d');
    overviewCharts[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {labels: [], datasets: [{label, data: [], tension: 0.25}]},
        options: {
            plugins: {legend: {display: false}},
            elements: {point: {radius: 0}},
            scales: {
                x: {type: 'time', time: {parser: 'ISO'}, ticks: {maxTicksLimit: 5}},
                y: {beginAtZero: false}
            }
        }
    });
    return overviewCharts[canvasId];
}

async function updateOverviewHistory() {
    await Promise.all(INTERVALS.map(async ({id, label, seconds, limit}) => {
        const chart = ensureChart(id, label);
        if (!chart) return;
        const data = await fetchMetrics(seconds, limit);
        chart.data.labels = data.map(d => d.timestamp);
        chart.data.datasets[0].data = data.map(d => d.hashrate_ths);
        chart.update();
    }));
}

window.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('chart-10m')) {
        updateOverviewHistory();
        setInterval(updateOverviewHistory, OVERVIEW_HISTORY_REFRESH_MS);
    }
});