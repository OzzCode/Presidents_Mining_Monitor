import ipaddress
import socket
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import func, and_
from concurrent.futures import ThreadPoolExecutor, as_completed
from dateutil import parser
from core.db import SessionLocal, Metric, Event, ErrorEvent
from core.miner import MinerClient, MinerError
from config import MINER_IP_RANGE, API_MAX_LIMIT, POLL_INTERVAL
from datetime import datetime, timezone, timedelta
import logging
from flask import current_app

# tune these if needed
_PER_MINER_TIMEOUT = 4.0  # seconds for each miner fetch
_MAX_WORKERS = 16  # threads for concurrent fetches

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.after_app_request
def api_cache_control(resp):
    # Only touch API responses
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp


@api_bp.route("/api/debug/peek")
def debug_peek():
    """Show last metric per miner, plus age in minutes."""
    fresh_within = int(request.args.get("fresh_within", 30))
    cutoff = datetime.utcnow() - timedelta(minutes=fresh_within)

    s = SessionLocal()
    try:
        latest = (
            s.query(
                Metric.miner_ip.label('ip'),
                func.max(Metric.timestamp).label('last_ts')
            ).group_by(Metric.miner_ip).subquery()
        )
        q = (s.query(Metric)
             .join(latest, and_(Metric.miner_ip == latest.c.ip,
                                Metric.timestamp == latest.c.last_ts))
             .order_by(Metric.miner_ip.asc()))
        rows = q.all()

        out = []
        for m in rows:
            age_min = (datetime.utcnow() - m.timestamp).total_seconds() / 60.0
            out.append({
                "ip": m.miner_ip,
                "last_seen": m.timestamp.isoformat() + "Z",
                "age_min": round(age_min, 1),
                "active@fresh_min": fresh_within,
                "is_active": m.timestamp >= cutoff,
                "hashrate_ths": float(m.hashrate_ths or 0.0),
                "power_w": float(m.power_w or 0.0),
            })
        return jsonify(out)
    finally:
        s.close()


@api_bp.route("/api/debug/tail")
def debug_tail():
    """Return last N metrics (optionally for one miner)."""
    ip = request.args.get("ip")
    n = int(request.args.get("n", 50))
    s = SessionLocal()
    try:
        q = s.query(Metric)
        if ip:
            q = q.filter(Metric.miner_ip == ip)
        rows = (q.order_by(Metric.timestamp.desc()).limit(n).all())
        rows.reverse()
        return jsonify([{
            "timestamp": r.timestamp.isoformat() + "Z",
            "ip": r.miner_ip, "hashrate_ths": r.hashrate_ths,
            "power_w": r.power_w, "temp_c": r.avg_temp_c, "fan_rpm": r.avg_fan_rpm
        } for r in rows])
    finally:
        s.close()


def discover_miners(timeout=1, workers=50):
    """
    Scan the configured CIDR for TCP/4028 and also browse mDNS _cgminer._tcp.
    """
    network = ipaddress.ip_network(MINER_IP_RANGE)

    # noinspection PyBroadException
    def scan(ip):
        with socket.socket() as s:
            s.settimeout(timeout)
            try:
                s.connect((str(ip), 4028))
                return str(ip)
            except Exception:
                return None

    # hosts = [ip for ip in ThreadPoolExecutor(workers).map(scan, network.hosts()) if ip]
    # zeroconf = Zeroconf()
    # services = []
    #
    # def on_service(zc, type_, name):
    #     info = zc.get_service_info(type_, name)
    #     if info:
    #         for addr in info.addresses:
    #             services.append(socket.inet_ntoa(addr))
    #
    # ServiceBrowser(zeroconf, "_cgminer._tcp.local.", handlers=[on_service])
    # time.sleep(2)
    # zeroconf.close()

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return sorted(set([ip for ip in ex.map(scan, network.hosts()) if ip]))

    # return sorted(set(hosts + services))


def _last_seen_for_ip(ip: str):
    session = SessionLocal()
    try:
        m = (session.query(Metric)
             .filter(Metric.miner_ip == ip)
             .order_by(Metric.timestamp.desc())
             .first())
        if not m:
            return None, None
        ts = m.timestamp
        # ensure aware -> UTC
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_sec = (datetime.now(timezone.utc) - ts).total_seconds()
        return ts.isoformat(), int(age_sec)
    finally:
        session.close()


def _normalize_since(value: str) -> datetime:
    """
    Convert an ISO8601 string to a naive UTC datetime, per tests/plan expectations.
    - If input is naive: assume it's already UTC and return as-is (tzinfo=None)
    - If input is aware (Z or offset): convert to UTC and strip tzinfo
    Raises ValueError on parse errors or invalid type.
    """
    if not isinstance(value, str):
        raise ValueError("since must be a string")
    dt = parser.isoparse(value)
    if dt.tzinfo is None:
        # treat naive as UTC already
        return dt
    # convert to UTC and strip tzinfo
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _naive_utc_now():
    return datetime.utcnow()


