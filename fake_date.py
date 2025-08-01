#!/usr/bin/env python3
"""
Populate SQLite with fake Antminer metrics for testing the History tab.
"""

import random
import datetime
from core.db import SessionLocal, Metric, engine, Base

# Ensure the table exists
Base.metadata.create_all(bind=engine)

# Configuration
NUM_ENTRIES = 240  # 2 hours @ 30 s intervals
INTERVAL_SEC = 30
START_TIME = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
MINER_IP = '192.168.1.100'  # the fake miner IP you can pass to /dashboard/?ip=<IP>

session = SessionLocal()
current = START_TIME

for _ in range(NUM_ENTRIES):
    m = Metric(
        miner_ip=MINER_IP,
        timestamp=current,
        power_w=random.uniform(3200, 3500),
        hashrate_ths=random.uniform(80, 100),  # in TH/s
        elapsed_s=int((current - datetime.datetime(1970, 1, 1)).total_seconds()),
        avg_temp_c=random.uniform(60, 75),
        avg_fan_rpm=random.uniform(5000, 7000)
    )
    session.add(m)
    current += datetime.timedelta(seconds=INTERVAL_SEC)

session.commit()
session.close()

print(f"✓ Inserted {NUM_ENTRIES} fake metrics for {MINER_IP}")
