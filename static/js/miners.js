const REFRESH_INTERVAL = 30;

function freshnessDot(ageSec) {
    if (ageSec == null) return '<span class="dot dot-gray" title="No data"></span>';
    if (ageSec <= 2 * REFRESH_INTERVAL) return '<span class="dot dot-green" title="Fresh"></span>';
    if (ageSec <= 5 * REFRESH_INTERVAL) return '<span class="dot dot-yellow" title="Lagging"></span>';
    return '<span class="dot dot-red" title="Stale"></span>';
}

function fmtLastSeen(lastSeenIso) {
    if (!lastSeenIso) return '—';
    try {
        const d = new Date(lastSeenIso);
        return Number.isNaN(d.getTime()) ? String(lastSeenIso) : d.toLocaleString();
    } catch {
        return String(lastSeenIso);
    }
}

async function fetchMiners() {
    const tbody = document.getElementById('miner-table');
    if (!tbody) return;
    tbody.innerHTML = '';
// ... existing code ...
    try {
        const res = await fetch('/api/miners');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const payload = await res.json();

        // Support both formats: array or { miners: [...] }
        const miners = Array.isArray(payload) ? payload
            : (Array.isArray(payload?.miners) ? payload.miners : null);

        if (!Array.isArray(miners)) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="5">Failed to load miners list.</td>`;
            tbody.appendChild(tr);
            console.error("Unexpected /api/miners payload:", payload);
            return;
        }

        if (!miners.length) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="5">No miners found.</td>`;
            tbody.appendChild(tr);
            return;
        }

        miners.forEach(miner => {
            const tr = document.createElement('tr');
            if (miner.is_stale) tr.classList.add('stale');
            const ip = miner.ip || '';
            const model = miner.model && String(miner.model).trim() ? miner.model : '—';
            const status = miner.status || '—';
            const lastSeen = fmtLastSeen(miner.last_seen);

            tr.innerHTML = `
      <td>${freshnessDot(miner.age_sec)} ${status}</td>
      <td>${model}</td>
      <td><a href="/dashboard/?ip=${encodeURIComponent(ip)}">${ip}</a></td>
      <td>${lastSeen}</td>
      <td><a href="http://${ip}/" target="_blank" rel="noopener">Web UI</a></td>
    `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td colspan="5">Error loading miners.</td>`;
        tbody.appendChild(tr);
        console.warn('fetchMiners failed:', e);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchMiners();
    setInterval(fetchMiners, REFRESH_INTERVAL * 1000);
});
