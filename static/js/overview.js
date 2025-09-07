// Overview charts — farm-wide
const OV_REFRESH = 30; // seconds

let ovCharts = {};

function getFreshWithin() {
    const sel = document.getElementById('fresh-within');
    if (!sel) return 30;
    const val = parseInt(sel.value, 10);
    return Number.isFinite(val) ? val : 30;
}

function getActiveOnly() {
    const cb = document.getElementById('active-only');
    return cb ? !!cb.checked : true;
}

function saveFreshPrefs() {
    try {
        localStorage.setItem('ov_fresh_within', String(getFreshWithin()));
        localStorage.setItem('ov_active_only', getActiveOnly() ? '1' : '0');
    } catch (e) {
        // Log error but don't break the app
        console.warn('Failed to save preferences to localStorage:', e);
    }
}

function loadFreshPrefs() {
    try {
        const fw = localStorage.getItem('ov_fresh_within');
        const ao = localStorage.getItem('ov_active_only');
        if (fw && document.getElementById('fresh-within')) {
            document.getElementById('fresh-within').value = fw;
        }
        if (ao && document.getElementById('active-only')) {
            document.getElementById('active-only').checked = ao === '1';
        }
    } catch (e) {
        console.warn('Failed to load preferences from localStorage:', e);
    }
}

function updateActiveWindowBadge() {
    const el = document.getElementById('active-window-badge');
    if (!el) return;
    const mins = getFreshWithin();
    el.textContent = `Active window: last ${mins} min`;
}

function ensureOvCharts() {
    // Check if charts already exist before creating new ones
    if (!ovCharts.hash) {
        const hashCtx = document.getElementById('overview-hash');
        if (hashCtx) {
            ovCharts.hash = new Chart(hashCtx, {
                type: 'line',
                data: {labels: [], datasets: [{label: 'TH/s', data: [], tension: 0.2, fill: false}]},
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {x: {type: 'time', time: {unit: 'hour'}}, y: {beginAtZero: true}},
                    plugins: {legend: {display: false}}
                }
            });
        }
    }
    if (!ovCharts.power) {
        const powerCtx = document.getElementById('overview-power');
        if (powerCtx) {
            ovCharts.power = new Chart(powerCtx, {
                type: 'line',
                data: {labels: [], datasets: [{label: 'W', data: [], tension: 0.2, fill: false}]},
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {x: {type: 'time', time: {unit: 'hour'}}, y: {beginAtZero: true}},
                    plugins: {legend: {display: false}}
                }
            });
        }
    }
    if (!ovCharts.tempfan) {
        const tempfanCtx = document.getElementById('overview-tempfan');
        if (tempfanCtx) {
            ovCharts.tempfan = new Chart(tempfanCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {label: 'Temp (°C)', data: [], yAxisID: 'y', tension: 0.2, fill: false},
                        {label: 'Fan RPM', data: [], yAxisID: 'y', tension: 0.2, fill: false}
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    scales: {
                        x: {type: 'time', time: {unit: 'hour'}},
                        y: {beginAtZero: true}
                    },
                    plugins: {legend: {display: false}}
                }
            });
        }
    }
}

function fmt(n, d = 3) {
    const v = Number(n);
    return Number.isFinite(v) ? v.toFixed(d) : '0';
}

function fmt0(n) {
    const v = Number(n);
    return Number.isFinite(v) ? Math.round(v).toString() : '0';
}

