import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, jsonify, request
from zeroconf import Zeroconf, ServiceBrowser
from dateutil import parser
from core.db import SessionLocal, Metric
from core.miner import MinerClient
from config import MINER_IP_RANGE

api_bp = Blueprint('api', __name__, url_prefix='/api')


def discover_miners(timeout=1, workers=50):
    """
    Scan the configured CIDR for TCP/4028 and also browse mDNS _cgminer._tcp.
    """
    network = ipaddress.ip_network(MINER_IP_RANGE)

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


# --------------------------
# Normalization helper
# --------------------------
def _read_summary_fields(ip: str):
    """
    Query a miner and normalize cgminer/BMminer SUMMARY/STATS into a consistent
    shape for our API: power, hash_ths, elapsed, temps[], fans[], when.
    """
    client = MinerClient(ip)

    # --- SUMMARY: has MHS 5s (hashrate) and Elapsed (uptime) ---
    s = {}
    try:
        summary = client.get_summary()
        # Typical shape: {"STATUS":[...], "SUMMARY":[{...}]}
        if isinstance(summary, dict) and "SUMMARY" in summary and summary["SUMMARY"]:
            s = summary["SUMMARY"][0]
        else:
            # Some firmwares flatten fields at the top level
            s = summary if isinstance(summary, dict) else {}
    except Exception:
        # Miner unreachable or parse failure
        return {"power": 0.0, "hash_ths": 0.0, "elapsed": 0, "temps": [], "fans": [], "when": ""}

    # Hashrate (MHS 5s -> TH/s), Uptime
    try:
        mhs_5s = float(s.get("MHS 5s", 0.0))
    except Exception:
        mhs_5s = 0.0
    try:
        elapsed = int(s.get("Elapsed", 0))
    except Exception:
        elapsed = 0

    # --- STATS: temps and fan speeds are typically here ---
    temps, fans = [], []
    try:
        stats = client.get_stats()
        if isinstance(stats, dict) and "STATS" in stats and stats["STATS"]:
            st0 = stats["STATS"][0]
            # Collect any numeric keys that look like temp/fan readings
            for k, v in st0.items():
                if isinstance(v, (int, float)):
                    lk = str(k).lower()
                    if lk.startswith("temp"):
                        temps.append(float(v))
                    if lk.startswith("fan"):
                        fans.append(float(v))
    except Exception:
        # Ignore STATS failures; we still have hashrate/uptime
        pass

    # Some firmwares provide a timestamp-like field in SUMMARY
    when = s.get("When") or s.get("STIME") or ""

    # Power may be 0/absent on stock fw; keep it best-effort
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
    """Aggregate summary metrics, optionally filtered by IP."""
    ip_filter = request.args.get('ip')
    miners = [ip_filter] if ip_filter else discover_miners()

    total_power = 0.0
    total_hash = 0.0
    total_uptime = 0
    temps, fans, log = [], [], []

    # Use normalized fields so the frontend gets real numbers.
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
    """
    Basic online/offline & model probe for the miners table.
    """
    info = []
    for ip in discover_miners():
        try:
            d = MinerClient(ip).get_summary()
            model = d.get("Model", "Unknown") if isinstance(d, dict) else "Unknown"
            status = "Online"
        except Exception:
            model = "Unknown"
            status = "Offline"
        info.append({"model": model, "ip": ip, "status": status})
    return jsonify({"miners": info})


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
