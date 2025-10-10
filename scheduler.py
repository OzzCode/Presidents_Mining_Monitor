from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from api.endpoints import discover_miners
from config import POLL_INTERVAL
from core.db import Base, engine, SessionLocal, Metric
from core.miner import MinerClient, MinerError
from core.alert_engine import AlertEngine, create_default_rules
from core.notification_service import NotificationService
from core.profitability import ProfitabilityEngine


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
    """Poll metrics from all miners."""
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


def check_alerts():
    """Check for alert conditions and send notifications."""
    try:
        with AlertEngine() as engine:
            new_alerts = engine.check_all_miners()

        # Send notifications for new alerts
        if new_alerts:
            logger.info(f"Found {len(new_alerts)} new alerts, sending notifications")
            notifier = NotificationService()
            success_count = notifier.batch_notify(new_alerts)
            logger.info(f"Sent {success_count}/{len(new_alerts)} notifications")
    except Exception as e:
        logger.exception("Alert checking failed", exc_info=e)


def calculate_profitability():
    """Calculate and save profitability snapshots."""
    try:
        with ProfitabilityEngine() as engine:
            # Calculate fleet-wide profitability
            fleet_result = engine.calculate_fleet_profitability()
            if fleet_result:
                engine.save_snapshot(fleet_result, None)
                logger.info(f"Fleet profitability: ${fleet_result.get('daily_profit_usd', 0):.2f}/day")
    except Exception as e:
        logger.exception("Profitability calculation failed", exc_info=e)


def start_scheduler():
    setup_db()

    # Initialize default alert rules if none exist
    try:
        create_default_rules()
        logger.info("Alert rules initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize default alert rules: {e}")

    scheduler = BackgroundScheduler()

    # Metrics polling job
    scheduler.add_job(poll_metrics, 'interval', seconds=POLL_INTERVAL, id='poll_metrics')

    # Alert checking job (run every 2 minutes)
    scheduler.add_job(check_alerts, 'interval', minutes=2, id='check_alerts')

    # Profitability calculation job (run every 15 minutes)
    scheduler.add_job(calculate_profitability, 'interval', minutes=15, id='calculate_profitability')

    scheduler.add_listener(_job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)
    scheduler.start()

    print(f"Scheduler started:")
    print(f"  - Polling metrics every {POLL_INTERVAL}s")
    print(f"  - Checking alerts every 2 minutes")
    print(f"  - Calculating profitability every 15 minutes")

    return scheduler
