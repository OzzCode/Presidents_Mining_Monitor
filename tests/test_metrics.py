from datetime import datetime
import pytest
from flask import Flask
import api.endpoints as endpoints
from api.endpoints import api_bp, _normalize_since


# ---- Unit tests for helper ----

def test_normalize_since_naive():
    dt = _normalize_since('2025-07-31T12:00:00')
    assert dt.tzinfo is None  # naive UTC


def test_normalize_since_aware_z():
    dt = _normalize_since('2025-07-31T12:00:00Z')
    assert dt.tzinfo is None  # converted to naive UTC


def test_normalize_since_aware_offset():
    # 08:00 -04:00 should become 12:00 UTC (naive)
    dt = _normalize_since('2025-07-31T08:00:00-04:00')
    assert dt.tzinfo is None
    assert dt.hour == 12


# ---- Endpoint smoke test with fakes ----

class FakeRow:
    def __init__(self, ts, ip='192.168.1.100'):
        self.timestamp = ts
        self.miner_ip = ip
        self.power_w = 3300
        self.hashrate_ths = 95.0
        self.avg_temp_c = 70.0
        self.avg_fan_rpm = 6000


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


class FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def query(self, *args, **kwargs):
        return FakeQuery(self._rows)

    def close(self):
        pass


@pytest.fixture
def client(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    # build two rows
    rows = [
        FakeRow(datetime(2025, 7, 31, 12, 0, 0)),
        FakeRow(datetime(2025, 7, 31, 12, 0, 30)),
    ]
    monkeypatch.setattr(endpoints, 'SessionLocal', lambda: FakeSession(rows))
    return app.test_client()


def test_metrics_returns_rows(client):
    r = client.get('/api/metrics?limit=2')
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
