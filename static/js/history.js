let historyChart;
const loadBtn = document.getElementById('load-history'),
    sinceEl = document.getElementById('since-input');
document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('history-chart').getContext('2d');
    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{label: 'Hashrate (TH/s)', data: [], tension: 0.1}, {
                label: 'Temp (°C)',
                data: [],
                tension: 0.1
            }, {label: 'Power (W)', data: [], tension: 0.1}]
        },
        options: {scales: {x: {type: 'time', time: {parser: 'ISO'}}}}
    });
    loadBtn.addEventListener('click', loadHistory);
});

async function loadHistory() {
    console.log('Loading history…', MINER_IP, sinceEl.value);
    let url = `/api/metrics?limit=500`;
    if (MINER_IP) url += `&ip=${MINER_IP}`;
    if (sinceEl.value) url += `&since=${new Date(sinceEl.value).toISOString()}`;
    const r = await fetch(url), d = await r.json();
    historyChart.data.labels = d.map(x => x.timestamp);
    historyChart.data.datasets[0].data = d.map(x => x.hashrate_ths);
    historyChart.data.datasets[1].data = d.map(x => x.avg_temp_c);
    historyChart.data.datasets[2].data = d.map(x => x.power_w);
    historyChart.update();
    d.forEach(x => x.avg_temp_c > 80 && console.warn(`High temp ${x.avg_temp_c}°C at ${x.timestamp}`));
}