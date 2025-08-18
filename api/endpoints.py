import ipaddress
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timezone
from flask import Blueprint, jsonify, request
from zeroconf import Zeroconf, ServiceBrowser
from dateutil import parser
from core.db import SessionLocal, Metric
from core.miner import MinerClient
from config import MINER_IP_RANGE

api_bp = Blueprint('api', __name__, url_prefix='/api')


def discover_miners(timeout=1, workers=50):
    network = ipaddress.ip_network(MINER_IP_RANGE)

    def scan(ip):
        with socket.socket() as s:
            s.settimeout(timeout)
            try:
                s.connect((str(ip), 4028))
                return str(ip)
            except:
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


@api_bp.route('/summary')
def summary():
    """Current metrics (power, hashrate, temp, fans). Optionally filter by ?ip=.

    Example:
      curl "http://localhost:5000/api/summary?ip=192.168.1.100"
    """
    ipf = request.args.get('ip')
    miners = [ipf] if ipf else discover_miners()
    data = [];
    totals = {'power': 0, 'hash': 0, 'uptime': 0, 'temps': [], 'fans': []}
    for ip in miners:
        try:
            s = MinerClient(ip).get_summary()
        except Exception:
            # unreachable or non-cgminer host; skip
            continue
        totals['power'] += s.get('power', 0)
        totals['hash'] += s.get('MHS 5s', 0) / 1e6
        totals['uptime'] = max(totals['uptime'], s.get('Elapsed', 0))
        totals['temps'] += s.get('temp', [])
        totals['fans'] += s.get('fan', [])
        data.append({'timestamp': s.get('When'), 'ip': ip, 'hash': s.get('MHS 5s', 0)})
    return jsonify({
        'total_power': totals['power'],
        'total_hashrate': round(totals['hash'], 3),
        'total_uptime': totals['uptime'],
        'avg_temp': round(sum(totals['temps']) / len(totals['temps']), 1) if totals['temps'] else 0,
        'avg_fan_speed': round(sum(totals['fans']) / len(totals['fans']), 0) if totals['fans'] else 0,
        'total_workers': len(miners), 'log': data
    })


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
            'avg_fan_rpm': r.avg_fan_rpm
        }
        for r in rows
    ])
