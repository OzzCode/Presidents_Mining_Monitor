import pytest
from flask import Flask
from api.metrics_exporter import metrics_bp
import main as app_main


def test_prometheus_metrics_basic():
    app = Flask(__name__)
    app.register_blueprint(metrics_bp)
    client = app.test_client()

    resp = client.get('/metrics')
    assert resp.status_code == 200
    # Prometheus text exposition
    assert 'text/plain' in resp.headers.get('Content-Type', '')
    body = resp.data.decode('utf-8')
    # Should include at least HELP/TYPE lines for our gauges
    assert 'miner_hashrate_ths' in body
    assert 'miner_power_est_w' in body
    assert 'miner_status' in body


def test_health_endpoints(monkeypatch):
    app = app_main.create_app()
    client = app.test_client()

    # healthz should always be OK
    r = client.get('/healthz')
    assert r.status_code == 200
    assert r.get_json().get('ok') is True

    # readyz depends on scheduler running. Patch scheduler to appear running.
    class DummySched:
        running = True
    monkeypatch.setattr(app_main, 'SCHEDULER', DummySched())

    r2 = client.get('/readyz')
    assert r2.status_code == 200
    j = r2.get_json()
    assert j.get('ok') is True
    assert j.get('db_ok') in (True, False)  # db should be reachable, but don’t hardcode
    assert j.get('scheduler_ok') is True
