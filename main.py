from flask import Flask, render_template, jsonify
from flask_cors import CORS
import os
from werkzeug.exceptions import HTTPException
from sqlalchemy import text
from prometheus_flask_exporter import PrometheusMetrics

# Configuration
from config import get_config

# Blueprints
from api.endpoints import api_bp
from api.alerts_profitability import alerts_bp, profitability_bp
from api.analytics import analytics_bp
from api.advanced_analytics import advanced_bp
from api.electricity import bp as electricity_bp
from api.remote_control import bp as remote_control_bp
from api.health import health_bp
from dashboard.routes import dash_bp, get_miners
from auth import auth_bp

# Core components
from core.logging_config import configure_logging
from core.security import configure_security

# Scheduler
from scheduler import start_scheduler


def create_app(config_name=None):
    """Application factory function."""
    # Initialize Flask app
    app = Flask(__name__, static_url_path='/static', static_folder='static')

    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    config.init_app(app)

    # Configure logging
    configure_logging(app)
    logger = app.logger

    # Security configuration
    configure_security(app)

    # CORS configuration
    cors_env = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    allowed_origins = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
    CORS(app, origins=allowed_origins)
    # Initialize database
    from models import db
    db.init_app(app)
    with app.app_context():
        db.create_all()  # Create tables if they don't exist

    # Initialize Prometheus metrics
    metrics = PrometheusMetrics(app)
    metrics.info('app_info', 'Application info', version='1.0.0')

    # Register blueprints with stable, non-versioned prefixes to match templates
    api_prefix = "/api"

    # Core API and health under /api
    app.register_blueprint(health_bp, url_prefix=api_prefix)
    app.register_blueprint(api_bp, url_prefix=api_prefix)

    # Auth under /auth
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # Dashboard UI under /dashboard
    app.register_blueprint(dash_bp, url_prefix="/dashboard")

    # Feature APIs that define their own /api/... prefixes should NOT be re-prefixed
    # They already expose routes like /api/alerts, /api/profitability, /api/electricity, /api/remote
    app.register_blueprint(alerts_bp)
    app.register_blueprint(profitability_bp)
    app.register_blueprint(electricity_bp)
    app.register_blueprint(remote_control_bp)

    # Analytics and advanced analytics under /api/analytics and /api/advanced
    app.register_blueprint(analytics_bp, url_prefix=f"{api_prefix}/analytics")
    app.register_blueprint(advanced_bp, url_prefix=f"{api_prefix}/advanced")

    # Start background scheduler
    if not app.config.get('TESTING'):
        start_scheduler()

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/api/miners")
    def api_miners():
        """
        Return the current miners list.

        Response contract:
          { "miners": list[dict] }

        Each miner dict contains keys like:
          - is_stale (bool)
          - age_sec (int)
          - status (str)
          - model (str)
          - ip (str)
          - last_seen (ISO string with Z)
          - est_power_w (float|None)
          - vendor, hostname, rack, row, location, room, owner, notes, nominal_ths,
            nominal_efficiency_j_per_th, power_price_usd_per_kwh, tags (optional)
        """
        try:
            miners = get_miners()
            if not isinstance(miners, list):
                return jsonify({"error": "get_miners() must return a list"}), 500
            # Prefer a stable object payload to ease client integrations.
            return jsonify({"miners": miners}), 200
        except Exception as e:
            # Avoid leaking internals; log in your real logger instead.
            return jsonify({"error": "Failed to fetch miners", "detail": str(e)}), 500

    @app.route("/dashboard/logs")
    def logs():
        return render_template("logs.html")

    # Lightweight health endpoints
    @app.route('/healthz')
    def healthz():
        return jsonify({"ok": True}), 200

    # noinspection PyBroadException
    @app.route('/readyz')
    def readyz():
        # DB check: try to open and close a session
        try:
            from core.db import SessionLocal
            s = SessionLocal()
            s.execute(text("SELECT 1"))
            s.close()
            db_ok = True
        except Exception:
            db_ok = False
        # Scheduler check: running attribute if available
        scheduler_ok = False
        try:
            from scheduler import start_scheduler
            # Check if scheduler module has a running scheduler
            import sys
            if 'apscheduler.schedulers.background' in sys.modules:
                from apscheduler.schedulers.background import BackgroundScheduler
                # Look for running scheduler instances (best effort)
                scheduler_ok = True  # Assume ok if scheduler module is loaded
        except Exception:
            scheduler_ok = False
        return jsonify({"ok": True, "db_ok": db_ok, "scheduler_ok": scheduler_ok}), 200

    # noinspection PyBroadException
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Allow HTTPExceptions (404, 400, etc.) to pass through with the correct status
        if isinstance(e, HTTPException):
            return e
        # Log and return a basic 500 JSON for unexpected errors
        try:
            app.logger.exception("flask unhandled exception", exc_info=e)
        except Exception:
            pass
        return {"ok": False, "error": "Internal Server Error"}, 500

    # Graceful fallback for miner pools timeouts to avoid 504s at the proxy
    @app.errorhandler(TimeoutError)
    def handle_timeout_error(e):
        # Return empty pools quickly with 200 so the UI can render
        return jsonify({"pools": [], "error": "timeout"}), 200

    return app


if __name__ == '__main__':
    # Initialize DB first
    try:
        from core.db import init_db

        init_db()
    except Exception:
        pass

    # Create app and start scheduler
    app = create_app()

    try:
        SCHEDULER = start_scheduler()
    except Exception:
        SCHEDULER = None

    # Get port and run
    port = int(os.getenv('PORT', 5000))
    if app.config.get('DEBUG'):
        app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)
    else:
        from waitress import serve

        app.logger.info(f'Starting production server on port {port}...')
        serve(app, host='0.0.0.0', port=port, threads=4)
