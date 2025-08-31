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

EFFICIENCY_J_PER_TH = float(os.getenv('EFFICIENCY_J_PER_TH', 29.5))

# Optional per-model overrides (J/TH). Tune these as you like.
# You can override any of these via env vars with the same keys (optional).
EFFICIENCY_MAP = {
    # Common S19 family baselines (rough stock figures)
    "S19": float(os.getenv("EFF_S19", 29.5)),
    "S19 Pro": float(os.getenv("EFF_S19_PRO", 27)),
    "S19j": float(os.getenv("EFF_S19J", 31)),
    "S19j Pro": float(os.getenv("EFF_S19J_PRO", 29)),
    "S19 XP": float(os.getenv("EFF_S19_XP", 21.5)),  # ~21–22 J/TH
    "S19a": float(os.getenv("EFF_S19A", 30)),
    "S19a Pro": float(os.getenv("EFF_S19A_PRO", 28)),
    # Add more models as needed
}

# Alert thresholds & behavior
TEMP_THRESHOLD = float(os.getenv('TEMP_THRESHOLD', 80))
HASHRATE_DROP_THRESHOLD = float(os.getenv('HASHRATE_DROP_THRESHOLD', 0.9))  # e.g., 0.9 => 10% drop
ALERT_COOLDOWN_MINUTES = int(os.getenv('ALERT_COOLDOWN_MINUTES', 30))
ROLLING_WINDOW_SAMPLES = int(os.getenv('ROLLING_WINDOW_SAMPLES', 10))

# CGMiner client behavior
CGMINER_TIMEOUT = float(os.getenv('CGMINER_TIMEOUT', 1.0))  # seconds

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # or 'text'
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "7"))
LOG_TO_DB = os.getenv("LOG_TO_DB", "1") in ("1", "true", "True")

# API behavior
API_MAX_LIMIT = int(os.getenv('API_MAX_LIMIT', 10000))


def efficiency_for_model(model: str | None) -> float:
    if not model: return EFFICIENCY_J_PER_TH
    name = model.lower()
    for k, v in EFFICIENCY_MAP.items():
        if k.lower() in name: return v
    return EFFICIENCY_J_PER_TH
