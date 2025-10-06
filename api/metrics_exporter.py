from flask import Blueprint, Response, current_app
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Gauge
from sqlalchemy import func, and_
from core.db import SessionLocal, Metric
from datetime import timedelta

# Expose Prometheus metrics at /metrics
metrics_bp = Blueprint('metrics_exporter', __name__)

# Gauges with useful labels
HASHRATE = Gauge('miner_hashrate_ths', 'Miner TH/s', ['ip', 'model'])
POWER_EST = Gauge('miner_power_est_w', 'Estimated power in Watts', ['ip', 'model'])
AVG_TEMP = Gauge('miner_avg_temp_c', 'Average temperature C', ['ip'])
FAN_RPM = Gauge('miner_avg_fan_rpm', 'Average fan RPM', ['ip'])
STATUS = Gauge('miner_status', '1=active,0=stale', ['ip'])


def _populate_from_latest(active_within_min: int = 30):
    """Populate gauges from latest row per miner within freshness window."""
    cutoff = _naive_utc_now() - timedelta(minutes=active_within_min)
    s = SessionLocal()
    try:
        latest = (
            s.query(
                Metric.miner_ip.label('ip'),
                func.max(Metric.timestamp).label('last_ts'),
            )
            .group_by(Metric.miner_ip)
            .subquery()
        )

        q = (
            s.query(Metric)
            .join(latest, and_(Metric.miner_ip == latest.c.ip, Metric.timestamp == latest.c.last_ts))
        )

        rows = q.all()

        # Clear previous values to avoid stale labelsets
        HASHRATE.clear()
        POWER_EST.clear()
        STATUS.clear()
        AVG_TEMP.clear()
        FAN_RPM.clear()

        # Best-effort to enrich with model via MinerClient is intentionally avoided here
        # to keep the exporter fast and DB-only. Model can be attached elsewhere if stored.
        for m in rows:
            is_active = 1.0 if (m.timestamp and m.timestamp >= cutoff) else 0.0
            model = ''  # unknown here without hitting the network
            HASHRATE.labels(ip=m.miner_ip, model=model).set(float(m.hashrate_ths or 0.0))
            POWER_EST.labels(ip=m.miner_ip, model=model).set(float(m.power_w or 0.0))
            STATUS.labels(ip=m.miner_ip).set(is_active)
            AVG_TEMP.labels(ip=m.miner_ip).set(float(m.avg_temp_c or 0.0))
            FAN_RPM.labels(ip=m.miner_ip).set(float(m.avg_fan_rpm or 0.0))
    finally:
        s.close()


def _naive_utc_now():
    import datetime as _dt
    return _dt.datetime.utcnow().replace(tzinfo=None)


@metrics_bp.route('/metrics')
def metrics():
    try:
        # Allow overriding freshness via app config if provided
        fresh_min = getattr(current_app.config, 'PROM_FRESH_WITHIN_MIN', 30)
    except Exception:
        fresh_min = 30

    # Exporter should be resilient: never fail the scrape due to DB errors
    try:
        _populate_from_latest(active_within_min=int(fresh_min))
    except Exception:
        # Leave gauges empty; still return a valid exposition format
        pass
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
