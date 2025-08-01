import time
from apscheduler.schedulers.background import BackgroundScheduler
from core.db import Base, engine, SessionLocal, Metric
from api.endpoints import discover_miners
from core.miner import MinerClient
from config import POLL_INTERVAL, TEMP_THRESHOLD, HASHRATE_DROP_THRESHOLD
from notifications import send_email_alert

# Ensure database tables are created
Base.metadata.create_all(bind=engine)


def poll_metrics():
    """
    Poll all discovered miners, store metrics, and send alerts on thresholds.
    """
    session = SessionLocal()
    for ip in discover_miners():
        data = MinerClient(ip).get_summary()
        temps = data.get('temp', [])
        fans = data.get('fan', [])
        metric = Metric(
            miner_ip=ip,
            power_w=data.get('power', 0),
            hashrate_ths=data.get('MHS 5s', 0) / 1e6,
            elapsed_s=data.get('Elapsed', 0),
            avg_temp_c=(sum(temps) / len(temps) if temps else 0),
            avg_fan_rpm=(sum(fans) / len(fans) if fans else 0)
        )
        session.add(metric)

        # Alert on a temperature threshold
        if metric.avg_temp_c > TEMP_THRESHOLD:
            send_email_alert(
                subject=f"High Temperature Alert - {ip}",
                message=f"Miner {ip} reached {metric.avg_temp_c}°C (threshold: {TEMP_THRESHOLD}°C)."
            )

        # TODO: compare hashrate against previous sample for drop alerts
        # Alert on hashrate drop threshold
        if metric.hashrate_ths < HASHRATE_DROP_THRESHOLD:
            send_email_alert(
                subject=f"Low Hashrate Alert - {ip}",
                message=f"Miner {ip} dropped below {metric.hashrate_ths} TH/s (threshold: {HASHRATE_DROP_THRESHOLD} TH/s)."
            )

    session.commit()
    session.close()


def start_scheduler():
    """
    Initialize and start the background scheduler for polling.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(poll_metrics, 'interval', seconds=POLL_INTERVAL, id='poll_metrics')
    scheduler.start()
    print(f"Scheduler started: polling every {POLL_INTERVAL} seconds.")


if __name__ == '__main__':
    start_scheduler()
    try:
        # Keep the main thread alive to let the scheduler run
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")