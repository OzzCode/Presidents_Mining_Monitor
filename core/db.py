from __future__ import annotations
import datetime as _dt
from pathlib import Path
import sqlite3
from sqlalchemy import (
    create_engine, event, Column, Integer, Float, String, DateTime, Text, Boolean, ForeignKey, Index
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON

# -----------------------------------------------------------------------------
# Database location (single source of truth)
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_DIR = (BASE_DIR / "../db_files").resolve()
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "metrics.db"

# -----------------------------------------------------------------------------
# Engine (SQLite best practices for multithreaded app + scheduler)
# -----------------------------------------------------------------------------
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},  # scheduler + web threads
)


# Apply WAL & reasonable sync level for durability and concurrency
@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    cur = dbapi_connection.cursor()
    try:
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA busy_timeout=5000;")
        # Optional: reduce page cache misses a bit
        # cur.execute("PRAGMA cache_size=-20000;")  # ~20MB cache
    finally:
        cur.close()


# -----------------------------------------------------------------------------
# Session / Base
# -----------------------------------------------------------------------------
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = (
        # Composite index to speed up latest-row-per-miner queries
        Index("idx_metrics_miner_ip_timestamp", "miner_ip", "timestamp"),
    )

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=_dt.datetime.utcnow, index=True)
    miner_ip = Column(String, index=True)
    power_w = Column(Float)
    hashrate_ths = Column(Float)
    elapsed_s = Column(Integer)
    avg_temp_c = Column(Float)
    avg_fan_rpm = Column(Float)


class Miner(Base):
    """Static/durable metadata about a miner device (one row per device/IP)."""
    __tablename__ = "miners"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow, index=True)

    # Identity
    miner_ip = Column(String(64), unique=True, index=True, nullable=False)
    hostname = Column(String(255), nullable=True)
    vendor = Column(String(64), nullable=True)
    model = Column(String(128), nullable=True)
    serial_number = Column(String(128), nullable=True)
    firmware_version = Column(String(128), nullable=True)
    psu_model = Column(String(128), nullable=True)
    mac = Column(String(64), nullable=True)

    # Physical/location
    rack = Column(String(64), nullable=True)
    row = Column(String(64), nullable=True)
    location = Column(String(128), nullable=True)
    room = Column(String(64), nullable=True)
    owner = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)

    # Network
    mgmt_vlan = Column(String(32), nullable=True)
    gateway = Column(String(64), nullable=True)
    dns = Column(String(128), nullable=True)
    link_speed = Column(String(32), nullable=True)

    # Operational baseline
    nominal_ths = Column(Float, nullable=True)
    nominal_efficiency_j_per_th = Column(Float, nullable=True)
    power_cap_w = Column(Float, nullable=True)
    fan_mode = Column(String(32), nullable=True)
    auto_tune_enabled = Column(Boolean, nullable=True)

    # Pool info (current/default)
    pool_url = Column(String(255), nullable=True)
    worker_name = Column(String(255), nullable=True)
    pool_user = Column(String(255), nullable=True)
    region = Column(String(64), nullable=True)

    # Cost & context
    power_price_usd_per_kwh = Column(Float, nullable=True)
    tariff_plan = Column(String(64), nullable=True)
    time_zone = Column(String(64), nullable=True)
    carbon_region = Column(String(64), nullable=True)

    # Health snapshot-ish metadata (non time-series, last-known)
    board_count = Column(Integer, nullable=True)
    alive_boards = Column(Integer, nullable=True)
    avg_asic_temp_c = Column(Float, nullable=True)
    heatsink_temp_c = Column(Float, nullable=True)
    fan_count = Column(Integer, nullable=True)
    dead_fans = Column(Integer, nullable=True)
    last_reboot_at = Column(DateTime, nullable=True)
    uptime_s = Column(Integer, nullable=True)

    # Tagging
    tags = Column(SQLITE_JSON, nullable=True)


