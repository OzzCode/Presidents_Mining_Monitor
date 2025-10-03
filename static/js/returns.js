const REFRESH_MS = 60000; // 60s
let abortCtrl = null;

function fmt(n, digits = 2) {
    if (!isFinite(n)) return '—';
    return Number(n).toLocaleString(undefined, {maximumFractionDigits: digits});
}

function savePrefs(rate, freshWithin) {
    try {
        localStorage.setItem('ret_rate', String(rate));
        localStorage.setItem('ret_fresh_within', String(freshWithin));
    } catch {
    }
}

function loadPrefs() {
    let rate = 0.1;
    let freshWithin = 30;
    try {
        const r = parseFloat(localStorage.getItem('ret_rate'));
        if (isFinite(r) && r >= 0) rate = r;
        const fw = parseInt(localStorage.getItem('ret_fresh_within'), 10);
        if (Number.isFinite(fw) && fw > 0) freshWithin = fw;
    } catch {
    }
    const rateEl = document.getElementById('rate');
    const fwEl = document.getElementById('fresh-within');
    if (rateEl) rateEl.value = String(rate);
    if (fwEl) fwEl.value = String(freshWithin);
}

async function fetchBTCPrice() {
    // Use server proxy for resiliency
    const res = await fetch('/api/btc/history');
    const payload = await res.json();
    if (!payload || !payload.ok) throw new Error('No BTC price');
    const last = Number(payload.last);
    const updated = payload.updated || '';
    const priceEl = document.getElementById('btc-price-simple');
    if (priceEl && isFinite(last)) priceEl.textContent = `$${fmt(last, 0)}`;
    return {price: last, updated};
}

async function fetchDifficulty() {
    // Simple public API for network difficulty
    const r = await fetch('https://blockchain.info/q/getdifficulty', {cache: 'no-store'});
    if (!r.ok) throw new Error(`Difficulty HTTP ${r.status}`);
    const t = await r.text();
    const diff = parseFloat(t);
    if (!isFinite(diff)) throw new Error('Bad difficulty');
    return diff;
}

function btcPerTHPerDay(difficulty, rewardBtc = 3.125) {
    // BTC per TH per day = (1e12 * 86400 / (diff * 2^32)) * reward
    const two32 = 4294967296; // 2^32
    return (1e12 * 86400 / (difficulty * two32)) * rewardBtc;
}

async function fetchMinersCurrent(freshWithin) {
    const params = new URLSearchParams({active_only: 'true', fresh_within: String(freshWithin)});
    const res = await fetch(`/api/miners/current?${params.toString()}`);
    if (!res.ok) throw new Error(`Miners HTTP ${res.status}`);
    const rows = await res.json();
    return Array.isArray(rows) ? rows : [];
}

function renderTable(miners, rate, usdPerThDay, btcPrice) {
    const tbody = document.getElementById('returns-body');
    if (!tbody) return {totalHash: 0, totalPower: 0, totalCost: 0, totalRev: 0};

    const frag = document.createDocumentFragment();
    let totalHash = 0;
    let totalPower = 0;
    let totalCost = 0;
    let totalRev = 0;

    miners.forEach(m => {
        const hr = Number(m.hashrate_ths || 0);
        const pw = Number(m.power_w || 0);
        totalHash += hr;
        totalPower += pw;

        const revUsd = hr * usdPerThDay; // rev per TH/day in USD
        const costUsd = (pw / 1000) * 24 * rate;
        const profitUsd = revUsd - costUsd;

        totalRev += revUsd;
        totalCost += costUsd;

        const tr = document.createElement('tr');
        tr.innerHTML = `
      <td><a href="/dashboard/?ip=${encodeURIComponent(m.ip || '')}">${m.ip || ''}</a></td>
      <td>${m.model || '—'}</td>
      <td>${fmt(hr, 3)}</td>
      <td>${fmt(pw, 0)}</td>
      <td>$${fmt(revUsd, 2)}</td>
      <td>$${fmt(costUsd, 2)}</td>
      <td style="font-weight:600; color:${profitUsd >= 0 ? 'var(--good)' : 'var(--bad)'};">$${fmt(profitUsd, 2)}</td>
    `;
        frag.appendChild(tr);
    });

    tbody.replaceChildren(frag);
    return {totalHash, totalPower, totalCost, totalRev};
}

async function refreshReturns() {
    const status = document.getElementById('status');
    const rate = parseFloat(document.getElementById('rate').value || '0.1');
    const freshWithin = parseInt(document.getElementById('fresh-within').value || '30', 10);
    savePrefs(rate, freshWithin);

    try {
        if (status) status.textContent = 'Loading…';

        // Fetch in parallel
        const [btc, diff, miners] = await Promise.all([
            fetchBTCPrice(),
            fetchDifficulty().catch(() => null),
            fetchMinersCurrent(freshWithin)
        ]);

        const price = Number(btc.price) || 0;
        let btcThDay = null;
        if (diff) {
            try {
                btcThDay = btcPerTHPerDay(diff, 3.125);
            } catch {
            }
        }

        const btcPerThDayEl = document.getElementById('btc-per-th-day');
        if (btcThDay != null) {
            btcPerThDayEl.textContent = `${fmt(btcThDay, 8)} BTC`;
        } else {
            btcPerThDayEl.textContent = '—';
        }

        // USD revenue per TH/day
        const usdPerThDay = (btcThDay != null) ? (btcThDay * price) : 0;

        const {totalHash, totalPower, totalCost, totalRev} = renderTable(miners, rate, usdPerThDay, price);

        // Update cards
        document.getElementById('total-hash').textContent = `${fmt(totalHash, 3)} TH/s`;
        document.getElementById('total-power').textContent = `${fmt(totalPower, 0)} W`;
        document.getElementById('daily-revenue').textContent = `$${fmt(totalRev, 2)}`;
        document.getElementById('daily-cost').textContent = `$${fmt(totalCost, 2)}`;
        const profit = totalRev - totalCost;
        document.getElementById('daily-profit').textContent = `$${fmt(profit, 2)}`;

        if (status) status.textContent = `Updated ${new Date().toLocaleTimeString()}`;
    } catch (e) {
        console.warn('refreshReturns failed', e);
        if (status) status.textContent = 'Failed to load data';
    }
}

function attachHandlers() {
    document.getElementById('apply').addEventListener('click', refreshReturns);
}

document.addEventListener('DOMContentLoaded', () => {
    loadPrefs();
    attachHandlers();
    refreshReturns();
    setInterval(refreshReturns, REFRESH_MS);
});