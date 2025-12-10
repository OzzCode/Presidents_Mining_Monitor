from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
import logging
import datetime as dt
from apscheduler.schedulers.background import BackgroundScheduler
from api.endpoints import discover_miners
from miner_config import POLL_INTERVAL
from core.db import Base, engine, SessionLocal, Metric, Miner
from core.miner import MinerClient, MinerError
from core.alert_engine import AlertEngine, create_default_rules
from core.notification_service import NotificationService
from core.profitability import ProfitabilityEngine
from core.electricity import ElectricityCostService
from core.firmware import FirmwareFlashService


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
        inserted = 0
        ips = []
        try:
            ips = discover_miners()
        except Exception as e:
            logger.exception("discover_miners_failed", exc_info=e)
            ips = []

        if not ips:
            logger.warning("poll_metrics_no_miners_found")
            return

        logger.info(f"poll_metrics_discovered_miners count={len(ips)}")

        for ip in ips:
            try:
                # If you're using fetch_normalized():
                payload = MinerClient(ip).fetch_normalized()
            except MinerError as me:
                logger.warning(f"miner_fetch_failed ip={ip} error={me}")
                continue

            session.add(Metric(
                miner_ip=ip,
                power_w=float(payload.get("power_w", 0.0)),
                hashrate_ths=float(payload.get("hashrate_ths", 0.0)),
                elapsed_s=int(payload.get("elapsed_s", 0)),
                avg_temp_c=float(payload.get("avg_temp_c", 0.0) or 0.0),
                avg_fan_rpm=float(payload.get("avg_fan_rpm", 0.0) or 0.0),
            ))
            inserted += 1

        session.commit()
        logger.info(f"poll_metrics_inserted_rows count={inserted}")
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


def record_electricity_costs():
    """Record electricity costs for all miners based on recent power consumption."""
    session = SessionLocal()
    try:
        # Get all active electricity rates
        from core.db import ElectricityRate
        active_rates = session.query(ElectricityRate).filter(ElectricityRate.active == True).all()

        if not active_rates:
            logger.debug("No active electricity rates configured, skipping cost recording")
            return

        # Define the recording period (last hour)
        period_end = dt.datetime.utcnow()
        period_start = period_end - dt.timedelta(hours=1)

        # Get all miners
        miners = session.query(Miner).all()

        # Group miners by location for rate matching
        location_groups = {}
        for miner in miners:
            location = miner.location or "default"
            if location not in location_groups:
                location_groups[location] = []
            location_groups[location].append(miner.miner_ip)

        total_recorded = 0

        # Process each location group
        for location, miner_ips in location_groups.items():
            # Find active rate for this location
            rate = None
            for r in active_rates:
                if r.location == location or (not r.location and location == "default"):
                    rate = r
                    break

            if not rate:
                # Use first active rate as fallback
                rate = active_rates[0]

            # Get average power consumption for each miner in the period
            for miner_ip in miner_ips:
                # Query metrics for this miner in the period
                metrics = session.query(Metric).filter(
                    Metric.miner_ip == miner_ip,
                    Metric.timestamp >= period_start,
                    Metric.timestamp <= period_end
                ).all()

                if not metrics:
                    continue

                # Calculate average power
                avg_power_w = sum(m.power_w for m in metrics if m.power_w) / len(metrics)

                if avg_power_w == 0:
                    continue

                try:
                    # Record the cost for this miner
                    ElectricityCostService.record_cost(
                        session=session,
                        period_start=period_start,
                        period_end=period_end,
                        power_w=avg_power_w,
                        miner_ip=miner_ip,
                        location=location if location != "default" else None,
                        rate=rate
                    )
                    total_recorded += 1
                except Exception as e:
                    logger.warning(f"Failed to record cost for {miner_ip}: {e}")

        logger.info(f"Recorded electricity costs for {total_recorded} miners")

    except Exception as e:
        logger.exception("Electricity cost recording failed", exc_info=e)
    finally:
        session.close()


def process_firmware_jobs():
    """Run firmware flash job processing simulations."""
    session = SessionLocal()
    try:
        summary = FirmwareFlashService.process_jobs(session)
        if summary["checked"]:
            logger.debug(
                "firmware_jobs_processed",
                extra={"component": "scheduler", **summary},
            )
    except Exception:
        logger.exception("Firmware job processing failed")
    finally:
        session.close()


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

    # Electricity cost recording job (run every hour)
    scheduler.add_job(record_electricity_costs, 'interval', hours=1, id='record_electricity_costs')

    # Firmware flash job processor (run every minute)
    scheduler.add_job(process_firmware_jobs, 'interval', minutes=1, id='process_firmware_jobs')

    scheduler.add_listener(_job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)
    scheduler.start()

    print(f"Scheduler started:")
    print(f"  - Polling metrics every {POLL_INTERVAL}s")
    print(f"  - Checking alerts every 2 minutes")
    print(f"  - Calculating profitability every 15 minutes")
    print(f"  - Recording electricity costs every hour")

    return scheduler