def _to_naive_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        # assume it's already UTC-naive
        return dt
    # convert aware → UTC → strip tzinfo
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


# --------------------------
# Normalization helper
# --------------------------
# noinspection PyBroadException
def log_event(level: str, message: str, miner_ip: str | None = None, source: str = 'app'):
    """Write a single event row; errors here are swallowed so logging never breaks requests."""
    s = None
    try:
        s = SessionLocal()
        s.add(Event(level=level.upper(), miner_ip=miner_ip, source=source, message=message))
        s.commit()
    except Exception:
        try:
            s and s.rollback()
        except Exception:
            pass
    finally:
        try:
            s and s.close()
        except Exception:
            pass


def _read_summary_fields(ip: str):
    """
    Query a miner and normalize cgminer/BMminer SUMMARY/STATS into a consistent
    shape for our API: power, hash_ths, elapsed, temps[], fans[], when.
    """
    client = MinerClient(ip)

    # --- SUMMARY (hashrate & uptime) ---
    s = {}
    try:
        summary = client.get_summary()
        if isinstance(summary, dict) and "SUMMARY" in summary and summary["SUMMARY"]:
            s = summary["SUMMARY"][0]
        else:
            s = summary if isinstance(summary, dict) else {}
    except Exception:
        return {"power": 0.0, "hash_ths": 0.0, "elapsed": 0, "temps": [], "fans": [], "when": ""}

    try:
        mhs_5s = float(s.get("MHS 5s", 0.0))
    except Exception:
        mhs_5s = 0.0
    try:
        elapsed = int(s.get("Elapsed", 0))
    except Exception:
        elapsed = 0

    # --- STATS (temps/fans) ---
    temps, fans = [], []
    try:
        stats = client.get_stats()
        if isinstance(stats, dict) and "STATS" in stats and stats["STATS"]:
            st0 = stats["STATS"][0]
            for k, v in st0.items():
                if isinstance(v, (int, float)):
                    lk = str(k).lower()
                    if lk.startswith("temp"):
                        temps.append(float(v))
                    if lk.startswith("fan"):
                        fans.append(float(v))
    except Exception:
        pass

    when = s.get("When") or s.get("STIME") or ""

    try:
        power = float(s.get("Power", 0.0) or 0.0)
    except Exception:
        power = 0.0

    return {
        "power": power,
        "hash_ths": round(mhs_5s / 1e6, 3),  # MHS -> TH/s
        "elapsed": elapsed,
        "temps": temps,
        "fans": fans,
        "when": when
    }


