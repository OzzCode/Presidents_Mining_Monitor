const POLL_INTERVAL = 30;
const baseUrl = MINER_IP ? `/api/summary?ip=${encodeURIComponent(MINER_IP)}` : '/api/summary';

async function fetchSummary() {
    const r = await fetch(baseUrl), d = await r.json();
    document.getElementById('total-power').textContent = `${d.total_power} W`;
    document.getElementById('total-hashrate').textContent = `${d.total_hashrate} TH/s`;
    document.getElementById('total-uptime').textContent = `${d.total_uptime} s`;
    document.getElementById('avg-temp').textContent = `${d.avg_temp} °C`;
    document.getElementById('avg-fan-speed').textContent = `${d.avg_fan_speed} RPM`;
    document.getElementById('total-workers').textContent = d.total_workers;
    const tb = document.getElementById('stats-log');
    tb.innerHTML = '';
    d.log.forEach(e => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${e.timestamp}</td><td>${e.ip}</td><td>${e.hash}</td>`;
        tb.appendChild(tr);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    fetchSummary();
    setInterval(fetchSummary, POLL_INTERVAL * 1e3);
});