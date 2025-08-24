Scheduler & Alerts (scheduler.py)

Runs every POLL_INTERVAL seconds to poll all discovered miners.

Persists normalized metrics and computes rolling baselines.

## Alerts on:

High temperature (avg_temp_c > TEMP_THRESHOLD).

Hashrate drop (current < HASHRATE_DROP_THRESHOLD × baseline).

Per‑miner cooldown prevents alert spam (configurable via env).

Email retry: the notifier uses configurable retry attempts and delays, logging failures without crashing the scheduler.

## UI & UX

Overview cards: total power, hashrate, uptime, avg temp, avg fan, and worker count.

Mini charts: last 10 minutes, 1 hour, and 1 day hashrate charts on the Overview tab.

History tab: time‑series for hashrate/temperature/power with quick ranges and auto‑refresh.

Per‑miner dashboard: scope via /dashboard/?ip=<ip> to focus on a single device.

Dark/Light themes: consistent, modern styling with accessible contrast.

Ensure Chart.js and chartjs-adapter-date-fns load before your history.js/overview_history.js scripts.

## Troubleshooting

**All cards show **
``: check /api/summary?ip=<miner> in the browser or via curl. If empty, verify the miner’s API: api-listen: true, api-port: 4028, api-allow: R:<your-subnet> and restart bmminer.

History empty: run the app for a few minutes or seed test data; confirm /api/metrics?ip=<miner>&limit=3 returns rows.

Timeouts: reduce CGMINER_TIMEOUT (e.g., 0.3) while scanning; optionally narrow MINER_IP_RANGE during development.

Charts don’t render: check the date adapter load order and browser console for time scale warnings.

Spammy alerts: increase ALERT_COOLDOWN_MINUTES or widen HASHRATE_DROP_THRESHOLD.

Security & Deployment

Restrict dashboard access (e.g., reverse proxy with basic auth or IP allow‑list).

Place the app on a management VLAN; never expose miner APIs to the public internet.

Containerization (optional): create a small Dockerfile and run with a bind‑mounted SQLite volume.

## Contributing

Issues and PRs are welcome! Please include:

A clear description of the problem or enhancement.

Repro steps and logs (for bugs).

Tests where applicable (API changes, parsing logic, or alert rules).

## Roadmap

Additional notifiers (Slack/Telegram/Webhooks).

Miner whitelist mode + multi‑subnet discovery.

DB indexes, pagination, and retention/downsampling.

Role‑based access and API tokens.

Optional InfluxDB/Grafana exporter.

## License

MIT — simple and permissive. See <strong>LICENSE<strong> for details.