class Event(Base):
    """Lightweight app/miner event log (ERROR/WARN/INFO)."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=_dt.datetime.utcnow, index=True)
    miner_ip = Column(String, index=True, nullable=True)  # may be None for app-level events
    level = Column(String, default="INFO", index=True)  # INFO/WARN/ERROR
    source = Column(String, default="app")  # 'app', 'scheduler', 'miner-logs', etc.
    message = Column(Text)  # full text


class ErrorEvent(Base):
    """Richer error record with optional structured context + traceback."""
    __tablename__ = "error_events"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow, index=True)
    level = Column(String(10), index=True)  # e.g., ERROR, WARN
    component = Column(String(32), index=True)  # e.g., 'summary', 'scheduler'
    miner_ip = Column(String(64), nullable=True, index=True)
    message = Column(Text)
    context = Column(SQLITE_JSON, nullable=True)
    traceback = Column(Text, nullable=True)


class AlertRule(Base):
    """Configurable alert rules for miner monitoring."""
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    # Rule identification
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    rule_type = Column(String(32), nullable=False, index=True)  # 'offline', 'temp', 'hashrate', 'fan', 'power'
    enabled = Column(Boolean, default=True, index=True)

    # Scope (apply to all miners or specific ones)
    miner_ip = Column(String(64), nullable=True, index=True)  # None = apply to all miners
    model_filter = Column(String(128), nullable=True)  # e.g., "S19" to apply to all S19 models
    tags_filter = Column(SQLITE_JSON, nullable=True)  # filter by tags

    # Thresholds (JSON for flexibility)
    thresholds = Column(SQLITE_JSON, nullable=False)  # e.g., {"temp_c": 80, "duration_min": 5}

    # Alert configuration
    severity = Column(String(16), default='warning')  # 'info', 'warning', 'critical'
    cooldown_minutes = Column(Integer, default=30)  # time before re-alerting

    # Notification channels
    notify_email = Column(Boolean, default=True)
    notify_webhook = Column(Boolean, default=False)
    webhook_url = Column(String(512), nullable=True)

    # Auto-remediation
    auto_action = Column(String(32), nullable=True)  # 'reboot', 'reduce_power', None


class Alert(Base):
    """Alert instances triggered by alert rules."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    # Alert details
    rule_id = Column(Integer, nullable=True, index=True)  # FK to AlertRule (nullable for manual alerts)
    miner_ip = Column(String(64), nullable=False, index=True)
    alert_type = Column(String(32), nullable=False, index=True)
    severity = Column(String(16), nullable=False, index=True)

    # Message and context
    message = Column(Text, nullable=False)
    details = Column(SQLITE_JSON, nullable=True)  # additional context

    # Status tracking
    status = Column(String(16), default='active', index=True)  # 'active', 'acknowledged', 'resolved', 'auto_resolved'
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(64), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_note = Column(Text, nullable=True)

    # Notification tracking
    notified_at = Column(DateTime, nullable=True)
    notification_status = Column(String(32), nullable=True)  # 'sent', 'failed', 'pending'


class ProfitabilitySnapshot(Base):
    """Time-series profitability calculations."""
    __tablename__ = "profitability_snapshots"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=_dt.datetime.utcnow, index=True)
    miner_ip = Column(String(64), nullable=True, index=True)  # None = fleet-wide aggregate

    # BTC metrics
    btc_price_usd = Column(Float, nullable=False)
    network_difficulty = Column(Float, nullable=True)

    # Mining performance
    hashrate_ths = Column(Float, nullable=False)
    power_w = Column(Float, nullable=False)
    uptime_hours = Column(Float, default=24.0)

    # Revenue (in BTC and USD)
    estimated_btc_per_day = Column(Float, nullable=True)
    estimated_revenue_usd_per_day = Column(Float, nullable=True)

    # Costs
    power_cost_usd_per_kwh = Column(Float, nullable=False)
    daily_power_cost_usd = Column(Float, nullable=False)

    # Profitability
    daily_profit_usd = Column(Float, nullable=False)
    profit_margin_pct = Column(Float, nullable=True)
    break_even_btc_price = Column(Float, nullable=True)

    # Pool data (if available)
    pool_hashrate_ths = Column(Float, nullable=True)
    pool_workers = Column(Integer, nullable=True)
    shares_accepted = Column(Integer, nullable=True)
    shares_rejected = Column(Integer, nullable=True)


# -----------------------------------------------------------------------------
# Utility
# -----------------------------------------------------------------------------

def _quick_check(db_path: Path) -> bool:
    try:
        con = sqlite3.connect(str(db_path))
        cur = con.execute("PRAGMA quick_check;")
        res = cur.fetchone()
        con.close()
        return bool(res) and res[0] == "ok"
    except Exception:
        return False


