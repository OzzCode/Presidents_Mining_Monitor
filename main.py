from flask import Flask
from core.miner import MinerClient
from dashboard.routes import dash_bp
from api.endpoints import api_bp

app = Flask(__name__)
app.register_blueprint(dash_bp)
app.register_blueprint(api_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