@api_bp.route('/summary')
def summary():
    """Summarize current metrics and indicate a data source (live vs. DB fallback)."""
    ipf = request.args.get('ip')
    miners = [ipf] if ipf else discover_miners()

    totals = {'power': 0.0, 'hash': 0.0, 'uptime': 0, 'temps': [], 'fans': []}
    data = []
    overall_srcs = set()

    # worker that returns (ip, payload, src) or (ip, None, None)
    def _fetch_one(ip: str):
        # 1) try live
        try:
            payload = MinerClient(ip).fetch_normalized()
            return ip, payload, 'live'
        except MinerError:
            # logger.warning("summary_live_fetch_failed", extra={"component": "api", "miner_ip": ip})
            pass
        except Exception:
            # logger.warning(f"summary_live_exception: {e}", extra={"component": "api", "miner_ip": ip})
            pass

        # 2) fallback: last DB metric
        s = SessionLocal()
        try:
            last = (
                s.query(Metric)
                .filter(Metric.miner_ip == ip)
                .order_by(Metric.timestamp.desc())
                .first()
            )
            if last:
                return ip, {
                    'hashrate_ths': last.hashrate_ths,
                    'elapsed_s': last.elapsed_s,
                    'avg_temp_c': last.avg_temp_c,
                    'avg_fan_rpm': last.avg_fan_rpm,
                    'power_w': last.power_w,
                    'when': last.timestamp.isoformat() + 'Z',
                }, 'db_fallback'
            else:
                return ip, None, None
        finally:
            s.close()

    # fetch all miners concurrently with hard per-future timeout
    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, max(len(miners), 1))) as ex:
        futures = {ex.submit(_fetch_one, ip): ip for ip in miners}
        for fut in as_completed(futures, timeout=None):
            ip = futures[fut]
            try:
                ip, payload, src = fut.result(timeout=_PER_MINER_TIMEOUT)
            except Exception as e:
                # includes per-future timeout or worker exception
                # logger.warning(f"summary_future_failed: {e}", extra={"component":"api","miner_ip":ip})
                continue

            if not payload:
                continue

            overall_srcs.add(src)
            totals['power'] += float(payload.get('power_w', 0) or 0)
            totals['hash'] += float(payload.get('hashrate_ths', 0) or 0)
            totals['uptime'] = max(totals['uptime'], int(payload.get('elapsed_s', 0) or 0))

            avg_temp_c = payload.get('avg_temp_c')
            avg_fan_rpm = payload.get('avg_fan_rpm')
            if avg_temp_c:
                totals['temps'].append(float(avg_temp_c))
            if avg_fan_rpm:
                totals['fans'].append(float(avg_fan_rpm))

            ts = payload.get('when')
            if not ts:
                # fallback to now (UTC) if miner didn’t provide a 'when
                ts = datetime.now(timezone.utc).isoformat()

            data.append({
                'timestamp': ts,
                'ip': ip,
                'hash': payload.get('hashrate_ths', 0),
                'source': src
            })

    overall_source = (
        'live' if overall_srcs == {'live'} else
        ('db_fallback' if overall_srcs == {'db_fallback'}
         else ('mixed' if overall_srcs else 'none'))
    )

    return jsonify({
        'source': overall_source,
        'total_power': round(totals['power'], 1),
        'total_hashrate': round(totals['hash'], 3),
        'total_uptime': totals['uptime'],
        'avg_temp': round(sum(totals['temps']) / len(totals['temps']), 1) if totals['temps'] else 0,
        'avg_fan_speed': round(sum(totals['fans']) / len(totals['fans']), 0) if totals['fans'] else 0,
        'total_workers': len(miners),
        'log': data,
        'last_updated': datetime.now(timezone.utc).isoformat()
    })


# noinspection PyBroadException
# @api_bp.route('/miners')
# returns one row per miner with averages over a window
@api_bp.route('/miners/summary')
def miners_summary():
    """
    Query params:
      window_min (int, default 30) — averaging window length
      active_only (bool, default true) — filter miners whose last row is fresh
      fresh_within (int, default 30) — freshness window in minutes
      ips (csv, optional) — restrict to a list of IPs
      since (ISO, optional) — overrides window_min if set
    Response: [{ ip, last_seen, avg_ths, avg_power_w }]
    """
    window_min = int(request.args.get('window_min', 30))
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    fresh_within = int(request.args.get('fresh_within', 30))
    ips_param = request.args.get('ips')
    since_param = request.args.get('since')

    now = _naive_utc_now()
    if since_param:
        try:
            # if you already import dateutil.parser you can parse ISO here;
            # otherwise, treat since_param as ISO UTC
            from dateutil import parser
            since_dt = _to_naive_utc(parser.isoparse(since_param))
        except Exception:
            since_dt = now - timedelta(minutes=window_min)
    else:
        since_dt = now - timedelta(minutes=window_min)

    cutoff = now - timedelta(minutes=fresh_within)
    ip_list = [i.strip() for i in ips_param.split(',')] if ips_param else None

    s = SessionLocal()
    try:
        q = (
            s.query(
                Metric.miner_ip.label('ip'),
                func.max(Metric.timestamp).label('last_ts'),
                func.avg(Metric.hashrate_ths).label('avg_ths'),
                func.avg(Metric.power_w).label('avg_power_w'),
            )
            .filter(Metric.timestamp >= since_dt)
        )
        if ip_list:
            q = q.filter(Metric.miner_ip.in_(ip_list))

        q = q.group_by(Metric.miner_ip)
        if active_only:
            q = q.having(func.max(Metric.timestamp) >= cutoff)

        q = q.order_by(func.max(Metric.timestamp).desc())

        rows = q.all()
        out = []
        for r in rows:
            last_ts = r.last_ts
            out.append({
                "ip": r.ip,
                "last_seen": (last_ts.isoformat() + "Z") if last_ts else "",
                "avg_ths": float(r.avg_ths or 0.0),
                "avg_power_w": float(r.avg_power_w or 0.0),
            })
        return jsonify(out)
    finally:
        s.close()


