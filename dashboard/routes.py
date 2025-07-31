from flask import Blueprint, render_template

dash_bp = Blueprint('dashboard', __name__)


@dash_bp.route('/')
def index():
    return render_template('index.html')


@dash_bp.route('/miners')
def show_miners():
    return render_template('miners.html')
