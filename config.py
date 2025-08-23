import os
from dotenv import load_dotenv
from core.get_network_ip import get_auto_cidr

load_dotenv()

# Discovery & polling
MINER_IP_RANGE = os.getenv('MINER_IP_RANGE', get_auto_cidr())
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 30))

# Email notifications
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
ALERT_EMAIL = os.getenv('ALERT_EMAIL')
# SMTP_USER = os.getenv('SMTP_USER')
# SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

# Alert thresholds & behavior
TEMP_THRESHOLD = float(os.getenv('TEMP_THRESHOLD', 80))
HASHRATE_DROP_THRESHOLD = float(os.getenv('HASHRATE_DROP_THRESHOLD', 0.9))  # e.g., 0.9 => 10% drop
ALERT_COOLDOWN_MINUTES = int(os.getenv('ALERT_COOLDOWN_MINUTES', 30))
ROLLING_WINDOW_SAMPLES = int(os.getenv('ROLLING_WINDOW_SAMPLES', 10))

# CGMiner client behavior
CGMINER_TIMEOUT = float(os.getenv('CGMINER_TIMEOUT', 1.0))  # seconds
