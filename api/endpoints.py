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
def discover_miners(timeout=1, workers=50, use_mdns=True, return_sources=False, cidrs=None):
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
    # Determine networks to scan
    networks = []
    try:
        if cidrs:
            items = cidrs if isinstance(cidrs, (list, tuple)) else [c.strip() for c in str(cidrs).split(',') if
                                                                    c.strip()]
            for c in items:
                try:
                    networks.append(ipaddress.ip_network(c))
                except Exception:
                    continue
        if not networks:
            networks = [ipaddress.ip_network(MINER_IP_RANGE)]
    except Exception:
        networks = [ipaddress.ip_network(MINER_IP_RANGE)]

    # noinspection PyBroadException
    def scan(ip):
        with socket.socket() as s:
            s.settimeout(timeout)
            try:
                s.connect((str(ip), 4028))
                return str(ip)
            except Exception:
                return None

    # TCP scan once using a single executor across all networks
    hosts = []
    for net in networks:
        try:
            hosts.extend(list(net.hosts()))
        except Exception:
            continue
    with ThreadPoolExecutor(max_workers=workers) as ex:
        tcp_hosts = {ip for ip in ex.map(scan, hosts) if ip}

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
      - enrich_model: 'true'/'false' (default 'false') to fetch live model via MinerClient.
                       When false, this endpoint avoids network calls and reads model from DB if present.
    """
    # Parse params robustly
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    try:
        fresh_within = int(request.args.get('fresh_within', 30))
    except Exception:
        fresh_within = 30

    ips_param = request.args.get('ips')
    ip_list = [i.strip() for i in ips_param.split(',') if i.strip()] if ips_param else None
    enrich_model = request.args.get('enrich_model', 'false').lower() == 'true'

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

        # Prefer DB-sourced model if available to avoid live network calls.
        models: dict[str, str] = {}
        try:
            ips = [m.miner_ip for m in rows]
            if ips:
                from core.db import Miner  # local import to avoid circulars at module import
                miner_rows = s.query(Miner).filter(Miner.miner_ip.in_(ips)).all()
                models.update({mr.miner_ip: (mr.model or '') for mr in miner_rows})
        except Exception:
            pass

        # Optional live enrichment if explicitly requested
        if enrich_model:
            try:
                ips = [m.miner_ip for m in rows]
                if ips:
                    def _fetch(ip):
                        try:
                            return ip, MinerClient(ip).fetch_normalized().get('model', '')
                        except Exception:
                            return ip, models.get(ip, '')

                    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, max(len(ips), 1))) as ex:
                        for fut in as_completed([ex.submit(_fetch, ip) for ip in ips]):
                            ip, model = fut.result()
                            if model:
                                models[ip] = model
            except Exception:
                pass

        payload = [{
            "ip": m.miner_ip,
            "last_seen": m.timestamp.isoformat() + "Z",
            "hashrate_ths": float(m.hashrate_ths or 0.0),
            "power_w": float(m.power_w or 0.0),
            "avg_temp_c": float(m.avg_temp_c or 0.0),
            "avg_fan_rpm": float(m.avg_fan_rpm or 0.0),
            "model": models.get(m.miner_ip, ''),
        } for m in rows]

        resp = jsonify(payload)
        try:
            resp = api_cache_control(resp)
        except Exception:
            pass
        return resp
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
    enrich_model = request.args.get('enrich_model', 'false').lower() == 'true'

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
            # Try DB first to avoid live calls
            model = ''
            try:
                from core.db import Miner
                mrow = s.query(Miner).filter(Miner.miner_ip == ip_filter).first()
                if mrow and mrow.model:
                    model = mrow.model
            except Exception:
                model = ''
            # Optional live enrichment
            if enrich_model and not model:
                try:
                    model = MinerClient(ip_filter).fetch_normalized().get('model', '')
                except Exception:
                    model = ''
            if model:
                for rec in out:
                    rec['model'] = model
        resp = jsonify(out)
        try:
            resp = api_cache_control(resp)
        except Exception:
            pass
        return resp
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

    # Treat empty or 'ALL' (any case) as no level filter
    if level:
        lvl = level.strip().upper()
        if lvl and lvl != 'ALL' and lvl != 'ANY':
            q = q.filter(ErrorEvent.level == lvl)
    if miner_ip:
        q = q.filter(ErrorEvent.miner_ip == miner_ip)
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


@api_bp.get('/miners/<ip>/pools')
def get_pools_for_miner(ip):
    """Return current mining pools for the specified miner.

    Response shape:
      { ok: true, pools: [ {id, url, user, status, prio, stratum_active}...], raw: <miner response> }
    """
    try:
        client = MinerClient(ip)
        resp = client.get_pools() or {}
        pools = resp.get("POOLS") or resp.get("pools") or []
        norm = []
        for p in pools if isinstance(pools, list) else []:
            # id/index across variants
            pid = None
            for k in ("POOL", "Index", "POOL#", "ID", "id"):
                if k in p:
                    try:
                        pid = int(p[k])
                        break
                    except Exception:
                        continue
            # url/user/status/priority across variants
            url = p.get("URL") or p.get("Url") or p.get("Stratum URL") or p.get("Stratum") or ""
            user = p.get("User") or p.get("USER") or p.get("Username") or p.get("user") or ""
            status = p.get("Status") or p.get("STATUS") or p.get("status") or ""
            prio = p.get("Priority") or p.get("Prio") or p.get("PRIO") or p.get("priority")
            # detect stratum active flags commonly used
            sa = p.get("Stratum Active")
            if sa is None:
                sa = p.get("StratumActive")
            if sa is None:
                sa = p.get("Stratum") if isinstance(p.get("Stratum"), bool) else None
            # normalize boolean if present
            if isinstance(sa, str):
                sa = sa.strip().lower() in ("1", "true", "yes", "y")

            # share stats
            def _num(v):
                try:
                    if v is None or v == "":
                        return None
                    return int(float(v))
                except Exception:
                    return None

            acc = _num(p.get("Accepted") or p.get("ACCEPTED") or p.get("accepted")) or 0
            rej = _num(p.get("Rejected") or p.get("REJECTED") or p.get("rejected")) or 0
            stl = _num(p.get("Stale") or p.get("STALE") or p.get("stale")) or 0
            total_shares = acc + rej + stl
            reject_percent = (rej / total_shares * 100.0) if total_shares > 0 else 0.0
            norm.append({
                "id": pid,
                "url": url,
                "user": user,
                "status": status,
                "prio": prio,
                "stratum_active": sa,
                "accepted": acc,
                "rejected": rej,
                "stale": stl,
                "reject_percent": round(reject_percent, 2),
            })
        return jsonify({"ok": True, "pools": norm, "raw": resp}), 200
    except MinerError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    # Handle expected network failures explicitly so the UI can degrade gracefully
    except Exception as e:
        import socket, errno as _errno
        # socket.timeout is a subclass of OSError in some versions; check robustly
        if isinstance(e, (socket.timeout, TimeoutError)):
            # Timeouts are expected when miners are offline/unreachable
            logger.warning("get pools timeout for %s", ip)
            return jsonify({"ok": False, "error": "Miner API timed out"}), 504
        if isinstance(e, ConnectionRefusedError):
            logger.warning("get pools connection refused for %s", ip)
            return jsonify({"ok": False, "error": "Miner refused connection"}), 502
        if isinstance(e, OSError):
            # Map common network errno to a 502/503
            code = getattr(e, "errno", None)
            if code in {
                _errno.EHOSTUNREACH,  # 113 (Linux)
                _errno.ENETUNREACH,  # 101
                _errno.ECONNREFUSED,  # 111/10061
                _errno.ETIMEDOUT,  # 110/10060
            }:
                logger.warning("get pools network error for %s: %s", ip, getattr(e, "strerror", str(e)))
                # Use 503 for unreachable/timeout to indicate temporary unavailability
                status = 503 if code in {_errno.EHOSTUNREACH, _errno.ENETUNREACH, _errno.ETIMEDOUT} else 502
                msg = "Network unreachable or timed out" if status == 503 else "Connection refused"
                return jsonify({"ok": False, "error": msg}), status
        logger.exception("get pools failed for %s", ip)
        return jsonify({"ok": False, "error": "Failed to fetch pools", "detail": str(e)}), 500


def _normalize_pool(p: dict) -> dict:
    return {
        "stratum": (p.get("stratum") or p.get("url") or "").strip(),
        "username": (p.get("username") or p.get("user") or "").strip(),
        "password": p.get("password") or "",
    }


def _validate_pools(pools: list[dict]):
    for p in pools:
        if not p["stratum"] or not p["username"]:
            return "Each pool requires stratum and username"
    return None


def _remove_all_pools(client, ops_log: list) -> dict | None:
    """Best-effort: fetch previous pools, then remove all existing pools by id."""
    previous = None
    try:
        previous = client.get_pools()
    except Exception as e:
        previous = {"error": f"failed to fetch pools: {e}"}
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
    return previous


def _add_pools_and_prioritize(client, pools: list[dict], ops_log: list):
    """Add pools, then set priority if multiple pools provided."""
    add_results = []
    for p in pools:
        r = client.add_pool(p["stratum"], p["username"], p.get("password") or "")
        add_results.append({"url": p["stratum"], "user": p["username"], "ok": True, "result": r})
    ops_log.append({"step": "add_pools", "count": len(add_results), "details": add_results})

    if len(pools) > 1:
        try:
            pr = client.pool_priority(list(range(len(pools))))
            ops_log.append({"step": "pool_priority", "ok": True, "result": pr})
        except Exception as e:
            ops_log.append({"step": "pool_priority", "ok": False, "error": str(e)})


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
    append_query = request.args.get("append", "false").lower() in ("1", "true", "yes")
    overwrite_flag = data.get("overwrite")
    overwrite = (not append_query) if overwrite_flag is None else bool(overwrite_flag)

    # Normalize to a list of pools
    pools_body = data.get("pools")
    ops_log = []

    if isinstance(pools_body, list) and pools_body:
        pools_to_set = [_normalize_pool(p) for p in pools_body]
    else:
        pools_to_set = [_normalize_pool(data)]

    # Basic validation
    err = _validate_pools(pools_to_set)
    if err:
        return jsonify({"ok": False, "error": err}), 400

    client = MinerClient(ip)
    prev_pools = None

    try:
        if overwrite:
            prev_pools = _remove_all_pools(client, ops_log)

        _add_pools_and_prioritize(client, pools_to_set, ops_log)

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

    client = MinerClient(ip)
    ops_log = []

    pools_to_set = [_normalize_pool(p) for p in pools_body]
    err = _validate_pools(pools_to_set)
    if err:
        return jsonify({"ok": False, "error": err}), 400

    try:
        previous = _remove_all_pools(client, ops_log)

        _add_pools_and_prioritize(client, pools_to_set, ops_log)

        try:
            final = client.get_pools()
        except Exception:
            final = None

        return jsonify({"ok": True, "previous": previous, "operations": ops_log, "pools": final}), 200
    except MinerError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("replace_pools failed for %s", ip)
        return jsonify({"ok": False, "error": "Failed to replace pools", "detail": str(e)}), 500


@api_bp.get('/miner/<ip>/logs')
def miner_logs(ip):
    """Fetch live logs from a miner via CGMiner/BMminer API.

    Query params:
      - limit: max number of entries to return (default 200)
      - since: ISO8601 or epoch seconds; if provided, filter to entries newer than this
      - raw: include raw miner response when 'true' (default false)
    Response shape: { ok: true, entries: [ {ts, level, message} ... ], raw?: object }
    """
    try:
        try:
            limit = int(request.args.get('limit', 200))
        except Exception:
            limit = 200
        # Enforce bounds for safety
        if limit <= 0:
            return jsonify({"ok": False, "error": "limit must be >= 1"}), 400
        limit = min(limit, API_MAX_LIMIT)
        since_param = request.args.get('since')
        include_raw = (request.args.get('raw', 'false').lower() in ('1', 'true', 'yes'))
        since_ts = None
        if since_param:
            try:
                # accept ISO or epoch
                try:
                    since_ts = int(float(since_param))
                except Exception:
                    dt = _normalize_since(since_param)  # returns naive UTC
                    from datetime import timezone, datetime
                    since_ts = int(datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
                                            tzinfo=timezone.utc).timestamp())
            except Exception:
                since_ts = None

        client = MinerClient(ip)

        # Try the standard 'log' command first
        resp = None
        try:
            resp = client.get_log() or {}
        except Exception:
            resp = None

        # Fallbacks: 'readlog' raw command, then 'notify'
        if not resp:
            try:
                import json as _json
                resp = client._send_command(_json.dumps({"command": "readlog"})) or {}
            except Exception:
                resp = None
        used_notify = False
        if not resp:
            try:
                resp = client.get_notify() or {}
                used_notify = True
            except Exception:
                resp = None

        if resp is None:
            return jsonify({"ok": False, "error": "Miner did not return logs"}), 502

        entries = []
        import math
        # Normalize LOG-style responses
        log_arrays = None
        for k in ("LOG", "log", "READLOG", "ReadLog", "readlog"):
            if isinstance(resp, dict) and k in resp and isinstance(resp[k], list):
                log_arrays = resp[k]
                break
        if log_arrays is None and used_notify:
            log_arrays = resp.get("NOTIFY") or resp.get("Notify") or resp.get("notify") or []

        from datetime import datetime, timezone

        def _sev_from(it):
            lv = (it.get('Level') or it.get('level') or it.get('Code') or it.get('Severity') or '')
            lv = str(lv).strip()
            lvu = lv.upper()
            if any(x in lvu for x in ("ERR", "ERROR", "FATAL", "CRIT")):
                return 'ERROR'
            if any(x in lvu for x in ("WARN", "WARNING")):
                return 'WARN'
            return 'INFO'

        def _ts_from(it):
            w = it.get('When') or it.get('when') or it.get('Timestamp') or it.get('ts')
            # numeric (epoch seconds)
            if isinstance(w, (int, float)) and not math.isnan(float(w)):
                try:
                    return datetime.fromtimestamp(int(w), tz=timezone.utc).isoformat().replace('+00:00', 'Z')
                except Exception:
                    pass
            # try numeric string, then ISO normalization
            if isinstance(w, str) and w:
                ws = w.strip()
                try:
                    sec = float(ws)
                    return datetime.fromtimestamp(int(sec), tz=timezone.utc).isoformat().replace('+00:00', 'Z')
                except Exception:
                    pass
                try:
                    # normalize ISO-ish strings to UTC Z
                    dt = _normalize_since(ws)  # naive UTC
                    return dt.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
                except Exception:
                    # fall through: return as-is
                    return ws
            # if notify had 'When' in seconds since start, fall back to now
            return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

        for it in (log_arrays or []):
            if not isinstance(it, dict):
                # treat as plain line
                msg = str(it)
                entries.append({"ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                                "level": 'INFO', "message": msg})
                continue
            ts = _ts_from(it)
            # Optional since filter
            if since_ts is not None:
                try:
                    ts_epoch = int(datetime.fromisoformat(ts.replace('Z', '+00:00')).timestamp())
                    if ts_epoch < since_ts:
                        continue
                except Exception:
                    pass
            msg = it.get('Msg') or it.get('Message') or it.get('Log') or it.get('msg') or ''
            if not msg:
                # concatenate remaining fields as best-effort message (case-insensitive key filter)
                try:
                    exclude = {'when', 'level', 'code', 'msg', 'message', 'log'}
                    msg = ' '.join(str(v) for k, v in it.items() if str(k).lower() not in exclude)
                except Exception:
                    msg = ''
            entries.append({
                'ts': ts,
                'level': _sev_from(it),
                'message': msg,
            })

        # Enforce limit keeping most recent entries
        if isinstance(entries, list) and len(entries) > limit:
            entries = entries[-limit:]

        payload = {"ok": True, "entries": entries}
        if include_raw:
            payload["raw"] = resp
        return jsonify(payload)

    except MinerError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        import socket, errno as _errno
        if isinstance(e, (socket.timeout, TimeoutError)):
            return jsonify({"ok": False, "error": "Miner API timed out"}), 504
        if isinstance(e, ConnectionRefusedError):
            return jsonify({"ok": False, "error": "Miner refused connection"}), 502
        if isinstance(e, OSError):
            code = getattr(e, 'errno', None)
            if code in {_errno.EHOSTUNREACH, _errno.ENETUNREACH, _errno.ETIMEDOUT}:
                return jsonify({"ok": False, "error": "Network unreachable or timed out"}), 503
        logger.exception("miner logs failed for %s", ip)
        return jsonify({"ok": False, "error": "Failed to fetch miner logs", "detail": str(e)}), 500


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


@api_bp.get('/btc/history')
def btc_history():
    """Return 14-day BTC/USD price history points via server-side proxy.
    Response: { ok: true, points: [{x: epoch_ms, y: price}], last: float, updated: ISO8601Z }
    """
    import requests
    from datetime import datetime, timezone

    # Try CoinGecko first
    points = []
    try:
        cg_url = 'https://api.coingecko.com/api/v3/coins/bitcoin/market_chart'
        params = {'vs_currency': 'usd', 'days': '14', 'interval': 'daily'}
        r = requests.get(cg_url, params=params, timeout=6)
        if r.ok:
            data = r.json() or {}
            prices = data.get('prices') or []
            for it in prices:
                try:
                    ts, price = it[0], it[1]
                    points.append({'x': int(ts), 'y': float(price)})
                except Exception:
                    continue
        else:
            raise RuntimeError(f'CoinGecko HTTP {r.status_code}')
    except Exception:
        # Fallback to CoinCap
        try:
            end_ms = int(time.time() * 1000)
            start_ms = end_ms - 14 * 24 * 60 * 60 * 1000
            cc_url = 'https://api.coincap.io/v2/assets/bitcoin/history'
            params = {'interval': 'd1', 'start': str(start_ms), 'end': str(end_ms)}
            r2 = requests.get(cc_url, params=params, timeout=6)
            if r2.ok:
                payload = r2.json() or {}
                arr = payload.get('data') or []
                for p in arr:
                    try:
                        points.append({'x': int(p.get('time')), 'y': float(p.get('priceUsd'))})
                    except Exception:
                        continue
        except Exception:
            points = []

    if not points:
        return jsonify({'ok': False, 'error': 'No data'}), 502

    last = points[-1]['y']
    updated = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    return jsonify({'ok': True, 'points': points, 'last': last, 'updated': updated})


@api_bp.get('/discover')
def api_discover():
    """Discover miners using optional query params or the user's default discovery profile.
    Query params:
      - cidrs: CSV of CIDR ranges to scan (overrides user/profile if provided)
      - timeout: per-connection timeout seconds (default 1)
      - workers: thread pool size (default 50)
      - mdns: 'true'/'false' to enable Zeroconf (default true)
    Response: { ok: true, miners: [ip,...], sources: {ip: 'tcp'|'mdns'|'both'} }
    """
    # Parse base params with safe fallbacks
    cidrs_param = request.args.get('cidrs')
    try:
        timeout = float(request.args.get('timeout', 1))
    except Exception:
        timeout = 1.0
    try:
        workers = int(request.args.get('workers', 50))
    except Exception:
        workers = 50
    use_mdns = request.args.get('mdns', 'true').lower() in ('1', 'true', 'yes', 'on')

    cidrs = None

    # If no explicit CIDRs, try current user's default profile
    if not cidrs_param:
        try:
            from auth import current_user as _current_user
            u = _current_user()
            if u and u.preferences:
                disc = (u.preferences.get('discovery') or {})
                default_id = disc.get('default_profile')
                profiles = disc.get('profiles') or []
                if default_id and isinstance(profiles, list):
                    for p in profiles:
                        if p.get('id') == default_id:
                            cidrs = p.get('cidrs') or None
                            try:
                                timeout = float(p.get('timeout', timeout))
                            except Exception:
                                pass
                            try:
                                workers = int(p.get('workers', workers))
                            except Exception:
                                pass
                            pm = p.get('use_mdns')
                            if isinstance(pm, bool):
                                use_mdns = pm
                            break
        except Exception:
            pass
    else:
        cidrs = [c.strip() for c in cidrs_param.split(',') if c.strip()]

    try:
        sources = discover_miners(timeout=timeout, workers=workers, use_mdns=use_mdns,
                                  return_sources=True, cidrs=cidrs)
        if isinstance(sources, list):
            miners = list(sources)
            src_map = {ip: 'unknown' for ip in miners}
        else:
            src_map = sources
            miners = sorted(list(src_map.keys()))
        return jsonify({"ok": True, "miners": miners, "sources": src_map})
    except Exception as e:
        logger.exception('discover failed')
        return jsonify({"ok": False, "error": str(e)}), 500
