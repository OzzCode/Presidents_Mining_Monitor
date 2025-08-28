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


# @app.before_request
# def _begin():
#     g.req_id = str(uuid.uuid4())[:8]
#     g.req_ts = time.time()
#
#
# from logging_setup import setup_logging
#
# logger = setup_logging("antminer_monitor")
#
# from config import LOG_TO_DB
#
# if LOG_TO_DB:
#     import logging
#     from helpers.logging_db_handler import DBHandler
#
#     logging.getLogger().addHandler(DBHandler())
#
#
# @app.after_request
# def _end(resp):
#     elapsed = (time.time() - getattr(g, "req_ts", time.time())) * 1000
#     logger.info("http_request", extra={
#         "component": "api", "path": request.path, "endpoint": request.endpoint, "job_id": g.req_id,
#     })
#     resp.headers["X-Request-ID"] = g.req_id
#     resp.headers["X-Elapsed-ms"] = f"{elapsed:.1f}"
#     return resp


start_scheduler()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
