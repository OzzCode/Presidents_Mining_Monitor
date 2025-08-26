from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Text, Index
from sqlalchemy.orm import sessionmaker, declarative_base
import datetime

# SQLite database URL
engine = create_engine('sqlite:///db_files/metrics.db', echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Metric(Base):
    __tablename__ = 'metrics'

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.now, index=True)
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
    timestamp = Column(DateTime, default=datetime.datetime.now, index=True)
    miner_ip = Column(String, index=True, nullable=True)   # may be None for app-level events
    level = Column(String, default='INFO', index=True)      # INFO/WARN/ERROR
    source = Column(String, default='app')                  # 'app', 'miner-notify', etc.
    message = Column(Text)                                  # full text
    