async function loadSummaryKPIs() {
    try {
        const windowMin = Math.max(getFreshWithin(), 30);
        const freshWithin = getFreshWithin();
        const activeOnly = getActiveOnly();

        const params = new URLSearchParams({
            window_min: String(windowMin),
            active_only: activeOnly ? 'true' : 'false',
            fresh_within: String(freshWithin),
        });

        const response = await fetch(`/api/summary?${params.toString()}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();

        // Update KPI values with proper validation
        const elHash = document.getElementById('kpi-hashrate');
        if (elHash) elHash.textContent = fmt(data.hashrate_ths);
        const elPower = document.getElementById('kpi-power');
        if (elPower) elPower.textContent = fmt0(data.power_w);
        const elTemp = document.getElementById('kpi-temp');
        if (elTemp) elTemp.textContent = fmt(data.avg_temp_c, 1);

    } catch (error) {
        console.warn('Failed to load summary KPIs:', error);
        // Set default values or show an error message
        const elHash = document.getElementById('kpi-hashrate');
        if (elHash) elHash.textContent = '0';
        const elPower = document.getElementById('kpi-power');
        if (elPower) elPower.textContent = '0';
        const elTemp = document.getElementById('kpi-temp');
        if (elTemp) elTemp.textContent = '0';
    }
}

async function loadAggregateSeries() {
    try {
        const windowMin = Math.max(getFreshWithin(), 30);
        const freshWithin = getFreshWithin();
        const activeOnly = getActiveOnly();

        // Validate that we have chart elements before proceeding
        if (!ovCharts.hash || !ovCharts.power || !ovCharts.tempfan) {
            ensureOvCharts(); // Re-initialize charts if needed
        }

        const params = new URLSearchParams({
            window_min: String(windowMin),
            active_only: activeOnly ? 'true' : 'false',
            fresh_within: String(freshWithin),
        });

        const response = await fetch(`/api/aggregate?${params.toString()}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Validate that we have data before updating charts
        if (data && Array.isArray(data.timestamps)) {
            // Update hash chart
            if (ovCharts.hash) {
                ovCharts.hash.data.labels = data.timestamps;
                ovCharts.hash.data.datasets[0].data = data.hashrate_ths || [];
                ovCharts.hash.update();
            }

            // Update power chart
            if (ovCharts.power) {
                ovCharts.power.data.labels = data.timestamps;
                ovCharts.power.data.datasets[0].data = data.power_w || [];
                ovCharts.power.update();
            }

            // Update temp/fan chart
            if (ovCharts.tempfan) {
                ovCharts.tempfan.data.labels = data.timestamps;
                if (ovCharts.tempfan.data.datasets.length >= 2) {
                    ovCharts.tempfan.data.datasets[0].data = data.avg_temp_c || [];
                    ovCharts.tempfan.data.datasets[1].data = data.avg_fan_rpm || [];
                }
                ovCharts.tempfan.update();
            }
        }
    } catch (error) {
        console.warn('Failed to load aggregate series:', error);
        // Clear charts if there's an error
        if (ovCharts.hash) {
            ovCharts.hash.data.labels = [];
            ovCharts.hash.data.datasets[0].data = [];
            ovCharts.hash.update();
        }
        if (ovCharts.power) {
            ovCharts.power.data.labels = [];
            ovCharts.power.data.datasets[0].data = [];
            ovCharts.power.update();
        }
        if (ovCharts.tempfan) {
            ovCharts.tempfan.data.labels = [];
            if (ovCharts.tempfan.data.datasets.length >= 2) {
                ovCharts.tempfan.data.datasets[0].data = [];
                ovCharts.tempfan.data.datasets[1].data = [];
            }
            ovCharts.tempfan.update();
        }
    }
}

async function fillMinersSummaryTable() {
    try {
        const tbody = document.getElementById('stats-log');
        if (!tbody) return;

        const windowMin = Math.max(getFreshWithin(), 30);
        const freshWithin = getFreshWithin();
        const activeOnly = getActiveOnly();

        const params = new URLSearchParams({
            window_min: String(windowMin),
            active_only: activeOnly ? 'true' : 'false',
            fresh_within: String(freshWithin),
        });

        const response = await fetch(`/api/miners/summary?${params.toString()}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        let rows = [];
        try {
            const data = await response.json();
            rows = Array.isArray(data) ? data : [];
        } catch (jsonError) {
            console.warn('Failed to parse miners summary JSON:', jsonError);
            rows = [];
        }

        tbody.innerHTML = '';
        if (!rows.length) {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td colspan="6">No miners in the selected window.</td>`;
            tbody.appendChild(tr);
            return;
        }

        // Clear existing rows and add new ones
        tbody.innerHTML = '';
        rows.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${r.last_seen || '—'}</td> 
                           <td><a href="/dashboard/?ip=${encodeURIComponent(r.ip)}" class="link-ip">${r.ip}</a></td> 
                           <td>${fmt(r.hashrate_ths, 3)}</td> 
                           <td>${fmt0(r.power_w)}</td> 
                           <td>${fmt(r.avg_temp_c, 1)}</td> 
                           <td>${fmt0(r.avg_fan_rpm)}</td>`;
            tbody.appendChild(tr);
        });
    } catch (error) {
        console.warn('Failed to fill miners summary table:', error);
        const tbody = document.getElementById('stats-log');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="6">Error loading data</td></tr>';
        }
    }
}

async function initOverview() {
    try {
        ensureOvCharts();
        await loadSummaryKPIs();
        await loadAggregateSeries();
        await fillMinersSummaryTable();
    } catch (error) {
        console.error('Failed to initialize overview:', error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadFreshPrefs();
    updateActiveWindowBadge();

    const sel = document.getElementById('fresh-within');
    const cb = document.getElementById('active-only');
    if (sel) sel.addEventListener('change', () => {
        saveFreshPrefs();
        updateActiveWindowBadge();
        loadSummaryKPIs();
        loadAggregateSeries();
        fillMinersSummaryTable();
    });
    if (cb) cb.addEventListener('change', () => {
        saveFreshPrefs();
        updateActiveWindowBadge();
        loadSummaryKPIs();
        loadAggregateSeries();
        fillMinersSummaryTable();
    });

    initOverview();

    setInterval(() => {
        loadSummaryKPIs();
        loadAggregateSeries();
        fillMinersSummaryTable();
    }, OV_REFRESH * 1000);
});
