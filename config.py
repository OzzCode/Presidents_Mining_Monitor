import os
from dotenv import load_dotenv

load_dotenv()


# Discovery and Polling
MINER_IP_RANGE = os.getenv('MINER_IP_RANGE', '192.168.86.0/24')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 30))

# Email Notification
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
ALERT_EMAIL = os.getenv('ALERT_EMAIL')

# Alert Thresholds & Behavior
TEMP_THRESHOLD = float(os.getenv('TEMP_THRESHOLD', 80))
HASHRATE_DROP_THRESHOLD = float(os.getenv('HASHRATE_DROP_THRESHOLD', 0.9))  # e.g. 10% drop
ALERT_COOLDOWN_MINUTES    = int(os.getenv('ALERT_COOLDOWN_MINUTES', 30))
ROLLING_WINDOW_SAMPLES    = int(os.getenv('ROLLING_WINDOW_SAMPLES', 10))
