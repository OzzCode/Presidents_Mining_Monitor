import os
import socket
import ipaddress
import psutil


def detect_local_ipv4_networks():
    """Return a list of IPv4Network objects for all active non-loopback interfaces."""
    nets = []
    for ifname, addrs in psutil.net_if_addrs().items():
        stats = psutil.net_if_stats().get(ifname)
        if not stats or not stats.isup:
            continue
        for a in addrs:
            if a.family == socket.AF_INET and a.address and a.netmask:
                try:
                    net = ipaddress.IPv4Network(f"{a.address}/{a.netmask}", strict=False)
                except ValueError:
                    continue
                if net.is_loopback or net.is_link_local:
                    continue
                nets.append(net)
    # Deduplicate
    unique = []
    seen = set()
    for n in nets:
        key = (int(n.network_address), n.prefixlen)
        if key not in seen:
            seen.add(key)
            unique.append(n)
    return unique


def detect_primary_ipv4():
    """Return the primary local IPv4 used for outbound traffic."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No packets are sent; this just selects a route
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def get_auto_cidr():
    """Pick the CIDR for the primary interface; fall back to the first available."""
    networks = detect_local_ipv4_networks()
    if not networks:
        return None
    primary_ip = detect_primary_ipv4()
    for net in networks:
        if ipaddress.IPv4Address(primary_ip) in net:
            return str(net)
    return str(networks[0])


def resolve_miner_ip_range():
    """Use MINER_IP_RANGE if set; otherwise auto-detect."""
    env_val = os.getenv("MINER_IP_RANGE")
    if env_val:
        return env_val
    auto = get_auto_cidr()
    # Optional: fallback to a conservative private range if detection fails
    return auto or "192.168.0.0/16"
