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
    """Aggregate summary metrics, optionally filtered by IP."""
    ip_filter = request.args.get('ip')
    miners = [ip_filter] if ip_filter else discover_miners()
    total_power = total_hash = total_uptime = 0
    temps = []
    fans = []
    log = []
    for ip in miners:
        data = MinerClient(ip).get_summary()
        total_power += data.get('power', 0)
        total_hash += data.get('MHS 5s', 0) / 1e6
        total_uptime = max(total_uptime, data.get('Elapsed', 0))
        temps.extend(data.get('temp', []))
        fans.extend(data.get('fan', []))
        log.append({'timestamp': data.get('When'), 'ip': ip, 'hash': data.get('MHS 5s', 0)})
    return jsonify({
        'total_power': total_power,
        'total_hashrate': round(total_hash, 3),
        'total_uptime': total_uptime,
        'avg_temp': round(sum(temps) / len(temps), 1) if temps else 0,
        'avg_fan_speed': round(sum(fans) / len(fans), 0) if fans else 0,
        'total_workers': len(miners),
        'log': log
    })


@api_bp.route('/miners')
def miners():
    info = []
    for ip in discover_miners():
        try:
            d = MinerClient(ip).get_summary()
            model = d.get('Model', 'Unknown')
            status = 'Online'
        except:
            model = 'Unknown'
            status = 'Offline'
        info.append({'model': model, 'ip': ip, 'status': status})
    return jsonify({'miners': info})


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
        dt = parser.isoparse(since)
        q = q.filter(Metric.timestamp >= dt)
    rows = (q.order_by(Metric.timestamp.asc())
            .limit(limit).all())
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
