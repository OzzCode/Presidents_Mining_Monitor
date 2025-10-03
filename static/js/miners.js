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

function renderMinerRow(miner) {
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
    return tr;
}

function renderMetadataRow(miner) {
    const tr = document.createElement('tr');
    const tags = Array.isArray(miner.tags) ? miner.tags.join(', ') : (miner.tags ? JSON.stringify(miner.tags) : '—');
    const nominalThs = (typeof miner.nominal_ths === 'number' && isFinite(miner.nominal_ths)) ? miner.nominal_ths : null;
    const nominalEff = (typeof miner.nominal_efficiency_j_per_th === 'number' && isFinite(miner.nominal_efficiency_j_per_th)) ? miner.nominal_efficiency_j_per_th : null;
    const ppk = (typeof miner.power_price_usd_per_kwh === 'number' && isFinite(miner.power_price_usd_per_kwh)) ? miner.power_price_usd_per_kwh : null;

    tr.innerHTML = `
      <td>${miner.ip || ''}</td>
      <td>${miner.model || '—'}</td>
      <td>${miner.vendor || '—'}</td>
      <td>${miner.hostname || '—'}</td>
      <td>${miner.rack || '—'}</td>
      <td>${miner.row || '—'}</td>
      <td>${miner.location || '—'}</td>
      <td>${miner.room || '—'}</td>
      <td>${miner.owner || '—'}</td>
      <td>${miner.notes || '—'}</td>
      <td>${nominalThs != null ? nominalThs : '—'}</td>
      <td>${nominalEff != null ? nominalEff : '—'}</td>
      <td>${ppk != null ? ppk : '—'}</td>
      <td>${tags}</td>
    `;
    return tr;
}

async function fetchMiners() {
    const activeTbody = document.getElementById('miner-table');
    const staleTbody = document.getElementById('stale-table');
    const staleCount = document.getElementById('stale-count');
    const metadataBody = document.getElementById('metadata-body');
    if (!activeTbody) return;

    try {
        const res = await fetch('/api/miners');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const payload = await res.json();
        const miners = Array.isArray(payload) ? payload : (Array.isArray(payload?.miners) ? payload.miners : null);

        if (!Array.isArray(miners)) {
            // Keep existing content; optionally show a non-destructive inline status
            console.warn('Failed to load miners list: unexpected payload shape');
            return;
        }

        // Split into Active vs Stale (Live = status === 'Active')
        const active = miners.filter(m => (m && m.status === 'Active'));
        const stale = miners.filter(m => (m && m.status !== 'Active'));

        if (staleCount) staleCount.textContent = String(stale.length);

        // Build fragments off-DOM for atomic swap (prevents blanking during refresh)
        const activeFrag = document.createDocumentFragment();
        const staleFrag = document.createDocumentFragment();
        const metaFrag = document.createDocumentFragment();

        if (!active.length) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="6">No live miners.</td>`;
            activeFrag.appendChild(tr);
        } else {
            active.forEach(m => activeFrag.appendChild(renderMinerRow(m)));
        }

        if (staleTbody) {
            if (!stale.length) {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td colspan="6">No stale miners.</td>`;
                staleFrag.appendChild(tr);
            } else {
                stale.forEach(m => staleFrag.appendChild(renderMinerRow(m)));
            }
        }

        if (metadataBody) {
            if (!active.length) {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td colspan="14">No metadata to display.</td>`;
                metaFrag.appendChild(tr);
            } else {
                active.forEach(m => metaFrag.appendChild(renderMetadataRow(m)));
            }
        }

        // Atomically replace content so users never see a blank table
        activeTbody.replaceChildren(activeFrag);
        if (staleTbody) staleTbody.replaceChildren(staleFrag);
        if (metadataBody) metadataBody.replaceChildren(metaFrag);
    } catch (e) {
        // Preserve existing data on error to avoid blanking the UI
        console.warn('fetchMiners failed:', e);
    }
}

function attachStaleToggle() {
    const btn = document.getElementById('toggle-stale');
    const section = document.getElementById('stale-section');
    if (!btn || !section) return;
    btn.addEventListener('click', () => {
        const isHidden = section.style.display === 'none' || section.style.display === '';
        section.style.display = isHidden ? 'block' : 'none';
        btn.textContent = (isHidden ? 'Hide' : 'Show') + ` Stale Miners (` + (document.getElementById('stale-count')?.textContent || '0') + `)`;
    });
}


document.addEventListener('DOMContentLoaded', () => {
    attachStaleToggle();
    fetchMiners();
    setInterval(fetchMiners, REFRESH_INTERVAL * 1000);
});
