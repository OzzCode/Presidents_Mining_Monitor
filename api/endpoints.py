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
    ipf = request.args.get('ip')
    miners = [ipf] if ipf else discover_miners()
    data = []
    totals = {'power': 0, 'hash': 0, 'uptime': 0, 'temps': [], 'fans': []}

    session = SessionLocal()
    for ip in miners:
        payload = None
        # noinspection PyBroadException
        try:
            payload = MinerClient(ip).get_summary()
        except Exception:
            # Fallback: use the last DB metric for this IP (demo/offline mode)
            last = (session.query(Metric)
                    .filter(Metric.miner_ip == ip)
                    .order_by(Metric.timestamp.desc())
                    .first())
            if last:
                payload = {
                    'power': last.power_w,
                    'MHS 5s': last.hashrate_ths * 1e6,
                    'Elapsed': last.elapsed_s,
                    'temp': [last.avg_temp_c],
                    'fan': [last.avg_fan_rpm],
                    'When': last.timestamp.isoformat()
                }
        if not payload:
            continue

        totals['power'] += payload.get('power', 0)
        totals['hash'] += payload.get('MHS 5s', 0) / 1e6
        totals['uptime'] = max(totals['uptime'], payload.get('Elapsed', 0))
        totals['temps'] += payload.get('temp', [])
        totals['fans'] += payload.get('fan', [])
        data.append({'timestamp': payload.get('When'), 'ip': ip, 'hash': payload.get('MHS 5s', 0)})

    session.close()
    return jsonify({
        'total_power': totals['power'],
        'total_hashrate': round(totals['hash'], 3),
        'total_uptime': totals['uptime'],
        'avg_temp': round(sum(totals['temps']) / len(totals['temps']), 1) if totals['temps'] else 0,
        'avg_fan_speed': round(sum(totals['fans']) / len(totals['fans']), 0) if totals['fans'] else 0,
        'total_workers': len(miners), 'log': data
    })


@api_bp.route('/miners')
def miners():
    info = []
    for ip in discover_miners():
        # noinspection PyBroadException
        try:
            d = MinerClient(ip).get_summary()
            model = d.get('Model', 'Unknown')
            status = 'Online'
        except:
            model = 'Unknown'
            status = 'Offline'
        info.append({'model': model, 'ip': ip, 'status': status})

    return jsonify({'miners': info})


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
    """
    Return historical metrics, optionally filtered by:
      - ip:    miner IP address
      - since: ISO8601 timestamp
      - limit: number of samples
    """
    ip_filter = request.args.get('ip')
    since = request.args.get('since')
    limit = int(request.args.get('limit', 500))

    session = SessionLocal()
    q = session.query(Metric)
    if ip_filter:
        q = q.filter(Metric.miner_ip == ip_filter)
    if since:
        dt = _normalize_since(since)
        q = q.filter(Metric.timestamp >= dt)
    rows = q.order_by(Metric.timestamp.asc()).limit(limit).all()
    session.close()

    return jsonify([
        {
            'timestamp': m.timestamp.isoformat(),
            'power_w': m.power_w,
            'hashrate_ths': m.hashrate_ths,
            'avg_temp_c': m.avg_temp_c,
            'avg_fan_rpm': m.avg_fan_rpm
        }
        for m in rows
    ])
