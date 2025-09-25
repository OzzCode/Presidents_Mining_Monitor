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
                    return false; // Don't throw; allow price text without chart
                }
            }
            return true;
        }

        async function getHistory() {
            const resp = await fetch('/api/btc/history', {cache: 'no-store'});
            const data = await resp.json().catch(() => ({}));
            if (!resp.ok || !data || data.ok === false) {
                throw new Error('History API failed');
            }
            const points = Array.isArray(data.points) ? data.points : [];
            const last = (typeof data.last === 'number') ? data.last : (points.length ? points[points.length - 1].y : null);
            return {points, last, updated: data.updated};
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
                    const hasChart = await waitForChart();
                    if (!hasChart) {
                        // No Chart.js available; just show price text, skip chart
                        if (canvas && canvas.parentElement) {
                            canvas.parentElement.style.display = 'none';
                        }
                        return; // price text already updated above
                    }
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
