import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, jsonify
from core.miner import MinerClient
from config import MINER_IP_RANGE

api_bp = Blueprint('api', __name__, url_prefix='/api')


def discover_miners(timeout=1, workers=50):
    """Discover miners by scanning the configured IP range for open CGMiner port (4028)
    and via mDNS (_cgminer._tcp.local.) discovery."""
    network = ipaddress.ip_network(MINER_IP_RANGE)

    # Port scan
    def scan_ip(ip):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((str(ip), 4028))
            s.close()
            return str(ip)
        except:
            return None

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = executor.map(scan_ip, network.hosts())
    scanned = [ip for ip in results if ip]

    # mDNS discovery
    from zeroconf import Zeroconf, ServiceBrowser
    import time

    zeroconf = Zeroconf()
    services = []

    def on_service(zeroconf_obj, service_type, name):
        info = zeroconf_obj.get_service_info(service_type, name)
        if info and info.addresses:
            for addr in info.addresses:
                services.append(socket.inet_ntoa(addr))

    ServiceBrowser(zeroconf, "_cgminer._tcp.local.", handlers=[on_service])
    # Allow time for discovery
    time.sleep(2)
    zeroconf.close()
    mdns_hosts = set(services)

    # Combine and return unique hosts
    return sorted(set(scanned + list(mdns_hosts)))


@api_bp.route('/summary')
def summary():
    """Aggregate summary metrics from all miners."""
    miners = discover_miners()
    total_power = 0
    total_hashrate = 0
    uptimes = []
    temps = []
    fans = []
    log = []  # for storing individual miner stats

    for ip in miners:
        client = MinerClient(ip)
        data = client.get_summary()
        # extract fields (keys may vary)
        total_power += data.get('power', 0)
        total_hashrate += data.get('MHS 5s', 0) / 1e6  # convert MH/s to TH/s
        uptimes.append(data.get('Elapsed', 0))
        temps.extend(data.get('temp', []))
        fans.extend(data.get('fan', []))
        # log individual
        log.append({
            'timestamp': data.get('When'),
            'stat': ip,
            'value': data.get('MHS 5s', 0)
        })

    avg_temp = sum(temps) / len(temps) if temps else 0
    avg_fan = sum(fans) / len(fans) if fans else 0

    return jsonify({
        'total_power': total_power,
        'total_hashrate': round(total_hashrate, 3),
        'total_uptime': max(uptimes) if uptimes else 0,
        'avg_temp': round(avg_temp, 1),
        'avg_fan_speed': round(avg_fan, 0),
        'total_workers': len(miners),
        'log': log
    })


@api_bp.route('/miners')
def miners():
    return jsonify({'miners': discover_miners()})
