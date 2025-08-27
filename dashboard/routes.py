from flask import Blueprint, render_template, request

dash_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


@dash_bp.route('/')
def index():
    ip = request.args.get('ip')
    return render_template('dashboard.html', ip=ip)


@dash_bp.route('/miners')
def show_miners():
    return render_template('miners.html')


# @dash_bp.route('/logs')
# def view_logs():
#     # optional: pass ?ip=... to filter
#     return render_template('logs.html')


@dash_bp.route("/logs")
def logs_page():
    return render_template("logs.html")
