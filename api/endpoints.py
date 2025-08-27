import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, jsonify, request
from zeroconf import Zeroconf, ServiceBrowser
from dateutil import parser
from core.db import SessionLocal, Metric, Event
from core.miner import MinerClient, MinerError
from config import MINER_IP_RANGE, POLL_INTERVAL, EFFICIENCY_J_PER_TH
from datetime import datetime, timezone


def _read_summary_fields(ip: str):
    from core.miner import MinerClient
    client = MinerClient(ip)

    # --- SUMMARY ---
    try:
        summary = client.get_summary()
        s = summary["SUMMARY"][0] if isinstance(summary, dict) and summary.get("SUMMARY") else (
            summary if isinstance(summary, dict) else {})
    except Exception:
        return {"power": 0.0, "hash_ths": 0.0, "elapsed": 0, "temps": [], "fans": [], "when": ""}

    mhs_5s = float(s.get("MHS 5s", 0.0)) if isinstance(s.get("MHS 5s", 0.0), (int, float, str)) else 0.0
    elapsed = int(float(s.get("Elapsed", 0) or 0))

    # --- STATS (temps/fans) ---
    temps, fans = [], []
    try:
        stats = client.get_stats()
        if isinstance(stats, dict) and stats.get("STATS"):
            st0 = stats["STATS"][0]
            for k, v in st0.items():
                if isinstance(v, (int, float)):
                    lk = str(k).lower()
                    if lk.startswith("temp"): temps.append(float(v))
                    if lk.startswith("fan"):  fans.append(float(v))
    except Exception:
        pass

    power = float(s.get("Power", 0.0) or 0.0)
    when = s.get("When") or s.get("STIME") or ""

    return {"power": power, "hash_ths": round(mhs_5s / 1e6, 3), "elapsed": elapsed, "temps": temps, "fans": fans,
            "when": when}


api_bp = Blueprint('api', __name__, url_prefix='/api')


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

    hosts = [ip for ip in ThreadPoolExecutor(workers).map(scan, network.hosts()) if ip]
    zeroconf = Zeroconf()
    services = []

    def on_service(zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            for addr in info.addresses:
                services.append(socket.inet_ntoa(addr))

    ServiceBrowser(zeroconf, "_cgminer._tcp.local.", handlers=[on_service])
    time.sleep(2)
    zeroconf.close()

    return sorted(set(hosts + services))


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

    data = []
    totals = {'power': 0.0, 'hash': 0.0, 'uptime': 0, 'temps': [], 'fans': [], 'log': []}
    overall_srcs = set()

    session = SessionLocal()
    for ip in miners:
        payload = None
        src = 'live'
        try:
            payload = MinerClient(ip).fetch_normalized()
        except MinerError:
            # Fallback: use last DB metric for this IP (offline/demo mode)
            last = (
                session.query(Metric)
                .filter(Metric.miner_ip == ip)
                .order_by(Metric.timestamp.desc())
                .first()
            )
            if last:
                payload = {
                    'hashrate_ths': last.hashrate_ths,
                    'elapsed_s': last.elapsed_s,
                    'avg_temp_c': last.avg_temp_c,
                    'avg_fan_rpm': last.avg_fan_rpm,
                    'power_w': last.power_w,
                    'when': last.timestamp.isoformat() + 'Z',
                }
                src = 'db_fallback'
        if not payload:
            continue

        overall_srcs.add(src)
        totals['power'] += float(payload['power_w'])
        totals['hash'] += float(payload['hashrate_ths'])
        totals['uptime'] = max(totals['uptime'], int(payload['elapsed_s']))
        if payload['avg_temp_c']:
            totals['temps'].append(float(payload['avg_temp_c']))
        if payload['avg_fan_rpm']:
            totals['fans'].append(float(payload['avg_fan_rpm']))

        data.append({'timestamp': payload['when'], 'ip': ip, 'hash': payload['hashrate_ths'], 'source': src})

    session.close()

    overall_source = (
        'live' if overall_srcs == {'live'} else
        ('db_fallback' if overall_srcs == {'db_fallback'} else 'mixed')
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


# @api_bp.route('/summary')
# def summary():
#     """Aggregate summary metrics, optionally filtered by IP."""
#     ip_filter = request.args.get('ip')
#     miners = [ip_filter] if ip_filter else discover_miners()
#
#     total_power = 0.0
#     total_hash = 0.0
#     total_uptime = 0
#     temps, fans, log = [], [], []
#
#     # Use normalized fields so the frontend gets real numbers.
#     for ip in miners:
#         norm = _read_summary_fields(ip)
#         total_power += float(norm.get("power", 0.0))
#         total_hash += float(norm.get("hash_ths", 0.0))
#         total_uptime = max(total_uptime, int(norm.get("elapsed", 0)))
#         temps.extend(norm.get("temps", []) or [])
#         fans.extend(norm.get("fans", []) or [])
#         log.append({
#             "timestamp": norm.get("when", ""),
#             "ip": ip,
#             "hash": norm.get("hash_ths", 0.0)
#         })
#
#     avg_temp = round(sum(temps) / len(temps), 1) if temps else 0
#     avg_fan = round(sum(fans) / len(fans), 0) if fans else 0
#
#     return jsonify({
#         "total_power": total_power,
#         "total_hashrate": round(total_hash, 3),
#         "total_uptime": total_uptime,
#         "avg_temp": avg_temp,
#         "avg_fan_speed": avg_fan,
#         "total_workers": len(miners),
#         "log": log
#     })


# noinspection PyBroadException
@api_bp.route('/miners')
def miners():
    info = []
    for ip in discover_miners():
        try:
            d = MinerClient(ip).get_summary()
            model = d.get('Model', 'Unknown') if isinstance(d, dict) else 'Unknown'
            status = 'Online'
        except Exception:
            model = 'Unknown'
            status = 'Offline'
        last_seen_iso, age_sec = _last_seen_for_ip(ip)
        is_stale = (age_sec is None) or (age_sec > 2 * POLL_INTERVAL)
        info.append({
            'model': model,
            'ip': ip,
            'status': status,
            'last_seen': last_seen_iso,
            'age_sec': age_sec,
            'is_stale': is_stale
        })
    return jsonify({'poll_interval': POLL_INTERVAL, 'miners': info})


@api_bp.route('/metrics')
def metrics():
    """
    Return historical metrics, optionally filtered by:
      - ip:    miner IP address
      - since: ISO8601 timestamp
      - limit: number of samples
    """
    ip_filter = request.args.get("ip")
    since = request.args.get("since")
    limit = int(request.args.get("limit", 500))

    session = SessionLocal()
    q = session.query(Metric)
    if ip_filter:
        q = q.filter(Metric.miner_ip == ip_filter)
    if since:
        dt = parser.isoparse(since)
        q = q.filter(Metric.timestamp >= dt)
    rows = q.order_by(Metric.timestamp.asc()).limit(limit).all()
    session.close()

    return jsonify([
        {
            "timestamp": m.timestamp.isoformat(),
            "power_w": m.power_w,
            "hashrate_ths": m.hashrate_ths,
            "avg_temp_c": m.avg_temp_c,
            "avg_fan_rpm": m.avg_fan_rpm
        }
        for m in rows
    ])
