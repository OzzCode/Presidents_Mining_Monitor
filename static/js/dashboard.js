const POLL_INTERVAL = 30;
const baseUrl = MINER_IP ? `/api/summary?ip=${encodeURIComponent(MINER_IP)}` : '/api/summary';

async function fetchSummary() {
    const res = await fetch(baseUrl);
    const data = await res.json();
    document.getElementById('total-power').textContent = `${data.total_power} W`;
    document.getElementById('total-hashrate').textContent = `${data.total_hashrate} TH/s`;
    document.getElementById('total-uptime').textContent = `${data.total_uptime} s`;
    document.getElementById('avg-temp').textContent = `${data.avg_temp} °C`;
    document.getElementById('avg-fan-speed').textContent = `${data.avg_fan_speed} RPM`;
    document.getElementById('total-workers').textContent = data.total_workers;
    const tbody = document.getElementById('stats-log');
    tbody.innerHTML = '';
    data.log.forEach(e => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${e.timestamp}</td><td>${e.ip}</td><td>${e.hash}</td>`;
        tbody.appendChild(tr);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    fetchSummary();
    setInterval(fetchSummary, POLL_INTERVAL * 1000);
});