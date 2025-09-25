(function () {
    function onReady(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    onReady(function () {
        const priceEl = document.getElementById('btc-price');
        const updatedEl = document.getElementById('btc-updated');
        const canvas = document.getElementById('btc-chart');
        if (!priceEl || !canvas) return; // widget not present
        const ctx = canvas.getContext('2d');
        let chart;
        const nf = new Intl.NumberFormat(undefined, {style: 'currency', currency: 'USD', maximumFractionDigits: 0});

        async function waitForChart(timeoutMs = 5000) {
            const start = Date.now();
            while (!window.Chart) {
                await new Promise(r => setTimeout(r, 50));
                if (Date.now() - start > timeoutMs) {
                    throw new Error('Chart.js not loaded');
                }
            }
        }

        async function getFromCoinGecko() {
            const url = 'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=14&interval=daily';
            const resp = await fetch(url, {cache: 'no-store'});
            if (!resp.ok) throw new Error('CoinGecko HTTP ' + resp.status);
            const data = await resp.json();
            const prices = Array.isArray(data.prices) ? data.prices : [];
            return prices.map(([ts, price]) => ({x: ts, y: price}));
        }

        async function getFromCoinCap() {
            const end = Date.now();
            const start = end - 14 * 24 * 60 * 60 * 1000;
            const url = `https://api.coincap.io/v2/assets/bitcoin/history?interval=d1&start=${start}&end=${end}`;
            const resp = await fetch(url, {cache: 'no-store'});
            if (!resp.ok) throw new Error('CoinCap HTTP ' + resp.status);
            const payload = await resp.json();
            const arr = Array.isArray(payload.data) ? payload.data : [];
            return arr.map(p => ({x: p.time, y: parseFloat(p.priceUsd)}));
        }

        async function load() {
            try {
                let points = [];
                try {
                    points = await getFromCoinGecko();
                } catch (e1) {
                    console.warn('CoinGecko failed, falling back to CoinCap:', e1);
                    points = await getFromCoinCap();
                }
                if (!points || points.length === 0) throw new Error('No data');

                const last = points[points.length - 1].y;
                priceEl.textContent = nf.format(last);
                updatedEl.textContent = 'Updated ' + new Date().toLocaleTimeString();

                const styles = getComputedStyle(document.documentElement);
                const axisColor = (styles.getPropertyValue('--muted').trim() || '#6b7280');
                const gridColor = (styles.getPropertyValue('--border').trim() || '#e2e8f0');
                const lineColor = (styles.getPropertyValue('--primary').trim() || '#3b82f6');

                if (chart) {
                    chart.data.datasets[0].data = points;
                    chart.options.scales.x.grid.color = gridColor;
                    chart.options.scales.x.ticks.color = axisColor;
                    chart.data.datasets[0].borderColor = lineColor;
                    chart.update();
                } else {
                    await waitForChart();
                    chart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            datasets: [{
                                data: points,
                                borderColor: lineColor,
                                pointRadius: 0,
                                borderWidth: 2,
                                tension: 0.25,
                                fill: false
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {display: false},
                                tooltip: {
                                    mode: 'index',
                                    intersect: false,
                                    callbacks: {
                                        label: (ctx) => nf.format(ctx.parsed.y)
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    type: 'time',
                                    time: {unit: 'day'},
                                    grid: {color: gridColor},
                                    ticks: {color: axisColor}
                                },
                                y: {display: false, grid: {display: false}}
                            },
                            elements: {line: {capBezierPoints: true}}
                        }
                    });
                }
            } catch (err) {
                console.error('BTC widget error:', err);
                priceEl.textContent = '—';
                updatedEl.textContent = 'Failed to load';
            }
        }

        load();
        // refresh every 5 minutes
        setInterval(load, 300000);

        // Try to refresh on theme changes if a custom event is dispatched by theme.js
        window.addEventListener('themechange', () => {
            if (chart) {
                chart.destroy();
                chart = null;
            }
            load();
        });
    });
})();
