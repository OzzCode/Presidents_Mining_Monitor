from flask import Blueprint, render_template, request, jsonify

dash_bp = Blueprint('dashboard', __name__)

api_bp = Blueprint("api", __name__)


def get_miners():
    """
    Replace this with your real data retrieval.
    Must return a list of dicts with keys:
    - is_stale (bool)
    - age_sec (int)
    - status (str)
    - model (str)
    - ip (str)
    - last_seen (ISO string or timestamp)
    """
    # Example structure; integrate with your DB/service layer instead.
    return []


@api_bp.get("/miners")
def miners():
    miners = get_miners()
    # Ensure a consistent response contract expected by miners.js
    return jsonify({"miners": miners})


@dash_bp.route('/')
def index():
    ip = request.args.get('ip')
    return render_template('dashboard.html', ip=ip)


@dash_bp.route('/miners')
def show_miners():
    return render_template('miners.html')


@dash_bp.route("/logs")
def logs_page():
    return render_template("logs.html")

