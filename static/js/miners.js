const REFRESH_INTERVAL = 30;

function freshnessDot(ageSec) {
    if (ageSec == null) return '<span class="dot dot-gray" title="No data"></span>';
    if (ageSec <= 2 * REFRESH_INTERVAL) return '<span class="dot dot-yellow" title="Fresh"></span>';
    if (ageSec <= 5 * REFRESH_INTERVAL) return '<span class="dot dot-red" title="Lagging"></span>';
    return '<span class="dot dot-green" title="Stale"></span>';
}

function fmtLastSeen(lastSeenIso) {
    if (!lastSeenIso) return '—';
    try {
        return new Date(lastSeenIso).toLocaleString();
    } catch {
        return lastSeenIso;
    }
}

async function fetchMiners() {
    const res = await fetch('/api/miners');
    const payload = await res.json();
    const {miners} = payload;
    const tbody = document.getElementById('miner-table');
    tbody.innerHTML = '';
    miners.forEach(miner => {
        const tr = document.createElement('tr');
        if (miner.is_stale) tr.classList.add('stale');
        tr.innerHTML = `
      <td>${freshnessDot(miner.age_sec)} ${miner.status}</td>
      <td>${miner.model}</td>
      <td><a href="/dashboard/?ip=${encodeURIComponent(miner.ip)}">${miner.ip}</a></td>
      <td>${fmtLastSeen(miner.last_seen)}</td>
      <td><a href="http://${miner.ip}/" target="_blank" rel="noopener">Web UI</a></td>
    `;
        tbody.appendChild(tr);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    fetchMiners();
    setInterval(fetchMiners, REFRESH_INTERVAL * 1000);
});
