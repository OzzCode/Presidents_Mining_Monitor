from flask import Flask, render_template
from dashboard.routes import dash_bp
from api.endpoints import api_bp
from scheduler import start_scheduler

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('home.html')


app.register_blueprint(dash_bp)
app.register_blueprint(api_bp)

start_scheduler()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
