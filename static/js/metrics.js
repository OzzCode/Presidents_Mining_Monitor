(function () {
    const REFRESH_INTERVAL_MS = 30_000;
    let minerCache = [];
    let activeMiners = [];
    let staleMiners = [];

    function onReady(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    function $(selector) {
        return document.querySelector(selector);
    }

    function setText(id, value) {
        const el = (typeof id === 'string' && id.startsWith('#')) ? $(id) : document.getElementById(id);
        if (el) el.textContent = value;
    }

    function formatNumber(value, options = {}) {
        if (value == null || Number.isNaN(value)) {
            return '--';
        }
        const formatter = new Intl.NumberFormat(undefined, options);
        return formatter.format(value);
    }

    function humanDuration(seconds) {
        const total = Math.floor(Number(seconds) || 0);
        if (!total || total < 0) return '--';
        const days = Math.floor(total / 86400);
        const hours = Math.floor((total % 86400) / 3600);
        const minutes = Math.floor((total % 3600) / 60);
        if (days) return `${days}d ${hours}h ${minutes}m`;
        if (hours) return `${hours}h ${minutes}m`;
        return `${minutes}m`;
    }

    function freshnessBadge(miner) {
        if (!miner) return 'Unknown';
        const age = Number(miner.age_sec || 0);
        if (age <= 30) return 'Active';
        if (age <= 75) return 'Lagging';
        return 'Stale';
    }

    function updateFleetSummary(summary) {
        if (!summary) {
            setText('fleet-total-power', '-- W');
            setText('fleet-total-hashrate', '-- TH/s');
            setText('fleet-total-uptime', '--');
            setText('fleet-avg-temp', '-- °C');
            setText('fleet-avg-fan', '-- RPM');
            setText('fleet-active-count', '--');
            setText('fleet-last-update', 'Last updated: —');
            return;
        }

        const setWithUnit = (id, value, unit, options = {}) => {
            setText(id, `${formatNumber(value, options)}${unit ? ` ${unit}` : ''}`);
        };

        setWithUnit('fleet-total-power', summary.total_power, 'W', { maximumFractionDigits: 0 });
        setWithUnit('fleet-total-hashrate', summary.total_hashrate, 'TH/s', { maximumFractionDigits: 2 });
        setText('fleet-total-uptime', humanDuration(summary.total_uptime));
        setWithUnit('fleet-avg-temp', summary.avg_temp, '°C', { maximumFractionDigits: 1 });
        setWithUnit('fleet-avg-fan', summary.avg_fan_speed, 'RPM', { maximumFractionDigits: 0 });
        setText('fleet-active-count', Array.isArray(activeMiners) ? activeMiners.length : '--');
        const last = summary.last_updated ? new Date(summary.last_updated) : null;
        setText('fleet-last-update', last ? `Last updated: ${last.toLocaleString()}` : 'Last updated: —');
    }

    function populateMinerTables() {
        const activeBody = $('#active-miner-body');
        const staleBody = $('#stale-miner-body');
        if (!activeBody || !staleBody) return;

        const makeRow = (miner) => {
            const tr = document.createElement('tr');
            const model = miner.model || '—';
            const status = miner.status || freshnessBadge(miner);
            const lastSeen = miner.last_seen ? new Date(miner.last_seen).toLocaleString() : '—';
            const power = (typeof miner.est_power_w === 'number' && Number.isFinite(miner.est_power_w))
                ? formatNumber(miner.est_power_w, { maximumFractionDigits: 0 })
                : '—';
            tr.innerHTML = `
                <td>${status}</td>
                <td>${model}</td>
                <td><a href="/dashboard/?ip=${encodeURIComponent(miner.ip)}">${miner.ip}</a></td>
                <td>${lastSeen}</td>
                <td>${power}</td>
                <td class="actions">
                    <a class="btn small" href="http://${miner.ip}/" target="_blank" rel="noopener">Firmware UI</a>
                </td>
            `;
            return tr;
        };

        const renderList = (target, minersList, emptyMessage) => {
            target.replaceChildren();
            if (!minersList.length) {
                const emptyRow = document.createElement('tr');
                emptyRow.innerHTML = `<td colspan="6" class="muted">${emptyMessage}</td>`;
                target.appendChild(emptyRow);
            } else {
                minersList.forEach(miner => target.appendChild(makeRow(miner)));
            }
        };

        renderList(activeBody, activeMiners, 'No active miners detected.');
        renderList(staleBody, staleMiners, 'No stale miners detected.');
    }

    function updateFocusedMiner(ip) {
        const miner = minerCache.find(m => m.ip === ip) || null;
        if (!miner) {
            setText('focus-hashrate', '-- TH/s');
            setText('focus-power', '-- W');
            setText('focus-temp', '-- °C');
            setText('focus-fan', '-- RPM');
            setText('focus-status', '--');
            setText('focus-last-seen', '--');
            const link = $('#focus-open-ui');
            if (link) link.setAttribute('href', '#');
            return;
        }
        setText('focus-hashrate', formatNumber(miner.hashrate_ths, { maximumFractionDigits: 2 }));
        setText('focus-power', formatNumber(miner.est_power_w, { maximumFractionDigits: 0 }));
        setText('focus-temp', formatNumber(miner.avg_temp_c, { maximumFractionDigits: 1 }));
        setText('focus-fan', formatNumber(miner.avg_fan_rpm, { maximumFractionDigits: 0 }));
        setText('focus-status', miner.status || freshnessBadge(miner));
        const lastSeen = miner.last_seen ? new Date(miner.last_seen).toLocaleString() : '—';
        setText('focus-last-seen', lastSeen);
        const link = $('#focus-open-ui');
        if (link) link.setAttribute('href', `http://${miner.ip}/`);
    }

    function populateMinerSelect() {
        const select = $('#miner-select');
        if (!select) return;
        const previous = select.value;
        select.replaceChildren();

        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = activeMiners.length ? 'Choose a miner…' : 'No active miners available';
        select.appendChild(placeholder);

        activeMiners.forEach(miner => {
            const option = document.createElement('option');
            option.value = miner.ip;
            option.textContent = `${miner.ip} · ${miner.model || 'Unknown model'}`;
            select.appendChild(option);
        });

        if (previous && activeMiners.some(m => m.ip === previous)) {
            select.value = previous;
            updateFocusedMiner(previous);
        } else if (activeMiners.length) {
            select.value = activeMiners[0].ip;
            updateFocusedMiner(activeMiners[0].ip);
        } else {
            select.value = '';
            updateFocusedMiner(null);
        }
    }

    async function fetchSummary() {
        try {
            const res = await fetch('/api/summary');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const summary = await res.json();
            updateFleetSummary(summary);
        } catch (err) {
            console.warn('Failed to load fleet summary', err);
        }
    }

    async function fetchMiners() {
        try {
            const res = await fetch('/api/miners');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const payload = await res.json();
            const miners = Array.isArray(payload?.miners) ? payload.miners : [];
            minerCache = miners.map(m => ({
                ip: m.ip,
                model: m.model,
                status: m.status,
                last_seen: m.last_seen,
                est_power_w: m.est_power_w,
                hashrate_ths: m.hashrate_ths,
                avg_temp_c: m.avg_temp_c,
                avg_fan_rpm: m.avg_fan_rpm,
                age_sec: m.age_sec,
            }));
            activeMiners = minerCache.filter(m => (m.status || freshnessBadge(m)) === 'Active');
            staleMiners = minerCache.filter(m => (m.status || freshnessBadge(m)) !== 'Active');
            populateMinerSelect();
            populateMinerTables();
        } catch (err) {
            console.warn('Failed to load miner list', err);
        }
    }

    function bindEvents() {
        const select = $('#miner-select');
        if (select) {
            select.addEventListener('change', (evt) => {
                updateFocusedMiner(evt.target.value || null);
            });
        }

        const showStaleToggle = $('#show-stale');
        const staleWrapper = document.getElementById('stale-wrapper');
        if (showStaleToggle && staleWrapper) {
            showStaleToggle.addEventListener('change', () => {
                staleWrapper.hidden = !showStaleToggle.checked;
            });
        }
    }

    function startPolling() {
        fetchSummary();
        fetchMiners();
        setInterval(fetchSummary, REFRESH_INTERVAL_MS);
        setInterval(fetchMiners, REFRESH_INTERVAL_MS);
    }

    onReady(() => {
        bindEvents();
        startPolling();
    });
})();
