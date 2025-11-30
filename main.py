import os
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
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
from core.security import configure_security, configure_cors

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
    configure_cors(app)

    # Initialize database
    from models import db
    db.init_app(app)
    with app.app_context():
        db.create_all()  # Create tables if they don't exist

    # Initialize Prometheus metrics
    metrics = PrometheusMetrics(app)
    metrics.info('app_info', 'Application info', version='1.0.0')

    # Register blueprints with proper URL prefixes
    api_prefix = f"/{app.config.get('API_PREFIX', 'api').strip('/')}/{app.config.get('API_VERSION', 'v1')}"

    app.register_blueprint(health_bp, url_prefix=api_prefix)
    app.register_blueprint(auth_bp, url_prefix=f"{api_prefix}/auth")
    app.register_blueprint(dash_bp, url_prefix=f"{api_prefix}/dashboard")
    app.register_blueprint(api_bp, url_prefix=api_prefix)
    app.register_blueprint(alerts_bp, url_prefix=api_prefix)
    app.register_blueprint(profitability_bp, url_prefix=api_prefix)
    app.register_blueprint(analytics_bp, url_prefix=f"{api_prefix}/analytics")
    app.register_blueprint(advanced_bp, url_prefix=f"{api_prefix}/advanced")
    app.register_blueprint(electricity_bp, url_prefix=f"{api_prefix}/electricity")
    app.register_blueprint(remote_control_bp, url_prefix=f"{api_prefix}/remote")

    # Initialize database tables
    with app.app_context():
        db.create_all()

    # Start background scheduler
    if not app.config.get('TESTING'):
        start_scheduler(app)

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
        try:
            scheduler_ok = bool(getattr(SCHEDULER, 'running', False))
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
    # Create application instance
    app = create_app()

    # Get port from environment variable or use default
    port = int(os.getenv('PORT', 5000))

    # Run the application
    if app.config.get('DEBUG'):
        app.run(host='0.0.0.0', port=port, debug=True)
    else:
        # In production, use Waitress
        from waitress import serve

        app.logger.info(f'Starting production server on port {port}...')
        serve(app, host='0.0.0.0', port=port, threads=4)

    # Ensure DB is initialized with app context
    if __name__ == "__main__":
        # Ensure DB is initialized if your app relies on it.
        # noinspection PyBroadException
        try:
            from core.db import init_db

            init_db()
        except Exception:
            # Initialization may be optional depending on your routes
            pass

    # Start background scheduler (no reloader in this config, so safe)
    # noinspection PyBroadException
    try:
        SCHEDULER = start_scheduler()
    except Exception:
        SCHEDULER = None
    # On Windows, disable the reloader to avoid socket close races causing WinError 10038
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
