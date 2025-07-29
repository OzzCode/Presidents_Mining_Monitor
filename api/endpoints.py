import ipaddress

from flask import Blueprint, jsonify
from core.miner import MinerClient
from config import MINER_IP_RANGE

api_bp = Blueprint('api', __name__, url_prefix='/api')


def discover_miners():
    """Discover miners on the network using the configured IP range."""
    network = ipaddress.ip_network(MINER_IP_RANGE)
    # naive scan: return all host IPs in the network
    return [str(ip) for ip in network.hosts()]


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
