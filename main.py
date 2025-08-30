from flask import Flask, render_template
# from dashboard.routes import dash_bp
from api.endpoints import api_bp, log_event
from core.db import init_db
from scheduler import start_scheduler
from flask_cors import CORS

app = Flask(__name__, static_url_path='/static', static_folder='static')


def create_app():
    app = Flask(__name__)
    CORS(app)
    app.register_blueprint(api_bp)

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/dashboard/")
    def dashboard():
        return render_template("dashboard.html")

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
    init_db()
    start_scheduler()
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
