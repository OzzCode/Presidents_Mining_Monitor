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
    """Current metrics (power, hashrate, temp, fans). Optionally filter by ?ip=.

    Example:
      curl "http://localhost:5000/api/summary?ip=192.168.1.100"
    """
    ipf = request.args.get('ip')
    miners = [ipf] if ipf else discover_miners()

    data = []
    totals = {'power': 0.0, 'hash': 0.0, 'uptime': 0, 'temps': [], 'fans': []}

    session = SessionLocal()
    for ip in miners:
        payload = None
        try:
            payload = MinerClient(ip).fetch_normalized()
        except MinerError:
            # Fallback: use the last DB metric for this IP (offline/demo mode)
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
        if not payload:
            continue

        totals['power'] += float(payload['power_w'])
        totals['hash'] += float(payload['hashrate_ths'])
        totals['uptime'] = max(totals['uptime'], int(payload['elapsed_s']))
        if payload['avg_temp_c']:
            totals['temps'].append(float(payload['avg_temp_c']))
        if payload['avg_fan_rpm']:
            totals['fans'].append(float(payload['avg_fan_rpm']))

        data.append({'timestamp': payload['when'], 'ip': ip, 'hash': payload['hashrate_ths']})

    session.close()
    return jsonify({
        'total_power': round(totals['power'], 1),
        'total_hashrate': round(totals['hash'], 3),
        'total_uptime': totals['uptime'],
        'avg_temp': round(sum(totals['temps']) / len(totals['temps']), 1) if totals['temps'] else 0,
        'avg_fan_speed': round(sum(totals['fans']) / len(totals['fans']), 0) if totals['fans'] else 0,
        'total_workers': len(miners),
        'log': data,
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
            'avg_fan_rpm': r.avg_fan_rpm,
        }
        for r in rows
    ])
