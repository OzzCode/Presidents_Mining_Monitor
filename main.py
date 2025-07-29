from flask import Flask
from dashboard.routes import dash_bp
from api.endpoints import api_bp
from scheduler import start_scheduler

# Initialize Flask app and register blueprints
app = Flask(__name__)
app.register_blueprint(dash_bp)
app.register_blueprint(api_bp)

# Start a background polling scheduler before handling requests
start_scheduler()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
