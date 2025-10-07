from __future__ import annotations
import datetime as _dt
from pathlib import Path
import sqlite3
from sqlalchemy import (
    create_engine, event, Column, Integer, Float, String, DateTime, Text, Boolean
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
