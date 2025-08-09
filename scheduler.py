import time
import json
import socket
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from core.db import Base, engine, SessionLocal, Metric
from api.endpoints import discover_miners
from core.miner import MinerClient
from notifications import send_email_alert
from config import (
    POLL_INTERVAL, TEMP_THRESHOLD,
    HASHRATE_DROP_THRESHOLD,
    ALERT_COOLDOWN_MINUTES, ROLLING_WINDOW_SAMPLES,
)

# Ensure database tables are created
Base.metadata.create_all(bind=engine)

# In-memory cooldown tracker: { (ip, type): datetime }
LAST_ALERTS = {}


def _cooldown_ok(ip: str, alert_type: str) -> bool:
    key = (ip, alert_type)
    last = LAST_ALERTS.get(key)
    if not last:
        return True
    return datetime.utcnow() - last >= timedelta(minutes=ALERT_COOLDOWN_MINUTES)


def _mark_alert(ip: str, alert_type: str):
    LAST_ALERTS[(ip, alert_type)] = datetime.utcnow()


def _extract_metrics(ip: str, data: dict) -> dict:
    """
    Normalize CGMiner-like responses to the fields used by Metric.
    CGMiner typically returns: {"STATUS": [...], "SUMMARY": [{...}], ...}
    Gracefully fall back to zeros when fields are missing.
    """
    # Try to read from SUMMARY[0] if present
    summary = data
    if isinstance(data, dict) and "SUMMARY" in data and isinstance(data["SUMMARY"], list) and data["SUMMARY"]:
        summary = data["SUMMARY"][0] or {}

    temps = summary.get('temp') or data.get('temp') or []  # some firmwares embed arrays elsewhere
    fans = summary.get('fan') or data.get('fan') or []

    power = summary.get('power') or summary.get('Power') or 0
    # CGMiner exposes "MHS 5s" in MH/s; convert to TH/s
    mhs_5s = summary.get('MHS 5s') or summary.get('GHS 5s')  # some variants use GHS 5s
    if mhs_5s is None:
        # If only GHS 5s present, convert to TH/s; if MHS 5s present, convert to TH/s
        ghs_5s = summary.get('GHS 5s')
        if ghs_5s is not None:
            hashrate_ths = float(ghs_5s) / 1000.0
        else:
            hashrate_ths = 0.0
    else:
        hashrate_ths = float(mhs_5s) / 1e6

    elapsed_s = int(summary.get('Elapsed') or 0)
    avg_temp_c = float(sum(temps) / len(temps)) if temps else 0.0
    avg_fan_rpm = float(sum(fans) / len(fans)) if fans else 0.0

    return {
        "miner_ip": ip,
        "power_w": power or 0,
        "hashrate_ths": hashrate_ths,
        "elapsed_s": elapsed_s,
        "avg_temp_c": avg_temp_c,
        "avg_fan_rpm": avg_fan_rpm,
    }


def poll_metrics():
    """
    Poll all discovered miners, store metrics, and send alerts on thresholds.
    - Temp alert: if avg_temp_c > temp_threshold
    - Hashrate drop: if current < hashrate_drop_threshold * rolling baseline
    """
    session = SessionLocal()

    for ip in discover_miners():
        try:
            data = MinerClient(ip).get_summary()
        except Exception:
            # Miner offline/unreachable; skip this cycle for this IP
            continue

        temps = data.get('temp', [])
        fans = data.get('fan', [])
        metric = Metric(
            miner_ip=ip,
            power_w=data.get('power', 0),
            hashrate_ths=data.get('MHS 5s', 0) / 1e6,
            elapsed_s=data.get('Elapsed', 0),
            avg_temp_c=(sum(temps) / len(temps) if temps else 0),
            avg_fan_rpm=(sum(fans) / len(fans) if fans else 0),
        )
        session.add(metric)
        session.flush()  # get ID/timestamp if needed

        # ---- Alerts: Temperature
        if metric.avg_temp_c > TEMP_THRESHOLD and _cooldown_ok(ip, 'temp'):
            send_email_alert(
                subject=f"High Temperature Alert - {ip}",
                message=(
                    f"Miner {ip} temperature {metric.avg_temp_c:.1f}°C exceeds"
                    f" threshold {TEMP_THRESHOLD:.1f}°C."
                ),
            )
            _mark_alert(ip, 'temp')

        # ---- Alerts: Hashrate drop vs. rolling baseline
        # Fetch last N samples BEFORE this one to compute baseline
        recent = (
            session.query(Metric)
            .filter(Metric.miner_ip == ip)
            .order_by(Metric.timestamp.desc())
            .limit(ROLLING_WINDOW_SAMPLES + 1)  # including this new one
            .all()
        )
        if len(recent) >= 2:  # need at least one prior sample
            # Exclude the newest sample (index 0) when computing baseline
            baseline_samples = [m.hashrate_ths for m in recent[1:] if m.hashrate_ths]
            if baseline_samples:
                baseline = sum(baseline_samples) / len(baseline_samples)
                if baseline > 0:
                    if metric.hashrate_ths < HASHRATE_DROP_THRESHOLD * baseline and _cooldown_ok(ip, 'hashrate_drop'):
                        pct = (metric.hashrate_ths / baseline) * 100.0
                        send_email_alert(
                            subject=f"Hashrate Drop Alert - {ip}",
                            message=(
                                f"Miner {ip} hashrate {metric.hashrate_ths:.2f} TH/s "
                                f"is {pct:.1f}% of baseline ({baseline:.2f} TH/s)."
                            ),
                        )
                        _mark_alert(ip, 'hashrate_drop')

    session.commit()
    session.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(poll_metrics, 'interval', seconds=POLL_INTERVAL, id='poll_metrics')
    scheduler.start()
    print(f"Scheduler started: polling every {POLL_INTERVAL} seconds.")


if __name__ == '__main__':
    start_scheduler()
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")
