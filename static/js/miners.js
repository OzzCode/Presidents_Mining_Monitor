const REFRESH_INTERVAL = 30;

async function fetchMiners() {
    const r = await fetch('/api/miners'),
        j = await r.json(),
        tb = document.getElementById('miner-table');
    tb.innerHTML = '';
    j.miners.forEach(m => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${m.model}</td><td><a href="/dashboard/?ip=${encodeURIComponent(m.ip)}">${m.ip}</a></td><td>${m.status}</td>`;
        tb.appendChild(tr);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    fetchMiners();
    setInterval(fetchMiners, REFRESH_INTERVAL * 1e3);
});