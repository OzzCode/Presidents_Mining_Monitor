from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from api.endpoints import discover_miners
from config import POLL_INTERVAL
from core.db import Base, engine, SessionLocal, Metric
from core.miner import MinerClient, MinerError


# create tables
def setup_db():
    Base.metadata.create_all(bind=engine)


logger = logging.getLogger(__name__)


def _job_listener(event):
    if event.exception:
        logger.exception("scheduler_job_failed", extra={"component": "scheduler", "job_id": event.job_id})
    else:
        logger.debug("scheduler_job_ok", extra={"component": "scheduler", "job_id": event.job_id})


def poll_metrics():
    session = SessionLocal()
    try:
        for ip in discover_miners():
            try:
                # If you're using fetch_normalized():
                payload = MinerClient(ip).fetch_normalized()
            except MinerError:
                continue

            session.add(Metric(
                miner_ip=ip,
                power_w=float(payload.get("power_w", 0.0)),
                hashrate_ths=float(payload.get("hashrate_ths", 0.0)),
                elapsed_s=int(payload.get("elapsed_s", 0)),
                avg_temp_c=float(payload.get("avg_temp_c", 0.0) or 0.0),
                avg_fan_rpm=float(payload.get("avg_fan_rpm", 0.0) or 0.0),
            ))

            session.commit()
    finally:
        session.close()


def start_scheduler():
    setup_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(poll_metrics, 'interval', seconds=POLL_INTERVAL, id='poll_metrics')
    scheduler.add_listener(_job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)
    scheduler.start()

    print(f"Polling every {POLL_INTERVAL}s...")


# if __name__ == '__main__':
#     start_scheduler()
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         pass
