from core.get_network_ip import detect_local_ipv4_networks, detect_primary_ipv4

print("Detected networks:", [str(net) for net in detect_local_ipv4_networks()])
print("Primary IP:", detect_primary_ipv4())
