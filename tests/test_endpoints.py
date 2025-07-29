import pytest
from flask import Flask
import api.endpoints as endpoints
from api.endpoints import api_bp


@pytest.fixture
def client():
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    return app.test_client()


@pytest.fixture(autouse=True)
def patch_discover_miners(monkeypatch):
    monkeypatch.setattr(endpoints, 'discover_miners', lambda *args, **kwargs: [])
    return None


@pytest.fixture(autouse=True)
def patch_minerclient(monkeypatch):
    class DummyClient:
        def __init__(self, ip, port=4028, timeout=5):
            pass

        def get_summary(self):
            return {'power': 0, 'MHS 5s': 0, 'Elapsed': 0, 'temp': [], 'fan': [], 'When': '0'}

    monkeypatch.setattr(endpoints, 'MinerClient', DummyClient)
    return None


def test_summary_no_miners(client):
    response = client.get('/api/summary')
    assert response.status_code == 200
    data = response.get_json()
    assert data['total_power'] == 0
    assert data['total_hashrate'] == 0
    assert data['total_workers'] == 0
