import logging, os, sys
from logging.handlers import TimedRotatingFileHandler
from pythonjsonlogger import jsonlogger


def setup_logging(app_name="antminer_monitor"):
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_dir = os.getenv("LOG_DIR", "logs")
    fmt = os.getenv("LOG_FORMAT", "json")  # 'json' or 'text'
    retention = int(os.getenv("LOG_RETENTION_DAYS", "7"))

    os.makedirs(log_dir, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)

    if fmt == "json":
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s "
            "%(component)s %(miner_ip)s %(job_id)s %(path)s %(endpoint)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(component)s | %(miner_ip)s | %(message)s"
        )

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    root.addHandler(sh)

    fh = TimedRotatingFileHandler(
        os.path.join(log_dir, f"{app_name}.log"), when="midnight", backupCount=retention
    )
    fh.setFormatter(formatter)
    root.addHandler(fh)

    return root
