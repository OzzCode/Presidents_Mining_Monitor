import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timezone
from flask import Blueprint, jsonify, request
from zeroconf import Zeroconf, ServiceBrowser
from dateutil import parser
from core.db import SessionLocal, Metric
from core.miner import MinerClient, MinerError
from config import MINER_IP_RANGE

api_bp = Blueprint('api', __name__, url_prefix='/api')


def _read_summary_fields(ip: str):
    """
    Query a miner and normalize cgminer/BMminer SUMMARY/STATS
    into consistent fields our API expects.
    """
    from core.miner import MinerClient
    client = MinerClient(ip)
    s = {}
    try:
        summary = client.get_summary()
        if "SUMMARY" in summary and summary["SUMMARY"]:
            s = summary["SUMMARY"][0]
        else:
            s = summary
    except Exception:
        return {"power": 0, "hash_ths": 0, "elapsed": 0, "temps": [], "fans": [], "when": ""}

    mhs_5s = float(s.get("MHS 5s", 0.0))
    elapsed = int(s.get("Elapsed", 0))

    temps, fans = [], []
    try:
        stats = client.get_stats()
        if "STATS" in stats and stats["STATS"]:
            st0 = stats["STATS"][0]
            for k, v in st0.items():
                if isinstance(v, (int, float)):
                    if k.lower().startswith("temp"):
                        temps.append(float(v))
                    if k.lower().startswith("fan"):
                        fans.append(float(v))
    except Exception:
        pass

    return {
        "power": float(s.get("Power", 0.0) or 0.0),
        "hash_ths": round(mhs_5s / 1e6, 3),  # MHS → THS
        "elapsed": elapsed,
        "temps": temps,
        "fans": fans,
        "when": s.get("When") or s.get("STIME") or ""
    }


def discover_miners(timeout=1, workers=50):
    network = ipaddress.ip_network(MINER_IP_RANGE)

    def scan(ip):
        with socket.socket() as s:
            s.settimeout(timeout)
            try:
                s.connect((str(ip), 4028))
                return str(ip)
            except Exception:
                return None

    hosts = [i for i in ThreadPoolExecutor(workers).map(scan, network.hosts()) if i]

    # mDNS discovery
    zc = Zeroconf()
    services = []

    def on_srv(zc_, type_, name):
        info = zc_.get_service_info(type_, name)
        if info:
            for a in info.addresses:
                services.append(socket.inet_ntoa(a))

    ServiceBrowser(zc, "_cgminer._tcp.local.", handlers=[on_srv])
    time.sleep(2)
    zc.close()

    return sorted(set(hosts + services))


@api_bp.route('/summary')
def summary():
    """Aggregate summary metrics, optionally filtered by IP."""
    ip_filter = request.args.get('ip')
    miners = [ip_filter] if ip_filter else discover_miners()

    total_power = 0.0
    total_hash = 0.0
    total_uptime = 0
    temps, fans, log = [], [], []

    # --- replace ONLY this loop body ---
    for ip in miners:
        norm = _read_summary_fields(ip)
        total_power += float(norm.get("power", 0.0))
        total_hash += float(norm.get("hash_ths", 0.0))
        total_uptime = max(total_uptime, int(norm.get("elapsed", 0)))
        temps.extend(norm.get("temps", []) or [])
        fans.extend(norm.get("fans", []) or [])
        log.append({
            "timestamp": norm.get("when", ""),
            "ip": ip,
            "hash": norm.get("hash_ths", 0.0)
        })
    # --- end replacement ---

    avg_temp = round(sum(temps) / len(temps), 1) if temps else 0
    avg_fan = round(sum(fans) / len(fans), 0) if fans else 0

    return jsonify({
        "total_power": total_power,
        "total_hashrate": round(total_hash, 3),
        "total_uptime": total_uptime,
        "avg_temp": avg_temp,
        "avg_fan_speed": avg_fan,
        "total_workers": len(miners),
        "log": log
    })


@api_bp.route('/miners')
def miners():
    """List discovered miners with basic status and (if known) model."""
    ips = discover_miners()
    session = SessionLocal()

    out = []
    for ip in ips:
        model = ''
        status = 'online'
        try:
            # Try to grab a model from STATS (Antminer/BMminer often puts it here)
            stats = MinerClient(ip).get_stats()
            st0 = (stats.get('STATS') or [{}])[0]
            model = (
                    st0.get('Type') or
                    st0.get('Model') or
                    st0.get('Miner Type') or 'Unknown'
            )
        except Exception:
            status = 'offline'

        last = (
            session.query(Metric)
            .filter(Metric.miner_ip == ip)
            .order_by(Metric.timestamp.desc())
            .first()
        )

        out.append({
            'ip': ip,
            'model': model,
            'status': status,
            'last_seen': (last.timestamp.isoformat() if last else None)
        })

    session.close()
    return jsonify({'miners': out})


def _normalize_since(since: str):
    """Return a *naive UTC* datetime for filtering metrics.

    Accepts ISO8601 with/without a timezone. If timezone-aware, converts to UTC and
    drops tzinfo to match naive UTC storage in the DB.

    Examples:
      naive: 2025-07-31T12:00:00
      aware: 2025-07-31T12:00:00Z or 2025-07-31T08:00:00-04:00
    """
    dt = parser.isoparse(since)
    if dt.tzinfo:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


@api_bp.route('/metrics')
@api_bp.get("/api/miner/<ip>/metrics")
@api_bp.get("/api/miners/<ip>/metrics")
def metrics():
    """Historical data with optional filters.

    Query params:
      ip     — miner IP address
      since  — ISO8601 timestamp (naive or tz-aware)
      limit  — max samples (default 500)

    Examples:
      curl "http://localhost:5000/api/metrics?limit=50"
      curl "http://localhost:5000/api/metrics?ip=192.168.1.100&since=2025-07-31T12:00:00Z"
    """
    ipf = request.args.get('ip')
    since = request.args.get('since')
    limit = int(request.args.get('limit', 500))

    session = SessionLocal()
    q = session.query(Metric)
    if ipf:
        q = q.filter(Metric.miner_ip == ipf)
    if since:
        dt = _normalize_since(since)
        q = q.filter(Metric.timestamp >= dt)
    rows = q.order_by(Metric.timestamp.asc()).limit(limit).all()
    session.close()

    return jsonify([
        {
            'timestamp': r.timestamp.isoformat(),
            'power_w': r.power_w,
            'hashrate_ths': r.hashrate_ths,
            'avg_temp_c': r.avg_temp_c,
            'avg_fan_rpm': r.avg_fan_rpm,
        }
        for r in rows
    ])
