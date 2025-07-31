const REFRESH_INTERVAL = 30;

async function fetchMiners() {
    const res = await fetch('/api/miners');
    const {miners} = await res.json();
    const list = document.getElementById('miner-list');
    list.innerHTML = '';
    miners.forEach(ip => {
        const li = document.createElement('li');
        // Link to dashboard with IP filter
        const a = document.createElement('a');
        a.href = `/?ip=${encodeURIComponent(ip)}`;
        a.textContent = ip;
        li.appendChild(a);
        list.appendChild(li);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    fetchMiners();
    setInterval(fetchMiners, REFRESH_INTERVAL * 1000);
});