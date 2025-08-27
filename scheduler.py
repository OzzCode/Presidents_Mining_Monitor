import time
from apscheduler.schedulers.background import BackgroundScheduler
from api.endpoints import discover_miners, log_event, _read_summary_fields
from config import POLL_INTERVAL, EFFICIENCY_J_PER_TH
from core.db import Base, engine, SessionLocal, Metric
from core.miner import MinerClient


# create tables
def setup_db():
    Base.metadata.create_all(bind=engine)


def poll_metrics():
    session = SessionLocal()
    try:
        for ip in discover_miners():
            try:
                # If you're using fetch_normalized():
                payload = MinerClient(ip).fetch_normalized()

                metric = Metric(
                    miner_ip=ip,
                    power_w=float(payload.get("power_w", 0.0)),
                    hashrate_ths=float(payload.get("hashrate_ths", 0.0)),
                    elapsed_s=int(payload.get("elapsed_s", 0)),
                    avg_temp_c=float(payload.get("avg_temp_c", 0.0) or 0.0),
                    avg_fan_rpm=float(payload.get("avg_fan_rpm", 0.0) or 0.0),
                )
                session.add(metric)

            except Exception as e:
                # Record that this IP failed to poll during the scheduled run
                log_event("ERROR", f"scheduler: poll failed: {e}", miner_ip=ip, source="scheduler")
                continue

        session.commit()
    except Exception as e:
        # If the commit fails (disk, schema), record once at job level
        log_event("ERROR", f"scheduler: commit failed: {e}", source="scheduler")
        try:
            session.rollback()
        except Exception:
            pass
    finally:
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
