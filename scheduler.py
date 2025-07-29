from apscheduler.schedulers.background import BackgroundScheduler
import time

from core.db import SessionLocal, Base, engine, Metric
from api.endpoints import discover_miners
from core.miner import MinerClient
from config import POLL_INTERVAL


def poll_metrics():
    """
    Poll all miners and store metrics in the database.
    """
    # Create tables if not exist
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    miners = discover_miners()
    for ip in miners:
        client = MinerClient(ip)
        data = client.get_summary()
        # Compute aggregated values
        power = data.get('power', 0)
        hashrate = data.get('MHS 5s', 0) / 1e6
        elapsed = data.get('Elapsed', 0)
        temps = data.get('temp', [])
        fans = data.get('fan', [])
        avg_temp = sum(temps) / len(temps) if temps else 0
        avg_fan = sum(fans) / len(fans) if fans else 0

        metric = Metric(
            miner_ip=ip,
            power_w=power,
            hashrate_ths=round(hashrate, 3),
            elapsed_s=elapsed,
            avg_temp_c=round(avg_temp, 1),
            avg_fan_rpm=round(avg_fan, 0)
        )
        session.add(metric)
    session.commit()
    session.close()


def start_scheduler():
    """Start the background scheduler for polling miners."""
    scheduler = BackgroundScheduler()
    # Schedule the poll job at an interval
    scheduler.add_job(poll_metrics, 'interval', seconds=POLL_INTERVAL, id='poll_metrics')
    scheduler.start()
    print('Scheduler started, polling every', POLL_INTERVAL, 'seconds.')


if __name__ == '__main__':
    start_scheduler()
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        print('Scheduler stopped.')
