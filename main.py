import uuid, time
from flask import Flask, render_template, g, request
from dashboard.routes import dash_bp
from api.endpoints import api_bp, log_event
from scheduler import start_scheduler

app = Flask(__name__, static_url_path='/static', static_folder='static')


@app.route('/')
def home():
    return render_template('home.html')


app.register_blueprint(dash_bp)
app.register_blueprint(api_bp)


# noinspection PyBroadException
@app.errorhandler(Exception)
def handle_exception(e):
    # Log and return a basic 500 JSON
    try:
        log_event("ERROR", f"flask unhandled: {repr(e)}", source="flask")
    except Exception:
        pass
    return {"ok": False, "error": "Internal Server Error"}, 500


start_scheduler()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
