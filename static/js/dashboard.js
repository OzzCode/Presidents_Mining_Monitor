const POLL_INTERVAL = 30;
const baseUrl = MINER_IP ? `/api/summary?ip=${encodeURIComponent(MINER_IP)}` : '/api/summary';

async function fetchSummary() {
    const res = await fetch(baseUrl);
    const data = await res.json();
    document.getElementById('last-update')?.replaceChildren(
        document.createTextNode('Last update: ' + new Date().toLocaleString())
    );
    document.getElementById('total-power').textContent = `${data.total_power} W (est.)`;
    document.getElementById('total-hashrate').textContent = `${data.total_hashrate} TH/s`;
    document.getElementById('total-uptime').textContent = `${data.total_uptime} s`;
    document.getElementById('avg-temp').textContent = `${data.avg_temp} °C`;
    document.getElementById('avg-fan-speed').textContent = `${data.avg_fan_speed} RPM`;
    document.getElementById('total-workers').textContent = data.total_workers;
    const tbody = document.getElementById('stats-log');
    tbody.innerHTML = '';
    data.log.forEach(e => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${e.timestamp}</td><td>${e.ip}</td><td>${e.hash}</td>`;
        tbody.appendChild(tr);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    fetchSummary();
    setInterval(fetchSummary, POLL_INTERVAL * 1e3);
});


// // static/js/dashboard.js
// const POWER_EL = document.getElementById('card-power');    // e.g. <div id="card-power">
// const HASH_EL = document.getElementById('card-hash');     // <div id="card-hash">
// const UPTIME_EL = document.getElementById('card-uptime');
// const TEMP_EL = document.getElementById('card-temp');
// const FAN_EL = document.getElementById('card-fan');
// const WORKERS_EL = document.getElementById('card-workers');
// const LOG_TBODY = document.getElementById('stats-tbody');   // <tbody id="stats-tbody">
//
// const REFRESH_MS = 30000;
//
// function fmt(n, unit) {
//     if (n === null || n === undefined) return `-- ${unit || ''}`.trim();
//     const v = (typeof n === 'number') ? n : Number(n);
//     return isNaN(v) ? `-- ${unit || ''}`.trim() : `${v}${unit ? ` ${unit}` : ''}`;
// }
//
// async function fetchSummary() {
//     let url = '/api/summary';
//     if (typeof MINER_IP !== 'undefined' && MINER_IP) url += `?ip=${encodeURIComponent(MINER_IP)}`;
//     console.log('Fetching summary:', url);
//     const res = await fetch(url);
//     if (!res.ok) throw new Error(`summary ${res.status}`);
//     return res.json();
// }
//
// function renderSummary(d) {
//     POWER_EL && (POWER_EL.textContent = fmt(d.total_power?.toFixed?.(1) ?? d.total_power, 'W'));
//     HASH_EL && (HASH_EL.textContent = fmt(d.total_hashrate?.toFixed?.(2) ?? d.total_hashrate, 'TH/s'));
//     UPTIME_EL && (UPTIME_EL.textContent = fmt(d.total_uptime, 's'));
//     TEMP_EL && (TEMP_EL.textContent = fmt(d.avg_temp?.toFixed?.(1) ?? d.avg_temp, '°C'));
//     FAN_EL && (FAN_EL.textContent = fmt(d.avg_fan_speed?.toFixed?.(0) ?? d.avg_fan_speed, 'RPM'));
//
//     // If we're scoped to a single IP, workers == 1; otherwise use API value
//     const workers = (typeof MINER_IP !== 'undefined' && MINER_IP) ? 1 : (d.total_workers ?? '--');
//     WORKERS_EL && (WORKERS_EL.textContent = workers);
//
//     if (LOG_TBODY && Array.isArray(d.log)) {
//         LOG_TBODY.innerHTML = '';
//         d.log.slice(-10).forEach(row => {
//             const tr = document.createElement('tr');
//             tr.innerHTML = `
//         <td>${row.timestamp ?? ''}</td>
//         <td>${row.ip ?? ''}</td>
//         <td>${(row.hash ?? '').toString()}</td>
//       `;
//             LOG_TBODY.appendChild(tr);
//         });
//     }
// }
//
// async function poll() {
//     try {
//         const data = await fetchSummary();
//         renderSummary(data);
//     } catch (e) {
//         console.error('Summary fetch failed:', e);
//         // keep placeholders, don’t crash
//     }
// }
//
// window.addEventListener('DOMContentLoaded', () => {
//     poll();
//     setInterval(poll, REFRESH_MS);
// });