def _quarantine_corrupt_files(db_path: Path) -> None:
    ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    base = db_path.with_suffix("")  # path without extension
    files = [
        db_path,
        db_path.with_name(db_path.name + "-wal"),
        db_path.with_name(db_path.name + "-shm"),
    ]
    for f in files:
        if f.exists():
            new_name = f.with_name(f.name + f".corrupt-{ts}")
            try:
                f.rename(new_name)
            except Exception:
                pass


def init_db():
    """Create tables; auto-recover if the existing DB appears corrupt.

    If PRAGMA quick_check fails or the file raises an error, the existing DB and
    its WAL/SHM siblings are renamed with a .corrupt-<timestamp> suffix, and a
    fresh database is created at the original path.
    """
    # If the file exists but quick_check fails, quarantine and recreate
    try:
        if DB_PATH.exists() and not _quick_check(DB_PATH):
            # Dispose current connections before file ops
            try:
                engine.dispose()
            except Exception:
                pass
            _quarantine_corrupt_files(DB_PATH)
    except Exception:
        # On any unexpected check error, fail open by attempting to recreate
        try:
            engine.dispose()
        except Exception:
            pass
        _quarantine_corrupt_files(DB_PATH)

    # Ensure directory exists and create tables
    DB_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


class User(Base):
    """Basic user auth + preferences for personalization."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow, index=True)

    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(256), nullable=False)

    # JSON blob for user personalization, e.g. {"favorite_miners": ["10.0.0.12"], "theme": "dark"}
    preferences = Column(SQLITE_JSON, nullable=True)


class ElectricityRate(Base):
    """Time-of-use electricity rate configuration."""
    __tablename__ = "electricity_rates"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    # Rate identification
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, index=True)

    # Location/scope
    location = Column(String(128), nullable=True)
    timezone = Column(String(64), default="UTC")

    # Rate structure
    rate_type = Column(String(32), default="flat")  # 'flat', 'tou', 'tiered'

    # Flat rate
    flat_rate_usd_per_kwh = Column(Float, nullable=True)

    # Time-of-use schedules (JSON)
    tou_schedule = Column(SQLITE_JSON, nullable=True)

    # Tiered pricing (JSON)
    tiered_rates = Column(SQLITE_JSON, nullable=True)

    # Additional charges
    daily_service_charge_usd = Column(Float, default=0.0)
    demand_charge_usd_per_kw = Column(Float, default=0.0)

    # Season dates
    season_start_month = Column(Integer, nullable=True)
    season_end_month = Column(Integer, nullable=True)

    # Metadata
    utility_name = Column(String(128), nullable=True)
    account_number = Column(String(128), nullable=True)
    notes = Column(Text, nullable=True)


class ElectricityCost(Base):
    """Time-series record of actual electricity costs."""
    __tablename__ = "electricity_costs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=_dt.datetime.utcnow, index=True)

    # Scope
    miner_ip = Column(String(64), nullable=True, index=True)
    location = Column(String(128), nullable=True, index=True)

    # Time period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    duration_hours = Column(Float, nullable=False)

    # Consumption
    total_kwh = Column(Float, nullable=False)
    avg_power_kw = Column(Float, nullable=True)
    peak_power_kw = Column(Float, nullable=True)

    # Rate applied
    rate_id = Column(Integer, nullable=True, index=True)
    rate_name = Column(String(128), nullable=True)
    avg_rate_usd_per_kwh = Column(Float, nullable=False)

    # Cost breakdown
    energy_cost_usd = Column(Float, nullable=False)
    demand_charge_usd = Column(Float, default=0.0)
    service_charge_usd = Column(Float, default=0.0)
    total_cost_usd = Column(Float, nullable=False)

    # TOU breakdown (JSON)
    tou_breakdown_usd = Column(SQLITE_JSON, nullable=True)


class PowerSchedule(Base):
    """Scheduled power on/off times for miners (optimize for TOU rates)."""
    __tablename__ = "power_schedules"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow)

    # Schedule identification
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, index=True)

    # Scope (which miners does this apply to?)
    miner_ip = Column(String(64), nullable=True, index=True)  # None = apply to all
    location = Column(String(128), nullable=True, index=True)
    tags_filter = Column(SQLITE_JSON, nullable=True)  # Filter by miner tags

    # Schedule type
    schedule_type = Column(String(32), default="weekly")  # 'weekly', 'daily', 'one-time'

    # Weekly schedule (JSON array of time periods)
    # [{"day": 0, "start_hour": 21, "end_hour": 7, "action": "off"}, ...]
    # day: 0=Monday, 6=Sunday
    weekly_schedule = Column(SQLITE_JSON, nullable=True)

    # One-time schedule
    one_time_start = Column(DateTime, nullable=True)
    one_time_end = Column(DateTime, nullable=True)
    one_time_action = Column(String(16), nullable=True)  # 'on' or 'off'

    # Power settings during 'on' periods
    power_limit_w = Column(Integer, nullable=True)  # Reduce power during expensive periods

    # Timezone for schedule
    timezone = Column(String(64), default="UTC")

    # Linked to electricity rate (optional)
    electricity_rate_id = Column(Integer, nullable=True)

    # Metadata
    created_by = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)


class FirmwareImage(Base):
    """Metadata for stored firmware images."""
    __tablename__ = "firmware_images"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow, index=True)

    file_name = Column(String(255), nullable=False)
    vendor = Column(String(64), nullable=True, index=True)
    model = Column(String(128), nullable=True, index=True)
    version = Column(String(128), nullable=True, index=True)
    checksum = Column(String(128), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String(512), nullable=False)
    notes = Column(Text, nullable=True)
    uploaded_by = Column(String(64), nullable=True)
    is_active = Column(Boolean, default=True, index=True)


class FirmwareFlashJob(Base):
    """Tracks firmware flashing operations against miners."""
    __tablename__ = "firmware_flash_jobs"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=_dt.datetime.utcnow, onupdate=_dt.datetime.utcnow, index=True)

    job_id = Column(String(64), unique=True, nullable=False, index=True)
    firmware_id = Column(Integer, ForeignKey("firmware_images.id"), nullable=False, index=True)
    miner_ip = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default="pending", index=True)  # pending, in_progress, success, failed
    progress = Column(Integer, default=0)  # 0-100
    initiated_by = Column(String(64), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    # Use a non-reserved Python attribute while keeping the DB column name "metadata"
    extra_metadata = Column("metadata", SQLITE_JSON, nullable=True)  # Additional context (e.g., firmware payload info)


class CommandHistory(Base):
    """Audit log of remote commands sent to miners."""
    __tablename__ = "command_history"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=_dt.datetime.utcnow, index=True)

    # Command details
    command_type = Column(String(32), nullable=False,
                          index=True)  # 'reboot', 'pool_switch', 'power_on', 'power_off', 'config_update'
    miner_ip = Column(String(64), nullable=False, index=True)

    # Command parameters (JSON)
    parameters = Column(SQLITE_JSON, nullable=True)

    # Execution details
    status = Column(String(32), default='pending', index=True)  # 'pending', 'success', 'failed', 'timeout'
    response = Column(SQLITE_JSON, nullable=True)  # Response from miner
    error_message = Column(Text, nullable=True)

    # Timing
    sent_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # User context
    initiated_by = Column(String(64), nullable=True)  # Username or 'system'
    source = Column(String(32), default='manual')  # 'manual', 'scheduled', 'automatic'

    # Batch operation tracking
    batch_id = Column(String(64), nullable=True, index=True)  # Group bulk operations


class MinerConfigBackup(Base):
    """Configuration backups for miners."""
    __tablename__ = "miner_config_backups"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=_dt.datetime.utcnow, index=True)

    # Miner identification
    miner_ip = Column(String(64), nullable=False, index=True)
    model = Column(String(128), nullable=True)
    firmware_version = Column(String(128), nullable=True)

    # Backup metadata
    backup_name = Column(String(128), nullable=True)
    description = Column(Text, nullable=True)
    backup_type = Column(String(32), default='manual')  # 'manual', 'automatic', 'pre_update'

    # Configuration data (JSON)
    # Includes pools, frequencies, voltage, fan settings, etc.
    config_data = Column(SQLITE_JSON, nullable=False)

    # Validation
    is_validated = Column(Boolean, default=False)  # Has this backup been tested?
    validated_at = Column(DateTime, nullable=True)

    # User context
    created_by = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
