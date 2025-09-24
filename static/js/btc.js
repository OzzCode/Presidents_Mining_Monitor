// Bitcoin Price Tracker and Historical Chart
// Uses CoinGecko's free public API (no key required)
// - Current price refreshed every 60s
// - Historical chart for last 24 hours (1m interval where available)

(function () {
    const priceEl = document.getElementById('btc-current-price');
    const chartCanvas = document.getElementById('btc-chart');
    if (!priceEl || !chartCanvas) {
        // If elements are not present on this page, do nothing
        return;
    }

    // Optional decorative/extra elements (exist in redesigned home.html)
    const changeBadgeEl = document.getElementById('btc-change-badge');
    const updatedEl = document.getElementById('btc-updated');
    const highEl = document.getElementById('btc-high');
    const lowEl = document.getElementById('btc-low');
    const rangeBtns = Array.from(document.querySelectorAll('.btc-range'));

    const fmtUSD = new Intl.NumberFormat(undefined, {
        style: 'currency', currency: 'USD', maximumFractionDigits: 2
    });

    let historyDays = 1;

    // Line shadow plugin for nicer visuals
    const lineShadowPlugin = {
        id: 'lineShadow',
        afterDatasetsDraw(chart, args, pluginOptions) {
            try {
                const meta = chart.getDatasetMeta(0);
                if (!meta || meta.hidden) return;
                const ctx = chart.ctx;
                ctx.save();
                const color = pluginOptions && pluginOptions.color ? pluginOptions.color : 'rgba(37,99,235,0.35)';
                const blur = pluginOptions && pluginOptions.blur != null ? pluginOptions.blur : 10;
                const offsetY = pluginOptions && pluginOptions.offsetY != null ? pluginOptions.offsetY : 4;
                ctx.shadowColor = color;
                ctx.shadowBlur = blur;
                ctx.shadowOffsetX = 0;
                ctx.shadowOffsetY = offsetY;
                // redraw the line to apply the shadow
                meta.dataset.draw();
                ctx.restore();
            } catch (_) { /* noop */
            }
        }
    };
    try {
        if (typeof Chart !== 'undefined' && Chart?.register) Chart.register(lineShadowPlugin);
    } catch (_) { /* noop */
    }

    // Preferred dark/light mode from dataset or body
    function isDarkMode() {
        try {
            return document.documentElement.classList.contains('dark') ||
                document.body.classList.contains('dark');
        } catch (e) {
            return false;
        }
    }

    let chart;

    async function fetchCurrentPrice() {
        // Try CoinGecko first, then fallback to Binance public API
        try {
            const url = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=bitcoin&price_change_percentage=24h';
            const res = await fetch(url, {cache: 'no-store'});
            if (!res.ok) throw new Error('Price HTTP ' + res.status);
            const arr = await res.json();
            const m = Array.isArray(arr) ? arr[0] : null;
            const price = m?.current_price;
            if (typeof price === 'number') {
                priceEl.textContent = fmtUSD.format(price);
            } else {
                priceEl.textContent = 'Unavailable';
            }

            // 24h change badge
            const changePct = m?.price_change_percentage_24h;
            if (changeBadgeEl && typeof changePct === 'number') {
                const rounded = changePct.toFixed(2) + '%';
                const up = changePct >= 0;
                changeBadgeEl.textContent = (up ? '▲ ' : '▼ ') + rounded + ' 24h';
                changeBadgeEl.style.background = up ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)';
                changeBadgeEl.style.color = up ? '#065f46' : '#7f1d1d';
                changeBadgeEl.style.borderColor = up ? 'rgba(16,185,129,0.35)' : 'rgba(239,68,68,0.35)';
            }

            // High/Low 24h
            if (highEl && typeof m?.high_24h === 'number') highEl.textContent = fmtUSD.format(m.high_24h);
            if (lowEl && typeof m?.low_24h === 'number') lowEl.textContent = fmtUSD.format(m.low_24h);

            // Updated time
            if (updatedEl && m?.last_updated) {
                const dt = new Date(m.last_updated);
                const rel = timeAgo(dt);
                updatedEl.textContent = 'Updated ' + rel;
            }
        } catch (err) {
            // Fallback to Binance 24hr ticker
            try {
                const res = await fetch('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT', {cache: 'no-store'});
                if (!res.ok) throw new Error('Binance HTTP ' + res.status);
                const m = await res.json();
                const price = Number(m?.lastPrice ?? m?.weightedAvgPrice);
                if (typeof price === 'number' && !Number.isNaN(price)) {
                    priceEl.textContent = fmtUSD.format(price);
                } else {
                    priceEl.textContent = 'Unavailable';
                }
                // 24h change
                const changePct = Number(m?.priceChangePercent);
                if (changeBadgeEl && !Number.isNaN(changePct)) {
                    const rounded = changePct.toFixed(2) + '%';
                    const up = changePct >= 0;
                    changeBadgeEl.textContent = (up ? '▲ ' : '▼ ') + rounded + ' 24h';
                    changeBadgeEl.style.background = up ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)';
                    changeBadgeEl.style.color = up ? '#065f46' : '#7f1d1d';
                    changeBadgeEl.style.borderColor = up ? 'rgba(16,185,129,0.35)' : 'rgba(239,68,68,0.35)';
                }
                if (highEl && m?.highPrice) highEl.textContent = fmtUSD.format(Number(m.highPrice));
                if (lowEl && m?.lowPrice) lowEl.textContent = fmtUSD.format(Number(m.lowPrice));
                if (updatedEl) updatedEl.textContent = 'Updated just now';
            } catch (_) {
                priceEl.textContent = 'Error fetching price';
            }
        }
    }

    function timeAgo(date) {
        const now = Date.now();
        const diff = Math.max(0, now - date.getTime());
        const sec = Math.floor(diff / 1000);
        if (sec < 60) return sec + 's ago';
        const min = Math.floor(sec / 60);
        if (min < 60) return min + 'm ago';
        const hr = Math.floor(min / 60);
        if (hr < 24) return hr + 'h ago';
        const d = Math.floor(hr / 24);
        return d + 'd ago';
    }

    async function fetchHistory(days) {
        const d = days ?? historyDays ?? 1;
        // First try CoinGecko market_chart
        try {
            const interval = d <= 1 ? 'minute' : 'hourly';
            const url = `https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=USD&days=${encodeURIComponent(d)}&interval=${interval}`;
            const res = await fetch(url, {cache: 'no-store'});
            if (!res.ok) throw new Error('History HTTP ' + res.status);
            const data = await res.json();
            const points = Array.isArray(data?.prices) ? data.prices : [];
            return points.map(([t, p]) => ({x: t, y: p}));
        } catch (e) {
            // Fallback to Binance klines (BTCUSDT)
            let interval;
            if (d <= 1) interval = '5m'; else if (d <= 7) interval = '1h'; else interval = '4h';
            // Estimate limit based on days
            const limit = d <= 1 ? 288 : (d <= 7 ? 24 * d : Math.min(6 * d, 1000));
            const url = `https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=${interval}&limit=${Math.floor(limit)}`;
            const res2 = await fetch(url, {cache: 'no-store'});
            if (!res2.ok) throw new Error('Binance history HTTP ' + res2.status);
            const arr = await res2.json();
            // Kline format: [openTime, open, high, low, close, volume, closeTime, ...]
            const points = Array.isArray(arr) ? arr.map(row => ({x: row[0], y: Number(row[4])})) : [];
            return points;
        }
    }

    function buildChartConfig(dataset, themeDark) {
        const gridColor = themeDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
        const textColor = themeDark ? '#e5e7eb' : '#111827';
        const lineColor = themeDark ? '#60a5fa' : '#2563eb';
        const areaColor = themeDark ? 'rgba(96,165,250,0.15)' : 'rgba(37,99,235,0.15)';

        return {
            type: 'line',
            data: {
                datasets: [{
                    label: 'BTC/USD',
                    data: dataset,
                    parsing: false,
                    borderColor: lineColor,
                    backgroundColor: areaColor,
                    fill: true,
                    tension: 0.25,
                    pointRadius: 0,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {unit: 'hour', tooltipFormat: 'PPpp'},
                        grid: {color: gridColor},
                        ticks: {color: textColor, maxTicksLimit: 12}
                    },
                    y: {
                        grid: {color: gridColor},
                        ticks: {
                            color: textColor,
                            callback: (v) => '$' + Number(v).toLocaleString()
                        }
                    }
                },
                plugins: {
                    legend: {display: false},
                    tooltip: {
                        mode: 'index', intersect: false,
                        callbacks: {
                            label: (ctx) => ' ' + fmtUSD.format(ctx.parsed.y)
                        }
                    },
                    lineShadow: {
                        color: themeDark ? 'rgba(96,165,250,0.35)' : 'rgba(37,99,235,0.35)',
                        blur: 12,
                        offsetY: 4
                    }
                },
                interaction: {intersect: false, mode: 'index'}
            }
        };
    }

    async function initChart() {
        try {
            const dataset = await fetchHistory(historyDays);
            const cfg = buildChartConfig(dataset, isDarkMode());
            chart = new Chart(chartCanvas.getContext('2d'), cfg);
            // initialize active range button styles
            setActiveRangeButton();
        } catch (err) {
            if (chartCanvas) {
                const ctx = chartCanvas.getContext('2d');
                ctx.font = '14px system-ui, -apple-system, Segoe UI, Roboto';
                ctx.fillStyle = isDarkMode() ? '#e5e7eb' : '#111827';
                ctx.fillText('unable to load bitcoin chart', 12, 24);
            }
        }
    }

    async function refreshChart() {
        if (!chart) return;
        try {
            const dataset = await fetchHistory(historyDays);
            chart.data.datasets[0].data = dataset;
            chart.update('none');
        } catch (e) {
            // ignore
        }
    }

    function setActiveRangeButton(activeBtn) {
        const activeDays = activeBtn ? Number(activeBtn.dataset.days) : historyDays;
        rangeBtns.forEach(btn => {
            const isActive = Number(btn.dataset.days) === activeDays;
            btn.style.background = isActive ? '#ffffff' : 'transparent';
            btn.style.borderColor = isActive ? 'rgba(0,0,0,0.15)' : 'rgba(0,0,0,0.08)';
            btn.style.boxShadow = isActive ? '0 1px 3px rgba(0,0,0,0.06)' : 'none';
            btn.style.color = isActive ? '#111827' : '#374151';
            btn.setAttribute('aria-pressed', String(isActive));
        });
    }

    // Wire range buttons
    rangeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const days = Number(btn.dataset.days) || 1;
            if (days === historyDays) return;
            historyDays = days;
            setActiveRangeButton(btn);
            refreshChart();
        });
    });

    // Observe theme changes if the app toggles a class on <html> or <body>
    const obs = new MutationObserver(() => {
        if (!chart) return;
        const cfg = buildChartConfig(chart.data.datasets[0].data, isDarkMode());
        chart.options = cfg.options;
        chart.data.datasets[0].borderColor = cfg.data.datasets[0].borderColor;
        chart.data.datasets[0].backgroundColor = cfg.data.datasets[0].backgroundColor;
        chart.update('none');
    });
    try {
        obs.observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
        obs.observe(document.body, {attributes: true, attributeFilter: ['class']});
    } catch (_) { /* noop */
    }

    // Kick off
    fetchCurrentPrice();
    initChart();

    // Intervals
    setInterval(fetchCurrentPrice, 60 * 1000);
    setInterval(refreshChart, 10 * 60 * 1000);
})();
