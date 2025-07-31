// Chart.js line chart for historical data
let historyChart;
const loadBtn = document.getElementById('load-history');
const sinceEl = document.getElementById('since-input');

document.addEventListener('DOMContentLoaded', () => {
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
    loadBtn.addEventListener('click', loadHistory);
});

async function loadHistory() {
    let url = `/api/metrics?limit=500`;
    if (MINER_IP) url += `&ip=${MINER_IP}`;
    if (sinceEl.value) url += `&since=${new Date(sinceEl.value).toISOString()}`;
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
    // Simple alert example
    data.forEach(d => d.avg_temp_c > 80 && console.warn(`High temp ${d.avg_temp_c} at ${d.timestamp}`));
}