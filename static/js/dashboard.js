const POLL_INTERVAL = 30; // seconds

async function fetchSummary() {
    try {
        const res = await fetch('/api/summary');
        const data = await res.json();

        document.getElementById('total-power').textContent = `${data.total_power} W`;
        document.getElementById('total-hashrate').textContent = `${data.total_hashrate} TH/s`;
        document.getElementById('total-uptime').textContent = `${data.total_uptime} s`;
        document.getElementById('avg-temp').textContent = `${data.avg_temp} °C`;
        document.getElementById('avg-fan-speed').textContent = `${data.avg_fan_speed} RPM`;
        document.getElementById('total-workers').textContent = data.total_workers;

        const tbody = document.getElementById('stats-log');
        tbody.innerHTML = '';
        data.log.forEach(entry => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${entry.timestamp}</td>
                <td>${entry.stat}</td>
                <td>${entry.value}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Error fetching summary:', err);
    }
}

window.onload = () => {
    fetchSummary();
    setInterval(fetchSummary, POLL_INTERVAL * 1000);
};


```javascript
// Placeholder for dashboard JS: fetch metrics and update DOM elements
// e.g. use fetch('/api/summary') to populate the fields and log```
