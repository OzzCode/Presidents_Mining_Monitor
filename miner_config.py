import os
from pathlib import Path

try:
    from dotenv import load_dotenv  # optional
except Exception:
    load_dotenv = None
from core.get_network_ip import get_auto_cidr, resolve_miner_ip_range

if load_dotenv:
    load_dotenv()

# Discovery & polling
# Prefer explicit MINER_IP_RANGE, otherwise use robust resolver with safe fallback
MINER_IP_RANGE = os.getenv('MINER_IP_RANGE', resolve_miner_ip_range())
POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', 30))

# Miner connection settings
CGMINER_TIMEOUT = float(os.getenv('CGMINER_TIMEOUT', 5.0))  # seconds

# Email notifications (for alerts feature)
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
ALERT_EMAIL = os.getenv('ALERT_EMAIL')  # recipient email for alerts

# Default power cost for profitability calculations (USD per kWh)
DEFAULT_POWER_COST = float(os.getenv('DEFAULT_POWER_COST', 0.10))

EFFICIENCY_J_PER_TH = float(os.getenv('EFFICIENCY_J_PER_TH', 29.5))

# Optional per-model overrides (J/TH). Tune these as you like.
# You can override any of these via env vars with the same keys (optional).
EFFICIENCY_MAP = {
    # Common S19 family baselines (rough stock figures)
    "Antminer S19": float(os.getenv("EFF_S19", 29.5)),
    "Antminer S19 Pro": float(os.getenv("EFF_S19_PRO", 27)),
    "Antminer S19j": float(os.getenv("EFF_S19J", 31)),
    "Antminer S19j Pro": float(os.getenv("EFF_S19J_PRO", 29)),
    "Antminer S19 XP": float(os.getenv("EFF_S19_XP", 21.5)),  # ~21–22 J/TH
    "Antminer S19a": float(os.getenv("EFF_S19A", 30)),
    "Antminer S19a Pro": float(os.getenv("EFF_S19A_PRO", 28)),
    # Add more models as needed
}

# Alert thresholds & behavior
TEMP_THRESHOLD = float(os.getenv('TEMP_THRESHOLD', 80))
HASHRATE_DROP_THRESHOLD = float(os.getenv('HASHRATE_DROP_THRESHOLD', 0.9))  # e.g., 0.9 => 10% drop
ALERT_COOLDOWN_MINUTES = int(os.getenv('ALERT_COOLDOWN_MINUTES', 30))
ROLLING_WINDOW_SAMPLES = int(os.getenv('ROLLING_WINDOW_SAMPLES', 10))

# Miner web interface credentials (for reboot and configuration)
MINER_USERNAME = os.getenv('MINER_USERNAME', '')
MINER_PASSWORD = os.getenv('MINER_PASSWORD', 'admin')

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", "logs")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # or 'text'
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "7"))
LOG_TO_DB = os.getenv("LOG_TO_DB", "1") in ("1", "true", "True")

# API behavior
API_MAX_LIMIT = int(os.getenv('API_MAX_LIMIT', 10000))

FIRMWARE_UPLOAD_DIR = Path(os.getenv("FIRMWARE_UPLOAD_DIR", "uploads/firmware"))
FIRMWARE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FIRMWARE_SIZE_BYTES = int(os.getenv("MAX_FIRMWARE_SIZE_BYTES", 100 * 1024 * 2048))
FIRMWARE_ALLOWED_EXTENSIONS = {
    ext.strip().lower()
    for ext in os.getenv("FIRMWARE_ALLOWED_EXTENSIONS", "bin,tar,tar.gz,zip,img").split(",")
    if ext.strip()
}

# Firmware flashing HTTP behavior and credentials
# Whether to verify HTTPS certs to miners; can be False (self-signed) in dev,
# or a path to a CA bundle in stricter environments.
FIRMWARE_HTTP_VERIFY = os.getenv("FIRMWARE_HTTP_VERIFY", "false").lower() in ("1", "true", "yes")

# Default per-vendor credentials (lowercase vendor keys). These act as fallbacks
# when no per-miner credentials are stored. Adjust as needed for your fleet.
FIRMWARE_DEFAULT_CREDENTIALS = {
    "bitmain": {"auth": "digest", "user": os.getenv("BITMAIN_USER", "root"),
                "password": os.getenv("BITMAIN_PASSWORD", "root")},
    "antminer": {"auth": "digest", "user": os.getenv("BITMAIN_USER", "root"),
                 "password": os.getenv("BITMAIN_PASSWORD", "root")},
    "microbt": {"auth": "basic", "user": os.getenv("MICROBT_USER", "root"),
                "password": os.getenv("MICROBT_PASSWORD", "root")},
    "whatsminer": {"auth": "basic", "user": os.getenv("MICROBT_USER", "root"),
                   "password": os.getenv("MICROBT_PASSWORD", "root")},
    # Examples for other vendors (uncomment/tune as needed):
    # "canaan": {"auth": "basic", "user": os.getenv("CANAAN_USER", "root"), "password": os.getenv("CANAAN_PASSWORD", "admin")},
    # "innosilicon": {"auth": "basic", "user": os.getenv("INNO_USER", "admin"), "password": os.getenv("INNO_PASSWORD", "admin")},
}

# Canonical vendor alias normalization for firmware metadata.
# Maps third-party firmware brands to the underlying hardware vendor used by the flasher.
# This is intentionally minimal and can be extended via code changes if needed.
FIRMWARE_VENDOR_ALIASES = {
    # Bitmain/Antminer family
    "vnish": "bitmain",
    "braiins": "bitmain",
    "braiins-os": "bitmain",
    "bos": "bitmain",
    "bosminer": "bitmain",
}


def efficiency_for_model(model: str | None) -> float:
    if not model: return EFFICIENCY_J_PER_TH
    name = model.lower()
    for k, v in EFFICIENCY_MAP.items():
        if k.lower() in name: return v
    return EFFICIENCY_J_PER_TH
