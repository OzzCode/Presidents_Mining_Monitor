import os
from dotenv import load_dotenv

load_dotenv()

MINER_IP_RANGE = os.getenv('MINER_IP_RANGE', '192.168.86.0/24')
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 30))
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
ALERT_EMAIL = os.getenv('ALERT_EMAIL')