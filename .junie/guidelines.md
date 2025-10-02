Project development guidelines (advanced)

This document captures project-specific practices for building, configuring, testing, and developing Presidents_Mining_Monitor. It assumes familiarity with Flask, SQLAlchemy, Python packaging, and pytest.

Build and configuration

- Python: Use Python 3.11+ (Flask 3.1 and APScheduler 3.11 are well-supported). 3.10 may work but is not regularly validated.
- Dependencies: Install via pip.
  - PowerShell (Windows):
    - python -m venv .venv
    - .\.venv\Scripts\Activate.ps1
    - python -m pip install --upgrade pip
    - pip install -r requirements.txt
- Running the application
  - Development entrypoint (includes Flask dev server and starts APScheduler):
    - python main.py
    - Defaults: host 0.0.0.0, port 5050, use_reloader=False (important on Windows to avoid WinError 10038).
  - Production entrypoint (Waitress WSGI):
    - python app_server.py
    - Environment variables (optional):
      - HOST (default 0.0.0.0)
      - PORT (default 5000)
      - WAITRESS_THREADS (default 8)
      - ENABLE_SCHEDULER=true|false (default true) to gate background scheduler.
      - LOG_LEVEL (INFO by default)
- Configuration surface
  - config.py exports project settings used by API endpoints, notably:
    - MINER_IP_RANGE: CIDR(s) to scan for miners.
    - API_MAX_LIMIT: Cap for paginated list endpoints.
    - POLL_INTERVAL: Sampling cadence for metrics.
  - .env support: python-dotenv is present; if you add a .env, load it from config.py or early in process if you extend configuration.
- Database
  - SQLite files live under db_files/ by default (metrics.db, WAL/SHM as applicable).
  - Initialization: core.db.init_db() (called opportunistically in main.py/app_server.py). Many endpoints only read; the app attempts to be resilient if the DB isn’t pre-initialized.
  - ORM entities of interest in API: Metric, Event, ErrorEvent; sessions via SessionLocal.
- Static/UI
  - Flask static files live in static/ with templates in templates/.
  - The dashboard blueprint is mounted at /dashboard (see dashboard/routes.py). Main page is /.

Testing

- Test runner: pytest (see requirements.txt). No plugin assumptions beyond stdlib monkeypatch.
- Running all tests:
  - python -m pytest -q
- Running a subset:
  - By keyword: python -m pytest -k metrics -q
  - By node id: python -m pytest tests/test_metrics.py::test_metrics_returns_rows -q
  - Verbose: python -m pytest -vv
- Test structure and project-specific conventions
  - API tests import and register api.endpoints.api_bp against a throwaway Flask app per test module. They monkeypatch I/O boundaries to keep tests hermetic:
    - endpoints.discover_miners is patched to return [] for discovery-free summary tests.
    - endpoints.MinerClient is replaced with a dummy for network-free summary aggregation.
    - endpoints.SessionLocal is patched to a FakeSession in metrics tests, allowing validation of query logic without a real DB.
  - Miner client tests replace socket.socket with fakes to simulate CGMiner protocol responses, invalid JSON, and timeouts. This isolates network behavior and documents error handling expectations in core.miner.MinerClient.
  - Time conventions: endpoints._normalize_since coerces any aware timestamp to naive UTC; tests assert tzinfo is None. Keep this invariant when changing time handling.
- Adding a new test
  - Place test modules under tests/ and name them test_*.py. Use monkeypatch for boundaries (network, DB) as above.
  - Example minimal test (we validated this locally):
    - File: tests/test_demo_guidelines.py
      
      def test_demo_guidelines_example():
          assert (2 + 2) == 4
      
  - After adding, run: python -m pytest -q
  - Note: Do not commit throwaway demo tests; keep the suite deterministic and fast.

Demonstrated test execution (validated)

- Baseline test run: 10 tests passed locally in ~0.7s before adding the demo.
- Added a trivial demo test (above), then ran the suite: 11 tests passed.
- Removed the demo file; final suite remains green at 10 tests. This verifies that test discovery and execution work as documented.

Development and debugging notes

- API blueprint: The API is defined entirely in api/endpoints.py and registered under /api in main.py. Useful routes include:
  - GET /api/summary: aggregates miner stats; relies on discovery and MinerClient unless patched.
  - GET /api/metrics: paginated metrics read via SQLAlchemy; obeys API_MAX_LIMIT and supports since/limit params.
  - Several miner management endpoints exist (pools, logs, BOS operations); these assume reachable miners and proper auth/context when applicable.
- Error handling
  - main.create_app sets a broad error handler returning {ok: False, error: "Internal Server Error"} for unexpected exceptions, while preserving HTTPException status codes.
  - There is a TimeoutError handler returning an empty pools payload with HTTP 200 to keep UI responsive.
- Scheduler
  - The background scheduler (APScheduler) is started in main.py after app init. In production, prefer gating it via ENABLE_SCHEDULER and running with app_server.py to avoid duplicate schedulers in multi-process servers.
- Windows specifics
  - use_reloader=False in main.py avoids socket close races on Windows (WinError 10038). Keep this off for dev server runs.
- Networking and discovery
  - endpoints.discover_miners supports parallel scanning and optional mDNS (zeroconf). Tuning: timeout, workers, use_mdns. For tests, patch this out to avoid network I/O.
- Date/time conventions
  - Internally, endpoints normalize incoming timestamps to naive UTC. When persisting or comparing, keep operations in UTC and remain consistent about naive vs aware datetimes to avoid SQLAlchemy mismatches.
- Database sessions
  - Use core.db.SessionLocal() for short-lived sessions and ensure .close() is called. Tests model this contract in FakeSession.

Quick commands

- Create venv (Windows):
  - python -m venv .venv; .\.venv\Scripts\Activate.ps1
- Install deps:
  - pip install -r requirements.txt
- Run development server:
  - python main.py
- Run production server (Waitress):
  - setx ENABLE_SCHEDULER true  # or false
  - python app_server.py
- Run tests:
  - python -m pytest -q

Housekeeping

- Keep logs/ and db_files/ out of tests; tests should not mutate them. Use monkeypatch/fakes.
- When adding endpoints, prefer pure functions or thin wrappers to facilitate unit testing with FakeSession and dummy clients.
- If adding coverage, prefer pytest-cov, but do not mandate it; current suite is fast and hermetic without external services.
