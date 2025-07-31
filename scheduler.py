import time
from apscheduler.schedulers.background import BackgroundScheduler
from core.db import Base, engine, SessionLocal, Metric
from api.endpoints import discover_miners
from core.miner import MinerClient
from config import POLL_INTERVAL


# create tables
def setup_db():
    Base.metadata.create_all(bind=engine)


def poll_metrics():
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
    session.commit()
    session.close()


def start_scheduler():
    setup_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(poll_metrics, 'interval', seconds=POLL_INTERVAL, id='poll_metrics')
    scheduler.start()
    print(f"Polling every {POLL_INTERVAL}s...")


if __name__ == '__main__':
    start_scheduler()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
