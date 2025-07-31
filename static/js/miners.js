const REFRESH_INTERVAL = 30;

/**
 * Fetch the list of discovered miners with details and render them in a table.
 */
async function fetchMiners() {
    try {
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
    } catch (err) {
        console.error('Error fetching miners:', err);
    }
}

// Initialize and set periodic refresh
document.addEventListener('DOMContentLoaded', () => {
    fetchMiners();
    setInterval(fetchMiners, REFRESH_INTERVAL * 1000);
});