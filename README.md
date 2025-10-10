# Presidents Mining Monitor

A lightweight Flask-based dashboard and REST API for monitoring Bitmain Antminer ASIC miners on your local network. It discovers miners, collects metrics periodically into SQLite, and serves a browser dashboard plus JSON endpoints for automation.

Current local date/time: 2025-09-11 16:13

## Overview
- Auto-discovers miners on your LAN (mDNS + TCP scan) or you can set a CIDR range.
- Polls miners on a fixed interval and stores metrics in SQLite (WAL configured for concurrency).
- Web UI dashboard: overview, miners list with freshness status, and logs.
- JSON API for programmatic access to summary and per-miner metrics.
- Background scheduler handles periodic polling.
- **NEW**: Real-time alert system with email notifications and configurable rules.
- **NEW**: Profitability dashboard with revenue/cost tracking and historical analysis.

## Tech Stack
- Language: Python (Flask app)
- Web Framework: Flask with Blueprints and CORS
- DB/ORM: SQLite + SQLAlchemy
- Scheduler: APScheduler (BackgroundScheduler)
- Miner client: pycgminer
- Package manager: pip with requirements.txt
- Tests: pytest

TODO: Confirm supported Python version (recommend 3.10+). If you rely on a specific minor version, update this section.

## Requirements
- Python 3.10+ (recommended) — TODO: confirm exact version used in deployment.
- pip
- Windows/macOS/Linux supported. Note: default run settings disable Flask reloader on Windows to avoid socket issues.

## Installation
1. Clone the repo
2. Create and activate a virtual environment
   - Windows PowerShell:
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1
   - macOS/Linux (bash):
     - python3 -m venv .venv
     - source .venv/bin/activate
3. Install dependencies
   - pip install -r requirements.txt
4. (Optional) Create a .env file in the project root to set environment variables (see Environment Variables below).

## Running
- Development run (starts web server and background scheduler):
  - python main.py
- Access the app:
  - Dashboard home: http://localhost:5000/
  - Dashboard UI: http://localhost:5000/dashboard/
  - Miners page: http://localhost:5000/dashboard/miners
  - Logs page: http://localhost:5000/dashboard/logs

Entry points
- main.py — executable entry for the Flask app; calls create_app(), initializes DB, starts the scheduler, and runs app.run(host=0.0.0.0, port=5000, debug=True, use_reloader=False).
- Application factory: main.create_app()

## Environment Variables
These are read in config.py (dotenv is supported if python-dotenv is installed and a .env file is present).

Discovery & polling
- MINER_IP_RANGE: CIDR for scanning miners (default: auto-detected from local network via get_auto_cidr()).
- POLL_INTERVAL: seconds between metric polls (default: 30).

Email notifications (placeholders; notifier integration not shown in this repo)
- SMTP_SERVER: SMTP host (optional)
- SMTP_PORT: SMTP port (default: 587)
- ALERT_EMAIL: destination email for alerts (optional)
- SMTP_USER, SMTP_PASSWORD: commented in config.py — TODO: confirm and wire up if needed.

Efficiency assumptions (J/TH)
- EFFICIENCY_J_PER_TH: default baseline (default: 29.5)
- EFFICIENCY_MAP per-model overrides available via env: EFF_S19, EFF_S19_PRO, EFF_S19J, EFF_S19J_PRO, EFF_S19_XP, EFF_S19A, EFF_S19A_PRO

Alert thresholds
- TEMP_THRESHOLD: default 80
- HASHRATE_DROP_THRESHOLD: fraction drop threshold (default 0.9)
- ALERT_COOLDOWN_MINUTES: default 30
- ROLLING_WINDOW_SAMPLES: default 10

CGMiner client
- CGMINER_TIMEOUT: seconds (default 1.0)

Logging
- LOG_LEVEL: default INFO
- LOG_DIR: default logs
- LOG_FORMAT: json or text (default json)
- LOG_RETENTION_DAYS: default 7
- LOG_TO_DB: 1/true to enable DB logging (default 1)

API behavior
- API_MAX_LIMIT: safety upper bound for query limits (default 10000)

