from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
import datetime as _dt
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path

app = Flask(__name__)

base_dir = Path(__file__).resolve().parent
db_dir = base_dir / "/data_files/"
db_dir.mkdir(parents=True, exist_ok=True)

db_path = db_dir / "metrics.db"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path.as_posix()}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

when_iso = _dt.datetime.utcnow().isoformat() + "Z"

# SQLite database URL
engine = create_engine('sqlite:///db_files/metrics.db', echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Metric(Base):
    __tablename__ = 'metrics'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=_dt.datetime.now, index=True)
    miner_ip = Column(String, index=True)
    power_w = Column(Float)
    hashrate_ths = Column(Float)
    elapsed_s = Column(Integer)
    avg_temp_c = Column(Float)
    avg_fan_rpm = Column(Float)


# NEW: lightweight event log
class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=_dt.datetime.now, index=True)
    miner_ip = Column(String, index=True, nullable=True)  # may be None for app-level events
    level = Column(String, default='INFO', index=True)  # INFO/WARN/ERROR
    source = Column(String, default='app')  # 'app', 'miner-notify', etc.
    message = Column(Text)  # full text


class ErrorEvent(Base):
    __tablename__ = "error_events"
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=when_iso, index=True)
    level = Column(String(10), index=True)
    component = Column(String(32), index=True)
    miner_ip = Column(String(64), nullable=True, index=True)
    message = Column(Text)
    context = Column(SQLITE_JSON)
    traceback = Column(Text, nullable=True)
