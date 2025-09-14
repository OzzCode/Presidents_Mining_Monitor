import ipaddress
import socket
import time
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import func, and_
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.db import SessionLocal, Metric, Event, ErrorEvent
from core.miner import MinerClient, MinerError
from config import MINER_IP_RANGE, API_MAX_LIMIT, POLL_INTERVAL
from datetime import datetime, timezone, timedelta
import logging

# tune these if needed
_PER_MINER_TIMEOUT = 4.0  # seconds for each miner fetch
_MAX_WORKERS = 16  # threads for concurrent fetches

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')
dash_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@api_bp.after_app_request
def api_cache_control(resp):
    # Only touch API responses
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, private"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp


@api_bp.route("/debug/peek")
def debug_peek():
    """Show the last metric per miner, plus age in minutes."""
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


@api_bp.route("/debug/tail")
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

@dash_bp.route("/dashboard/miners")
def discover_miners(timeout=1, workers=50, use_mdns=True, return_sources=False):
    """
    Scan the configured CIDR for TCP/4028 and optionally browse mDNS _cgminer._tcp.

    Args:
        timeout (int|float): socket timeout per probe in seconds
        workers (int): concurrent threads for TCP scan
        use_mdns (bool): whether to attempt Zeroconf discovery
        return_sources (bool): when True, return dict[ip] -> {"tcp","mdns","both"}

    Returns:
        list[str] if return_sources is False
        dict[str, str] if return_sources is True
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

    # TCP scan once using a single executor
    with ThreadPoolExecutor(max_workers=workers) as ex:
        tcp_hosts = {ip for ip in ex.map(scan, network.hosts()) if ip}

    mdns_hosts = set()
    if use_mdns:
        try:
            from zeroconf import Zeroconf, ServiceBrowser
            zeroconf = Zeroconf()
            services = []

            def on_service(zc, type_, name):
                info = zc.get_service_info(type_, name)
                if info:
                    for addr in info.addresses:
                        try:
                            services.append(socket.inet_ntoa(addr))
                        except OSError:
                            # ignore non-IPv4 addresses
                            pass

            ServiceBrowser(zeroconf, "_cgminer._tcp.local.", handlers=[on_service])
            time.sleep(2)
            zeroconf.close()
            mdns_hosts = set(services)
        except Exception:
            # zeroconf not installed or runtime error; ignore
            mdns_hosts = set()

    union = tcp_hosts | mdns_hosts
    if not return_sources:
        return sorted(union)

    sources = {}
    for ip in union:
        in_tcp = ip in tcp_hosts
        in_mdns = ip in mdns_hosts
        sources[ip] = "both" if (in_tcp and in_mdns) else ("tcp" if in_tcp else "mdns")
    return sources


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
        return ts.isoformat().replace("+00:00", "Z"), int(age_sec)
    finally:
        session.close()


def _normalize_since(value: str) -> datetime:
    """
    Convert an ISO8601 string to a naive UTC datetime (standard library only).
    - If input is naive: assume it's already UTC and return as-is (tzinfo=None)
    - If input is aware (Z or offset): convert to UTC and strip tzinfo
    Raises ValueError on parse errors or invalid type.
    """
    if not isinstance(value, str):
        raise ValueError("since must be a string")

    s = value.strip()
    # Accept trailing 'Z'
    if s.endswith("Z") or s.endswith("z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)
    except Exception as e:
        raise ValueError(f"Invalid ISO datetime: {value}") from e

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


@api_bp.route('/summary')
def summary():
    """Summarize current metrics and indicate a data source (live vs. DB fallback)."""
    ipf = request.args.get('ip')
    mdns_flag = request.args.get('mdns', 'true').lower() == 'true'

    if ipf:
        miners = [ipf]
        discovery_sources = {ipf: "manual"}
    else:
        discovery_sources = discover_miners(use_mdns=mdns_flag, return_sources=True)
        # Be resilient to patched/mocked discover_miners that return a list
        if isinstance(discovery_sources, list):
            miners = list(discovery_sources)
            discovery_sources = {ip: 'unknown' for ip in miners}
        else:
            miners = list(discovery_sources.keys())
    totals = {'power': 0.0, 'hash': 0.0, 'uptime': 0, 'temps': [], 'fans': []}
    data = []
    overall_srcs = set()

    # Prefetch latest DB metric per miner once to avoid per-thread queries
    prefetch = {}
    if miners:
        s_pref = SessionLocal()
        try:
            latest_subq = (
                s_pref.query(
                    Metric.miner_ip.label('ip'),
                    func.max(Metric.timestamp).label('last_ts')
                )
                .filter(Metric.miner_ip.in_(miners))
                .group_by(Metric.miner_ip)
                .subquery()
            )
            rows = (
                s_pref.query(Metric)
                .join(latest_subq, and_(Metric.miner_ip == latest_subq.c.ip,
                                        Metric.timestamp == latest_subq.c.last_ts))
                .all()
            )
            for m in rows:
                prefetch[m.miner_ip] = m
        except Exception:
            prefetch = {}
        finally:
            s_pref.close()

    # worker that returns (ip, payload, src) or (ip, None, None)
    def _fetch_one(ip: str):
        # 1) try live
        try:
            payload = MinerClient(ip).fetch_normalized()
            return ip, payload, 'live'
        except MinerError:
            pass
        except Exception:
            pass
        # 2) fallback: last prefetched DB metric
        last = prefetch.get(ip)
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

    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, max(len(miners), 1))) as ex:
        futures = {ex.submit(_fetch_one, ip): ip for ip in miners}
        for fut in as_completed(futures, timeout=None):
            ip = futures[fut]
            try:
                ip, payload, src = fut.result()
            except Exception:
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

            ts = payload.get('when') or datetime.now(timezone.utc).isoformat()
            data.append({
                'timestamp': ts,
                'ip': ip,
                'hash': payload.get('hashrate_ths', 0),
                'source': src,
                'discovery': discovery_sources.get(ip, 'unknown')
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
        'last_updated': datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    })


@api_bp.route('/miners/summary')
def miners_summary():
    """
    Query params:
      window_min (int, default 30) — averaging window length
      active_only (bool, default true) — filter miners whose last row is fresh
      fresh_within (int, default 30) — freshness window in minutes
      ips (csv, optional) — restrict to a list of IPs
      since (ISO, optional) — overrides window_min if set
    Response: [{ ip, last_seen, hashrate_ths, power_w, avg_temp_c, avg_fan_rpm }]
    """
    # Parse params safely
    try:
        window_min = int(request.args.get('window_min', 30))
    except Exception:
        window_min = 30
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    try:
        fresh_within = int(request.args.get('fresh_within', 30))
    except Exception:
        fresh_within = 30
    ips_param = request.args.get('ips')
    since_param = request.args.get('since')

    now = _naive_utc_now()
    if since_param:
        try:
            since_dt = _normalize_since(since_param)
        except Exception:
            since_dt = now - timedelta(minutes=window_min)
    else:
        since_dt = now - timedelta(minutes=window_min)
    cutoff = now - timedelta(minutes=fresh_within)
    ip_list = [i.strip() for i in ips_param.split(',') if i.strip()] if ips_param else None

    s = SessionLocal()
    try:
        # Aggregate per miner over the window
        q = (
            s.query(
                Metric.miner_ip.label('ip'),
                func.max(Metric.timestamp).label('last_ts'),
                func.avg(Metric.hashrate_ths).label('hashrate_ths'),
                func.avg(Metric.power_w).label('power_w'),
                func.avg(Metric.avg_temp_c).label('avg_temp_c'),
                func.avg(Metric.avg_fan_rpm).label('avg_fan_rpm'),
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
                "hashrate_ths": float(r.hashrate_ths or 0.0),
                "power_w": float(r.power_w or 0.0),
                "avg_temp_c": float(r.avg_temp_c or 0.0),
                "avg_fan_rpm": float(r.avg_fan_rpm or 0.0),
            })
        return jsonify(out)
    finally:
        s.close()


@api_bp.route('/miners/current')
def miners_current():
    """
    Returns the latest row per miner, optionally filtering by freshness.

    Query params:
      - active_only: 'true'/'false' (default 'true')
      - fresh_within: minutes (int, default 30)
      - ips: optional CSV to restrict to a set of IPs
    """
    # Parse params robustly
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    try:
        fresh_within = int(request.args.get('fresh_within', 30))
    except Exception:
        fresh_within = 30

    ips_param = request.args.get('ips')
    ip_list = [i.strip() for i in ips_param.split(',') if i.strip()] if ips_param else None

    cutoff = _naive_utc_now() - timedelta(minutes=fresh_within)

    s = SessionLocal()
    try:
        latest = (
            s.query(
                Metric.miner_ip.label('ip'),
                func.max(Metric.timestamp).label('last_ts')
            )
            .group_by(Metric.miner_ip)
            .subquery()
        )

        q = (
            s.query(Metric)
            .join(latest, and_(Metric.miner_ip == latest.c.ip,
                               Metric.timestamp == latest.c.last_ts))
        )

        if ip_list:
            q = q.filter(Metric.miner_ip.in_(ip_list))
        if active_only:
            q = q.filter(Metric.timestamp >= cutoff)

        rows = q.order_by(Metric.miner_ip.asc()).all()

        # Attempt to enrich with model by fetching live model per IP (best-effort)
        models = {}
        try:
            ips = [m.miner_ip for m in rows]
            if ips:
                def _fetch(ip):
                    try:
                        return ip, MinerClient(ip).fetch_normalized().get('model', '')
                    except Exception:
                        return ip, ''
                with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(ips))) as ex:
                    for fut in as_completed([ex.submit(_fetch, ip) for ip in ips]):
                        ip, model = fut.result()
                        models[ip] = model
        except Exception:
            models = {}

        return jsonify([{
            "ip": m.miner_ip,
            "last_seen": m.timestamp.isoformat() + "Z",
            "hashrate_ths": float(m.hashrate_ths or 0.0),
            "power_w": float(m.power_w or 0.0),
            "avg_temp_c": float(m.avg_temp_c or 0.0),
            "avg_fan_rpm": float(m.avg_fan_rpm or 0.0),
            "model": models.get(m.miner_ip, ''),
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

    # enforce a hard upper bound for safety
    limit = max(1, min(limit, API_MAX_LIMIT))

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
                dt = _normalize_since(since)
            except Exception:
                dt = None
            if dt:
                q = q.filter(Metric.timestamp >= dt)

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

        out = [
            {
                "timestamp": (m.timestamp.isoformat() + "Z"),  # return ISO+Z
                "ip": m.miner_ip,
                "power_w": m.power_w,
                "hashrate_ths": m.hashrate_ths,
                "avg_temp_c": m.avg_temp_c,
                "avg_fan_rpm": m.avg_fan_rpm,
            }
            for m in rows
        ]

        # For single-miner queries, best-effort include model once
        if ip_filter:
            try:
                model = MinerClient(ip_filter).fetch_normalized().get('model', '')
            except Exception:
                model = ''
            if model:
                for rec in out:
                    rec['model'] = model
        return jsonify(out)
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
        try:
            dt = _normalize_since(since)
            q = q.filter(ErrorEvent.created_at >= dt)
        except Exception:
            pass
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
            "timestamp": e.timestamp.isoformat() + "Z",
            "miner_ip": e.miner_ip,
            "level": e.level,
            "source": e.source,
            "message": e.message
        } for e in rows])
    finally:
        s.close()


@api_bp.post('/miners/<ip>/pools')
def add_pool(ip):
    """Add or replace mining pools for the specified miner.

    POST behaviors:
      - Single pool body: {stratum, username, password?, overwrite?}
        If overwrite is true (default), existing pools will be fetched and removed before adding this one.
        If overwrite is false, this single pool will be appended.
      - Multiple pools body: {pools: [{stratum, username, password?}, ...]}
        Always treated as overwrite unless query param append=true is set.
    """
    data = request.get_json(silent=True) or {}
    append_qs = request.args.get("append", "false").lower() in ("1", "true", "yes")
    overwrite_flag = data.get("overwrite")
    overwrite = (not append_qs) if overwrite_flag is None else bool(overwrite_flag)

    # Normalize to a list of pools
    pools_body = data.get("pools")
    ops_log = []

    def _norm_pool(p):
        return {
            "stratum": (p.get("stratum") or p.get("url") or "").strip(),
            "username": (p.get("username") or p.get("user") or "").strip(),
            "password": p.get("password") or "",
        }

    if isinstance(pools_body, list) and pools_body:
        pools_to_set = [_norm_pool(p) for p in pools_body]
    else:
        pools_to_set = [_norm_pool(data)]

    # Basic validation of at least first pool
    for p in pools_to_set:
        if not p["stratum"] or not p["username"]:
            return jsonify({"ok": False, "error": "Each pool requires stratum and username"}), 400

    client = MinerClient(ip)

    prev_pools = None
    final_pools = None

    try:
        # If overwrite requested, remove existing pools first
        if overwrite:
            try:
                prev_pools = client.get_pools()
            except Exception as e:
                prev_pools = {"error": f"failed to fetch pools: {e}"}
            # attempt to list and remove by indices
            try:
                ids = client.list_pool_ids()
            except Exception as e:
                ids = []
                ops_log.append({"step": "list_pool_ids", "ok": False, "error": str(e)})
            for pid in sorted(ids, reverse=True):
                try:
                    r = client.remove_pool(pid)
                    ops_log.append({"step": "remove_pool", "id": pid, "ok": True, "result": r})
                except Exception as e:
                    ops_log.append({"step": "remove_pool", "id": pid, "ok": False, "error": str(e)})

        # Add the requested pools
        add_results = []
        for p in pools_to_set:
            r = client.add_pool(p["stratum"], p["username"], p.get("password") or "")
            add_results.append({"url": p["stratum"], "user": p["username"], "ok": True, "result": r})
        ops_log.append({"step": "add_pools", "count": len(add_results), "details": add_results})

        # Set priorities in declared order if more than one pool
        if len(pools_to_set) > 1:
            try:
                pr = client.pool_priority(list(range(len(pools_to_set))))
                ops_log.append({"step": "pool_priority", "ok": True, "result": pr})
            except Exception as e:
                ops_log.append({"step": "pool_priority", "ok": False, "error": str(e)})

        try:
            final_pools = client.get_pools()
        except Exception:
            final_pools = None

        return jsonify({
            "ok": True,
            "overwrite": overwrite,
            "previous": prev_pools,
            "operations": ops_log,
            "pools": final_pools,
        }), 200

    except MinerError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("add/replace pool(s) failed for %s", ip)
        return jsonify({"ok": False, "error": "Failed to update pools", "detail": str(e)}), 500


@api_bp.put('/miners/<ip>/pools')
def replace_pools(ip):
    """Replace all pools with the provided list.
    Body: {pools:[{stratum,username,password?}, ...]}
    """
    data = request.get_json(silent=True) or {}
    pools_body = data.get("pools")
    if not isinstance(pools_body, list) or not pools_body:
        return jsonify({"ok": False, "error": "Body must include non-empty 'pools' array"}), 400

    # Reuse POST handler with forced overwrite
    with current_app.test_request_context():
        request.args = request.args.copy()
    # Construct a fake request-like object by calling the function directly with prepared data
    # Instead, inline logic to avoid context mutation

    client = MinerClient(ip)
    ops_log = []

    def _norm_pool(p):
        return {
            "stratum": (p.get("stratum") or p.get("url") or "").strip(),
            "username": (p.get("username") or p.get("user") or "").strip(),
            "password": p.get("password") or "",
        }

    pools_to_set = [_norm_pool(p) for p in pools_body]
    for p in pools_to_set:
        if not p["stratum"] or not p["username"]:
            return jsonify({"ok": False, "error": "Each pool requires stratum and username"}), 400

    try:
        prev = None
        try:
            prev = client.get_pools()
        except Exception:
            prev = None

        # remove existing
        try:
            ids = client.list_pool_ids()
        except Exception as e:
            ids = []
            ops_log.append({"step": "list_pool_ids", "ok": False, "error": str(e)})
        for pid in sorted(ids, reverse=True):
            try:
                r = client.remove_pool(pid)
                ops_log.append({"step": "remove_pool", "id": pid, "ok": True, "result": r})
            except Exception as e:
                ops_log.append({"step": "remove_pool", "id": pid, "ok": False, "error": str(e)})

        add_results = []
        for p in pools_to_set:
            r = client.add_pool(p["stratum"], p["username"], p.get("password") or "")
            add_results.append({"url": p["stratum"], "user": p["username"], "ok": True, "result": r})
        ops_log.append({"step": "add_pools", "count": len(add_results), "details": add_results})

        if len(pools_to_set) > 1:
            try:
                pr = client.pool_priority(list(range(len(pools_to_set))))
                ops_log.append({"step": "pool_priority", "ok": True, "result": pr})
            except Exception as e:
                ops_log.append({"step": "pool_priority", "ok": False, "error": str(e)})

        try:
            final = client.get_pools()
        except Exception:
            final = None

        return jsonify({"ok": True, "previous": prev, "operations": ops_log, "pools": final}), 200
    except MinerError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("replace_pools failed for %s", ip)
        return jsonify({"ok": False, "error": "Failed to replace pools", "detail": str(e)}), 500


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


# --- Braiins OS (BOS) REST helpers & endpoints ---
try:
    from core.bos import BosRest
except Exception:
    BosRest = None  # optional, endpoints will guard


def _bos_from_request(ip: str):
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or data.get("user") or "").strip()
    password = data.get("password") or ""
    try:
        timeout = int(data.get("timeout", 5))
    except Exception:
        timeout = 5
    if not BosRest:
        raise RuntimeError("BOS client not available on server")
    if not username:
        raise ValueError("username is required")
    return BosRest(ip, username, password, timeout=timeout)


@api_bp.post('/bos/<ip>/details')
def bos_details(ip):
    """Fetch BOS miner details. Body: {username, password?, timeout?}"""
    try:
        bos = _bos_from_request(ip)
        payload = bos.details()
        return jsonify({"ok": True, "details": payload}), 200
    except Exception as e:
        logger.exception("BOS details failed for %s", ip)
        return jsonify({"ok": False, "error": str(e)}), 400


@api_bp.post('/bos/<ip>/pause')
def bos_pause(ip):
    """Pause the miner via BOS. Body: {username, password?, timeout?}"""
    try:
        bos = _bos_from_request(ip)
        res = bos.pause()
        return jsonify({"ok": True, "result": res}), 200
    except Exception as e:
        logger.exception("BOS pause failed for %s", ip)
        return jsonify({"ok": False, "error": str(e)}), 400


@api_bp.put('/bos/<ip>/power-target')
def bos_power_target(ip):
    """Set BOS power target. Body: {username, password?, watt, timeout?}"""
    data = request.get_json(silent=True) or {}
    try:
        watt = int(data.get('watt'))
    except Exception:
        return jsonify({"ok": False, "error": "watt (int) is required"}), 400
    try:
        bos = _bos_from_request(ip)
        res = bos.set_power_target(watt)
        return jsonify({"ok": True, "result": res}), 200
    except Exception as e:
        logger.exception("BOS set power target failed for %s", ip)
        return jsonify({"ok": False, "error": str(e)}), 400
