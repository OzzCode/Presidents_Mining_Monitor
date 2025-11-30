from flask import Blueprint, jsonify
import psutil
import os
import platform
import socket
from datetime import datetime
from models import db

health_bp = Blueprint('health', __name__)

def get_system_status():
    """Get system status information."""
    try:
        # Database connection check
        db_status = 'ok'
        try:
            db.session.execute('SELECT 1')
        except Exception as e:
            db_status = str(e)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # System info
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'system': {
                'platform': platform.system(),
                'hostname': socket.gethostname(),
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'process_memory': psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024,  # MB
            },
            'services': {
                'database': db_status,
                'disk_space': {
                    'total_gb': round(disk.total / (1024 ** 3), 2),
                    'used_gb': round(disk.used / (1024 ** 3), 2),
                    'free_gb': round(disk.free / (1024 ** 3), 2),
                    'percent_used': disk.percent
                }
            },
            'version': os.getenv('APP_VERSION', '1.0.0')
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

@health_bp.route('/health')
def health_check():
    """Health check endpoint for load balancers and monitoring."""
    status = get_system_status()
    status_code = 200 if status.get('status') == 'healthy' else 503
    return jsonify(status), status_code

@health_bp.route('/ready')
def readiness_check():
    """Readiness check for Kubernetes and other orchestrators."""
    # Check database connection
    try:
        db.session.execute('SELECT 1')
        return jsonify({'status': 'ready'}), 200
    except Exception as e:
        return jsonify({
            'status': 'not ready',
            'error': str(e)
        }), 503
