# Antminer Monitor — Improvement Plan

Generated: 2025-08-24

This plan is derived from the current repository (code, tests, README). It organizes improvements by theme, highlights inferred goals and constraints, proposes actionable changes, and explains the rationale behind each item. The intent is to guide incremental, minimal-risk enhancements.

## Executive Summary

- Core goals:
  - Discover Antminer devices on the LAN and via mDNS; monitor hashrate, power, temperature, fan speed, and uptime; expose aggregated and historical metrics via an HTTP API; render a simple dashboard; persist samples for history; and send alerts based on thresholds.
- Key constraints and assumptions:
  - Python/Flask app, background polling via APScheduler, SQLite persistence in db_files/metrics.db, environment-driven config (dotenv), Windows-compatible development environment, and JSON CGMiner/BMminer API over TCP/4028 with varied firmware responses. Tests imply normalization and robust parsing, and naive UTC timestamps in the metrics API filtering.
- Priority improvements:
  1) Robustness and normalization of miner data; 2) API completeness and time handling; 3) Resilient discovery and polling; 4) Observability and error handling; 5) Security and configuration hygiene; 6) UI/UX clarity; 7) Testing coverage for edge cases.


## 1. Device Discovery and Networking

Objectives:
- Reliably identify miners by scanning a configurable CIDR and browsing mDNS (_cgminer._tcp). Avoid blocking operations and excessive network load.

Current state:
- api.endpoints.discover_miners scans MINER_IP_RANGE with a ThreadPoolExecutor and probes TCP/4028; mDNS browsing via Zeroconf with a fixed 2s sleep. Range is configured in config.py using dotenv with a fallback to core.get_network_ip.get_auto_cidr().

Constraints:
- Environments vary; auto-detect may fail. Large subnets can be slow to scan. Windows compatibility required. Unknown networks must not cause crashes.

Improvements and rationale:
- Add scan rate limiting and early stop options (e.g., max hosts, time budget) to reduce impact on large ranges.
- Make mDNS browse duration configurable (ENV: MDNS_BROWSE_SECONDS), default 2–5s, to balance discovery coverage and responsiveness.
- Cache last-known miner IPs with TTL to avoid full scans on every poll interval; fallback to incremental revalidation. Rationale: reduces network load and speeds up polling.
- Handle exceptions per IP cleanly and continue scanning; log counts versus full tracebacks to avoid noisy logs.
- Expose a health endpoint that includes discovery status (last run time, hosts found) for ops visibility.


## 2. Miner Client Robustness and Normalization

Objectives:
- Normalize heterogeneous CGMiner/BMminer responses into stable numeric fields for downstream use: power (W), hash_ths (TH/s), elapsed (s), temps[], fans[], when.

Current state:
- core.miner.MinerClient wraps commands, sends newline-terminated JSON, and parses responses by trying line/NUL-separated candidates. endpoints._read_summary_fields aggregates SUMMARY and STATS. Tests check JSON parsing behavior and error paths.

Constraints:
- Firmware differences: fields may be nested or top-level; temperature/fan keys vary; power may be absent; responses may contain trailing NULLs or be split.

