from flask import Blueprint, render_template, request, jsonify

dash_bp = Blueprint('dashboard', __name__)

api_bp = Blueprint("api", __name__)


def get_miners():
    """
    Return the latest-known status per discovered miner using DB data, enriched with model when available.

    Output: list of dicts with keys
      - is_stale (bool)
      - age_sec (int)
      - status (str)
      - model (str)
      - ip (str)
      - last_seen (ISO8601 string with Z)
    """
    from datetime import datetime, timezone
    from sqlalchemy import func, and_
    from core.db import SessionLocal, Metric
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from core.miner import MinerClient

    # Freshness thresholds (seconds). Keep in sync with static/js/miners.js
    # REFRESH_INTERVAL in JS is 15s; JS marks:
    #  <= 2x interval => green (Fresh)
    #  <= 5x interval => yellow (Lagging)
    #  >  5x interval => red (Stale)
    INTERVAL = 15
    LAGGING = 5 * INTERVAL

    now = datetime.now(timezone.utc)

    s = SessionLocal()
    try:
        latest = (
            s.query(
                Metric.miner_ip.label('ip'),
                func.max(Metric.timestamp).label('last_ts')
            ).group_by(Metric.miner_ip).subquery()
        )

        rows = (
            s.query(Metric)
            .join(latest, and_(Metric.miner_ip == latest.c.ip,
                               Metric.timestamp == latest.c.last_ts))
            .order_by(Metric.miner_ip.asc())
            .all()
        )

        # Best-effort model lookup in parallel
        models = {}
        ips = [m.miner_ip for m in rows]
        if ips:
            def _fetch(ip):
                try:
                    return ip, MinerClient(ip).fetch_normalized().get('model', '')
                except Exception:
                    return ip, ''
            with ThreadPoolExecutor(max_workers=min(8, len(ips))) as ex:
                for fut in as_completed([ex.submit(_fetch, ip) for ip in ips]):
                    ip, model = fut.result()
                    models[ip] = model

        out = []
        for m in rows:
            ts = m.timestamp
            # Ensure aware UTC for age computation
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = int((now - ts).total_seconds())

            if age <= 2 * INTERVAL:
                status = 'Active'
            elif age <= LAGGING:
                status = 'Lagging'
            else:
                status = 'Stale'

            out.append({
                'is_stale': age > LAGGING,
                'age_sec': age,
                'status': status,
                'model': models.get(m.miner_ip, ''),
                'ip': m.miner_ip,
                'last_seen': ts.isoformat().replace('+00:00', 'Z'),
            })
        return out
    finally:
        s.close()


@api_bp.get("/miners")
def miners():
    miners = get_miners()
    # Ensure a consistent response contract expected by miners.js
    return jsonify({"miners": miners})


@dash_bp.route('/')
def index():
    ip = request.args.get('ip')
    return render_template('dashboard.html', ip=ip)


@dash_bp.route('/miners')
def show_miners():
    return render_template('miners.html')


@dash_bp.route("/logs")
def logs_page():
    return render_template("logs.html")

