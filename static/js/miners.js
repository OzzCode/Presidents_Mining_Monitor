const REFRESH_INTERVAL = 30;

async function fetchMiners() {
    const res = await fetch('/api/miners');
    const {miners} = await res.json();
    const tbody = document.getElementById('miner-table');
    tbody.innerHTML = '';
    miners.forEach(miner => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
      <td>${miner.model}</td>
      <td><a href="/dashboard/?ip=${encodeURIComponent(miner.ip)}">${miner.ip}</a></td>
      <td>${miner.status}</td>
    `;
        tbody.appendChild(tr);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    fetchMiners();
    setInterval(fetchMiners, REFRESH_INTERVAL * 1000);
});