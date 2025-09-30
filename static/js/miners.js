const REFRESH_INTERVAL = 15;

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

    try {
        console.log("Fetching miners from /api/miners...");
        const res = await fetch('/api/miners');
        console.log("Response status:", res.status);
        if (!res.ok) {
            console.error("Error fetching miners:", res.status, res.statusText);
            throw new Error(`HTTP ${res.status}`);
        }
        const payload = await res.json();
        console.log("Payload:", payload);

        const miners = Array.isArray(payload)
            ? payload
            : Array.isArray(payload?.miners) ? payload.miners : null;

        if (!Array.isArray(miners)) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="6">Failed to load miners list.</td>`;
            tbody.appendChild(tr);
            console.error("Unexpected /api/miners payload:", payload);
            return;
        }

        if (!miners.length) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="6">No miners found.</td>`;
            tbody.appendChild(tr);
            return;
        }

        miners.forEach(miner => {
            createMinerRow(tbody, miner);
        });
    } catch (e) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td colspan="6">Error loading miners.</td>`;
        tbody.appendChild(tr);
        console.warn('fetchMiners failed:', e);
    }
}

function createMinerRow(tbody, miner) {
    const tr = document.createElement('tr');
    if (miner.is_stale) tr.classList.add('stale');
    const ip = miner.ip || '';
    const model = miner.model && String(miner.model).trim() ? miner.model : '—';
    const status = miner.status || '—';
    const lastSeen = fmtLastSeen(miner.last_seen);
    const power = (typeof miner.est_power_w === 'number' && isFinite(miner.est_power_w))
        ? miner.est_power_w.toLocaleString(undefined, {maximumFractionDigits: 1})
        : '—';

    tr.innerHTML = `
      <td>${freshnessDot(miner.age_sec)} ${status}</td>
      <td>${model}</td>
      <td><a href="/dashboard/?ip=${encodeURIComponent(ip)}">${ip}</a></td>
      <td>${lastSeen}</td>
      <td>${power}</td>
      <td><a href="http://${ip}/" target="_blank" rel="noopener">Web UI</a></td>
    `;
    tbody.appendChild(tr);
}


document.addEventListener('DOMContentLoaded', () => {
    fetchMiners();
    setInterval(fetchMiners, REFRESH_INTERVAL * 1000);
});
