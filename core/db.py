# from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text
# from sqlalchemy.orm import sessionmaker, declarative_base
# from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
# import datetime as _dt
# from flask import Flask
# from flask_sqlalchemy import SQLAlchemy
# from pathlib import Path
#
# app = Flask(__name__)
#
# base_dir = Path(__file__).resolve().parent
# db_dir = base_dir / "/db_files/"
# db_dir.mkdir(parents=True, exist_ok=True)
#
# db_path = db_dir / "metrics.db"
# app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path.as_posix()}"
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
#
# db = SQLAlchemy(app)
#
# when_iso = _dt.datetime.utcnow().isoformat() + "Z"
#
# # SQLite database URL
# engine = create_engine('sqlite:///db_files/metrics.db', echo=False)
# SessionLocal = sessionmaker(bind=engine)
# Base = declarative_base()
#
#
# class Metric(Base):
#     __tablename__ = 'metrics'
#
#     id = Column(Integer, primary_key=True, index=True)
#     timestamp = Column(DateTime, default=_dt.datetime.now, index=True)
#     miner_ip = Column(String, index=True)
#     power_w = Column(Float)
#     hashrate_ths = Column(Float)
#     elapsed_s = Column(Integer)
#     avg_temp_c = Column(Float)
#     avg_fan_rpm = Column(Float)
#
#
# # NEW: lightweight event log
# class Event(Base):
#     __tablename__ = 'events'
#     id = Column(Integer, primary_key=True)
#     timestamp = Column(DateTime, default=_dt.datetime.now, index=True)
#     miner_ip = Column(String, index=True, nullable=True)  # may be None for app-level events
#     level = Column(String, default='INFO', index=True)  # INFO/WARN/ERROR
#     source = Column(String, default='app')  # 'app', 'miner-notify', etc.
#     message = Column(Text)  # full text
#
#
# class ErrorEvent(Base):
#     __tablename__ = "error_events"
#     id = Column(Integer, primary_key=True)
#     created_at = Column(DateTime, default=when_iso, index=True)
#     level = Column(String(10), index=True)
#     component = Column(String(32), index=True)
#     miner_ip = Column(String(64), nullable=True, index=True)
#     message = Column(Text)
#     context = Column(SQLITE_JSON)
#     traceback = Column(Text, nullable=True)

from __future__ import annotations
import datetime as _dt
from pathlib import Path
from sqlalchemy import (
    create_engine, event, Column, Integer, Float, String, DateTime, Text
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON

# -----------------------------------------------------------------------------
# Database location (single source of truth)
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "db_files"
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
def init_db():
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)