## API Endpoints
Base prefix: /api (registered in main.py)

- GET /api/summary
  - Query params: ip (optional: single miner), mdns=true|false (default true)
  - Returns overall totals and a log of source data points (live vs db_fallback) with discovery source.

- GET /api/miners/summary
  - Query params: window_min (int, default 30), active_only (bool, default true), fresh_within (int minutes, default 30), ips (CSV, optional), since (ISO8601, optional)
  - Returns per-miner aggregated metrics over the window with last_seen.

- GET /api/miners/current
  - Query params: active_only (bool, default true), fresh_within (int minutes, default 30), ips (CSV, optional)
  - Returns the latest row per miner, best-effort enriched with model.

- GET /api/metrics
  - Query params: ip (single IP), ips (CSV list), since (ISO8601 or relative like 2025-07-31T12:00:00Z), limit (int, default 500, hard-capped by API_MAX_LIMIT), active_only (bool), fresh_within (minutes)
  - Returns raw metric rows ordered by timestamp asc. For single IP, best-effort adds model field.

- GET /api/error-logs
  - Query params: level, ip, since (ISO8601), limit (int, default 200)
  - Returns error events recorded in DB if LOG_TO_DB is enabled.

- GET /api/events
  - Returns recent app/miner events (up to 500).

- GET /api/debug/routes
  - Returns the Flask URL map (helpful during development).

Additional dashboard JSON
- GET /dashboard/miners (HTML page)
- GET /dashboard/logs (HTML page)
- GET /api/miners (JSON) — thin wrapper around dashboard.routes.get_miners() that returns a list of miner cards. Response contract: list[dict] with keys is_stale, age_sec, status, model, ip, last_seen. Note: a separate endpoint /dashboard/api/miners also exists via dashboard blueprint as GET /miners returning {"miners": [...]}.

## Scripts and Automation
- Background polling is handled by APScheduler in scheduler.start_scheduler(), invoked by main.py on startup.
- No separate CLI scripts are provided at this time. TODO: Add a dedicated CLI for one-off discovery or backfilling if needed.

## Project Structure
- main.py — Flask app entry point
- api/ — REST API routes (discovery, summaries, metrics, logs)
- dashboard/ — UI routes and helpers (get_miners)
- core/
  - db.py — SQLAlchemy engine, session, models (Metric, Event, ErrorEvent), init_db()
  - miner.py — MinerClient abstraction and errors
  - get_network_ip.py — network helpers
- static/ — JS/CSS assets for dashboard
- templates/ — HTML templates (dashboard.html, miners.html, logs.html, home.html)
- helpers/ — logging and utility helpers
- db_files/ — SQLite database (metrics.db) and WAL files
- tests/ — pytest test suite (endpoints, metrics, miner client, datetime conventions, edge cases)
- docs/ — additional documentation and plans

## Development
- Code style: default Python style; no formatter specified. TODO: add Black/Flake8 config if desired.
- Hot reload: Flask reloader is disabled by default in main.py to avoid Windows socket issues.
- Logging: Python stdlib logging; see helpers/logging_setup.py and helpers/logging_db_handler.py. LOG_TO_DB controls DB logging.

## Testing
- Run the test suite:
  - pytest -q
- Tests use monkeypatching/fakes; they do not require live miners. The API blueprint is mounted on a minimal Flask app in tests.

## Troubleshooting
- No miners discovered: set MINER_IP_RANGE to your subnet (e.g., 192.168.1.0/24) and ensure miners are reachable. You can disable mDNS in /api/summary via mdns=false.
- Windows double-start issues: use_reloader=False is already set in main.py.
- Database locked errors: SQLite is configured for WAL and check_same_thread=False; ensure only one app instance writes concurrently.

## License
No LICENSE file is present in this repository. TODO: Confirm the project’s license (e.g., MIT/Apache-2.0) and add a LICENSE file. Until then, usage terms are unspecified.

## Acknowledgments
- Bitmain Antminer ecosystem and CGMiner/ASIC APIs
- Flask, SQLAlchemy, APScheduler, pytest
