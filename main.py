from flask import Flask, render_template, jsonify
from api.endpoints import api_bp
from api.alerts_profitability import alerts_bp, profitability_bp
from scheduler import start_scheduler
from flask_cors import CORS
from dashboard.routes import dash_bp, get_miners
from werkzeug.exceptions import HTTPException

# Expose scheduler instance for readiness checks in tests/runtime
SCHEDULER = None


def create_app():
    app = Flask(__name__, static_url_path='/static', static_folder='static')
    CORS(app)

    app.register_blueprint(dash_bp, url_prefix="/dashboard")
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(alerts_bp)
    app.register_blueprint(profitability_bp)

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

    @app.route('/readyz')
    def readyz():
        # DB check: try to open and close a session
        try:
            from core.db import SessionLocal
            s = SessionLocal()
            s.execute("SELECT 1")
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
    app = create_app()
    # Ensure DB is initialized with app context
    if __name__ == "__main__":
        # Ensure DB is initialized if your app relies on it.
        try:
            from core.db import init_db

            init_db()
        except Exception:
            # Initialization may be optional depending on your routes
            pass

    # Start background scheduler (no reloader in this config, so safe)
    try:
        SCHEDULER = start_scheduler()
    except Exception:
        SCHEDULER = None

    # On Windows, disable the reloader to avoid socket close races causing WinError 10038
    app.run(host='0.0.0.0', port=5050, debug=True, use_reloader=False)
