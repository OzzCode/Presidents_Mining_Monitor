from flask import Flask, render_template
from api.endpoints import api_bp, log_event
from core.db import init_db
from dashboard.routes import dash_bp
from scheduler import start_scheduler
from flask_cors import CORS
import os


def create_app():
    app = Flask(__name__, static_url_path='/static', static_folder='static')
    CORS(app)
    app.register_blueprint(api_bp)

    @app.route("/")
    def home():
        return render_template("home.html")

    app.register_blueprint(dash_bp)

    @app.route("/dashboard/logs")
    def logs():
        return render_template("logs.html")

    # noinspection PyBroadException
    @app.errorhandler(Exception)
    def handle_exception(e):
        # Log and return a basic 500 JSON
        try:
            log_event("ERROR", f"flask unhandled: {repr(e)}", source="flask")
        except Exception:
            pass
        return {"ok": False, "error": "Internal Server Error"}, 500

    return app


if __name__ == '__main__':
    app = create_app()
    # Ensure DB is initialized with app context
    with app.app_context():
        init_db()

    # Start background scheduler only in the main serving process
    # Avoid duplicate threads when the reloader would spawn a child process
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        start_scheduler()

    # On Windows, disable the reloader to avoid socket close races causing WinError 10038
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
