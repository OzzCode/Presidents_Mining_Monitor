from flask import Flask, render_template, jsonify
from api.endpoints import api_bp
from scheduler import start_scheduler
from flask_cors import CORS
from dashboard.routes import dash_bp, get_miners
from werkzeug.exceptions import HTTPException

# Logging setup
from helpers.logging_setup import setup_logging
from helpers.logging_db_handler import DBHandler
from config import LOG_TO_DB, LOG_LEVEL

import logging  # added


def create_app():
    # Initialize logging early
    root_logger = setup_logging()
    if LOG_TO_DB:
        try:
            dbh = DBHandler()
            dbh.setLevel(LOG_LEVEL.upper() if isinstance(LOG_LEVEL, str) else 'INFO')
            root_logger.addHandler(dbh)
        except Exception:
            # Avoid breaking the app if DB logging can't be attached
            pass

    # Remove any console/stream handlers to prevent terminal output
    for h in list(root_logger.handlers):
        if isinstance(h, logging.StreamHandler):
            root_logger.removeHandler(h)

    # Silence werkzeug request logging to the console
    wlog = logging.getLogger('werkzeug')
    wlog.handlers = []
    wlog.propagate = False
    wlog.setLevel(logging.ERROR)

    app = Flask(__name__, static_url_path='/static', static_folder='static')
    CORS(app)

    # Ensure Flask app logger does not add its own console handlers
    app.logger.handlers.clear()
    app.logger.propagate = True

    app.register_blueprint(dash_bp, url_prefix="/dashboard")
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/api/miners")
    def api_miners():
        """
        Return the current miners list.

        The payload is a list[dict] with keys:
          - is_stale (bool)
          - age_sec (int)
          - status (str)
          - model (str)
          - ip (str)
          - last_seen (ISO string or timestamp)
        """
        try:
            miners = get_miners()
            if not isinstance(miners, list):
                return jsonify({"error": "get_miners() must return a list"}), 500
            return jsonify(miners), 200
        except Exception as e:
            # Avoid leaking internals; log in your real logger instead.
            return jsonify({"error": "Failed to fetch miners", "detail": str(e)}), 500

    @app.route("/dashboard/logs")
    def logs():
        return render_template("logs.html")

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
    start_scheduler()

    # Print a clean startup message with reachable URLs (no logger, just once)
    try:
        from core.get_network_ip import detect_primary_ipv4

        _lan_ip = detect_primary_ipv4() or '127.0.0.1'
    except Exception:
        _lan_ip = '127.0.0.1'
    print("App running:")
    print("  Local:    http://127.0.0.1:5000")
    print(f"  Network:  http://{_lan_ip}:5000")

    # On Windows, disable the reloader to avoid socket close races causing WinError 10038
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