@api_bp.route('/miners/current')
def miners_current():
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    fresh_within = int(request.args.get('fresh_within', 30))
    ips_param = request.args.get('ips')
    ip_list = [i.strip() for i in ips_param.split(',')] if ips_param else None

    cutoff = _naive_utc_now() - timedelta(minutes=fresh_within)

    s = SessionLocal()
    try:
        latest = (
            s.query(
                Metric.miner_ip.label('ip'),
                func.max(Metric.timestamp).label('last_ts')
            ).group_by(Metric.miner_ip).subquery()
        )

        q = (s.query(Metric)
             .join(latest, and_(Metric.miner_ip == latest.c.ip,
                                Metric.timestamp == latest.c.last_ts)))

        if ip_list:
            q = q.filter(Metric.miner_ip.in_(ip_list))
        if active_only:
            q = q.filter(Metric.timestamp >= cutoff)

        rows = q.order_by(Metric.miner_ip.asc()).all()
        return jsonify([{
            "ip": m.miner_ip,
            "last_seen": m.timestamp.isoformat() + "Z",
            "hashrate_ths": float(m.hashrate_ths or 0.0),
            "power_w": float(m.power_w or 0.0),
            "avg_temp_c": float(m.avg_temp_c or 0.0),
            "avg_fan_rpm": float(m.avg_fan_rpm or 0.0),
        } for m in rows])
    finally:
        s.close()


@api_bp.route("/metrics")
def metrics():
    ip_filter = request.args.get("ip")
    ips_param = request.args.get("ips")
    since = request.args.get("since")
    limit = int(request.args.get("limit", 500))
    active_only = request.args.get("active_only", "false").lower() == "true"
    fresh_within = int(request.args.get("fresh_within", 30))

    s = SessionLocal()
    try:
        q = s.query(Metric)

        if ip_filter:
            q = q.filter(Metric.miner_ip == ip_filter)

        if ips_param and not ip_filter:
            ip_list = [i.strip() for i in ips_param.split(",") if i.strip()]
            if ip_list:
                q = q.filter(Metric.miner_ip.in_(ip_list))

        if since:
            try:
                dt = parser.isoparse(since)
            except Exception:
                dt = None
            if dt:
                q = q.filter(Metric.timestamp >= _to_naive_utc(dt))

        if active_only:
            cutoff = _naive_utc_now() - timedelta(minutes=fresh_within)
            latest_subq = (
                s.query(
                    Metric.miner_ip.label("ip"),
                    func.max(Metric.timestamp).label("last_ts"),
                )
                .group_by(Metric.miner_ip)
                .subquery()
            )
            active_ips = [
                r.ip
                for r in s.query(latest_subq)
                .filter(latest_subq.c.last_ts >= cutoff)
                .all()
            ]
            if not active_ips:
                return jsonify([])
            q = q.filter(Metric.miner_ip.in_(active_ips))

        rows = q.order_by(Metric.timestamp.asc()).limit(limit).all()
        return jsonify([
            {
                "timestamp": (m.timestamp.isoformat() + "Z"),  # return ISO+Z
                "ip": m.miner_ip,
                "power_w": m.power_w,
                "hashrate_ths": m.hashrate_ths,
                "avg_temp_c": m.avg_temp_c,
                "avg_fan_rpm": m.avg_fan_rpm,
            }
            for m in rows
        ])
    finally:
        s.close()


@api_bp.route("/error-logs")
def error_logs():
    level = request.args.get("level")
    miner_ip = request.args.get("ip")
    since = request.args.get("since")
    limit = int(request.args.get("limit", 200))

    session = SessionLocal()
    q = session.query(ErrorEvent)

    if level: q = q.filter(ErrorEvent.level == level.upper())
    if miner_ip: q = q.filter(ErrorEvent.miner_ip == miner_ip)
    if since:
        dt = parser.isoparse(since)
        if dt.tzinfo: dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        q = q.filter(ErrorEvent.created_at >= dt)
    rows = q.order_by(ErrorEvent.created_at.desc()).limit(limit).all()
    out = [{
        "id": r.id,
        "created_at": r.created_at.isoformat() + "Z",
        "level": r.level,
        "component": r.component,
        "miner_ip": r.miner_ip,
        "message": r.message,
        "context": r.context,
    } for r in rows]

    session.close()

    return jsonify(out)


@api_bp.route("/events")
def events():
    s = SessionLocal()
    try:
        rows = (s.query(Event).order_by(Event.timestamp.desc()).limit(500).all())
        return jsonify([{
            "timestamp": e.timestamp.isoformat(),
            "miner_ip": e.miner_ip,
            "level": e.level,
            "source": e.source,
            "message": e.message
        } for e in rows])
    finally:
        s.close()


@api_bp.route('/debug/routes')
def debug_routes():
    rules = []
    for r in current_app.url_map.iter_rules():
        rules.append({
            "rule": str(r),
            "methods": sorted(list(r.methods - {'HEAD', 'OPTIONS'})),
            "endpoint": r.endpoint
        })
    # sort by rule for readability
    rules.sort(key=lambda x: x["rule"])
    return jsonify(rules)