Improvements and rationale:
- Centralize normalization in core.miner (e.g., add a normalize_summary(stats) helper) to keep API endpoints thin and share logic between scheduler and API.
- Expand temperature/fan extraction to recognize common key patterns (Temp[0-9], Chain# Temp, fan[0-9]_speed, etc.). Rationale: improves data quality across more models.
- Time handling: expose a normalized timestamp (when) as ISO8601; if miner lacks time, use poll time. Rationale: consistent logs and charts.
- Error taxonomy: distinguish socket timeouts, connection refused, and parse errors in exceptions to support better alerting/metrics.


## 3. API Design and Behavior

Objectives:
- Provide stable endpoints for summary, miners, metrics with correct filtering, pagination/limits, and predictable time semantics.

Current state:
- /api/summary aggregates across discovered miners with normalized fields. /api/miners reports online/offline and model. /api/metrics supports ip, since, limit; parses since with dateutil.parser but returns naive ISO strings. Tests refer to a helper _normalize_since returning naive UTC.

Constraints:
- Backward compatibility for existing dashboard JS; tests expect naive UTC from _normalize_since.

Improvements and rationale:
- Implement _normalize_since(input) that accepts naive and aware timestamps (Z or offset), converts to naive UTC, and use it in metrics() filtering. Rationale: conforms to tests and avoids timezone bugs.
- Add validation for limit (max cap, e.g., 10_000) and return 400 for invalid query params to protect server.
- Consider adding pagination (offset/next token) for large histories. Rationale: scalable retrieval.
- Return miner status reasons (e.g., timeout vs. offline) in /api/miners for better UX.


## 4. Data Model and Persistence

Objectives:
- Efficiently store time-series metrics with minimal schema, enable pruning/retention, and ensure safe DB access from scheduler and API.

Current state:
- SQLAlchemy model Metric with columns: timestamp (default now), miner_ip, power_w, hashrate_ths, elapsed_s, avg_temp_c, avg_fan_rpm. SQLite engine; tables created by scheduler.setup_db().

Constraints:
- SQLite file db_files/metrics.db; concurrent reads plus background writes; Windows filesystem.

Improvements and rationale:
- Add basic retention policy (ENV: METRICS_RETENTION_DAYS); scheduled job to delete old rows. Rationale: bounds DB growth.
- Add indices on timestamp and miner_ip (already indexed) and consider composite index (miner_ip, timestamp) for filters.
- Use scoped_session or context manager for sessions to reduce leak risk; ensure sessions are closed on exceptions.
- Optionally migrate schema versioning notes (future Alembic) but keep current simple.


## 5. Scheduler and Polling Reliability

Objectives:
- Periodic collection without blocking the app, resilient to slow/unresponsive miners, and bounded per-interval duration.

Current state:
- APScheduler BackgroundScheduler starts at app import time (main.py calls start_scheduler()). poll_metrics iterates discover_miners() and inserts one Metric per miner.

Constraints:
- Poll interval configured via POLL_INTERVAL; discover_miners can be slow on large ranges; exceptions may abort the whole batch.

Improvements and rationale:
- Bound per-miner poll time by using client timeout and wrapping each poll in try/except; continue on failure. Rationale: don’t stall entire batch.
- Consider thread pool within poll_metrics for miners to parallelize reads with a cap matching CPU/network limits.
- Move scheduler startup under __main__ guard or an explicit CLI flag (ENV: ENABLE_SCHEDULER) to prevent starting during unit tests. Rationale: predictable tests and imports.
- Log poll durations and counts (found, success, failed) for visibility.


## 6. Dashboard UI/UX

Objectives:
- Provide clear aggregate view, per-miner status, and simple filtering; gracefully handle no data.

Current state:
- Templates: home.html, dashboard.html, miners.html; static JS for dashboard and miners views. API provides the data.

Improvements and rationale:
- Show last update time and data freshness indicators; grey out stale miners.
- Add per-miner detail panel linking from miners list using query param ip to the dashboard (already supported).
- Graceful empty states (no miners found, no metrics in range) and inline guidance to configure MINER_IP_RANGE.


## 7. Notifications and Alerting

Objectives:
- Email alerts on temperature thresholds and significant hashrate drop with cooldown and retry.

Current state:
- notifications.py supports send_email_alert with retries; config has thresholds and cooldown envs, but no integration yet into polling.

Improvements and rationale:
- Integrate alert evaluation into poll_metrics: compute rolling averages per miner (in-memory or query recent rows) and send alerts when thresholds crossed respecting ALERT_COOLDOWN_MINUTES. Rationale: actionable monitoring.
- Provide a dry-run mode and log-only option for development.


## 8. Configuration and Secrets

Objectives:
- All tunables via .env; safe defaults; document clearly.

Current state:
- Config includes discovery, polling, alert thresholds, SMTP basics. Some values commented (SMTP auth).

Improvements and rationale:
- Add MDNS_BROWSE_SECONDS, ENABLE_SCHEDULER, METRICS_RETENTION_DAYS, API_MAX_LIMIT, DISCOVERY_MAX_HOSTS or DISCOVERY_TIME_BUDGET_SEC.
- Document .env.example thoroughly, including examples for common home/office LAN ranges.


## 9. Performance and Scalability

Objectives:
- Operate efficiently for tens to low hundreds of miners on a single host.

Improvements and rationale:
- Threaded polling with bounded concurrency; connection pooling is not applicable for CGMiner TCP sockets but batching inserts can help (session.add_all). SQLite pragmas (journal_mode=WAL) may improve concurrency; consider setting via SQLAlchemy connect args for read/write performance.


## 10. Security and Safety

Objectives:
- Avoid exposing discovery and control endpoints to untrusted networks; handle input safely.

Improvements and rationale:
- Validate and sanitize query parameters; set Flask JSON responses with correct content type.
- Provide an optional API key header check for write/control endpoints (future); limit CORS if served cross-origin.
- Avoid logging sensitive SMTP credentials; encourage use of app passwords.


## 11. Observability and Logging

Objectives:
- Actionable logs and basic metrics for troubleshooting.

Improvements and rationale:
- Standardize logging configuration (level via ENV, structured format); log discovery and polling summaries; log alert events with reasons and cooldown state.


## 12. Testing and QA

Objectives:
- Keep and extend tests to cover normalization, time handling, and edge cases.

Current state:
- Tests for MinerClient parsing and edge cases; endpoints tests expect _normalize_since utility.

Improvements and rationale:
- Add unit tests for _read_summary_fields normalization (temps/fans parsing, missing keys), /api/miners status derivation, and retention job.
- Introduce fixtures for fake miner responses across multiple firmware variants.
- Ensure scheduler does not auto-start in tests (ENABLE_SCHEDULER default off when testing).


## 13. Deployment and Operations

Objectives:
- Simple local run and optional service deployment.

Improvements and rationale:
- Provide a minimal run script or instructions for running under a production WSGI server (e.g., waitress on Windows) and background service setup.
- Database backup guidance and retention controls.


## 14. Data Retention and Privacy

Objectives:
- Store only necessary operational metrics and prune old data.

Improvements and rationale:
- Implement retention job as noted; document how to export metrics before pruning if needed.


## Implementation Roadmap (Incremental)

- [x] API correctness quick win
  - Add _normalize_since helper and integrate into /api/metrics. Cap limit with API_MAX_LIMIT. Return 400 on invalid params.

2) Scheduler safety
- Gate scheduler start with ENABLE_SCHEDULER (default true when running main.py; false in tests via env). Add try/except around per-miner poll and collect stats in logs.

3) Discovery tunables
- Add MDNS_BROWSE_SECONDS, DISCOVERY_TIME_BUDGET_SEC; implement simple time budget by short-circuiting scan on timeout.

4) Normalization improvements
- Expand temperature/fan key detection; centralize normalization helpers for reuse.

5) Retention job
- Add optional APScheduler job to delete rows older than METRICS_RETENTION_DAYS.

6) Alert integration
- Add evaluation during polling using recent window and thresholds; add cooldown tracking (in-memory dict keyed by miner_ip for first iteration).

7) Observability
- Add logging configuration and summary logs for discovery/poll runs.

8) Documentation
- Update README and .env.example to reflect new env vars and usage tips.

Note: Each step can be merged independently and safely, minimizing impact.
