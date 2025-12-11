from flask import Flask
from flask_talisman import Talisman
from functools import wraps
import os

def configure_security(app: Flask):
    """Configure security headers and policies."""
    # Security headers middleware
    csp = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "'unsafe-inline'",  # Required for some Flask features
            "'unsafe-eval'",    # Required for some JS libraries
            'https://cdn.jsdelivr.net',  # Chart.js and other CDN libraries
            'https://api.coinbase.com'   # BTC price widget
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'"
        ],
        'img-src': ["'self'", 'data:', 'https:'],
        'font-src': ["'self'", 'data:'],
        'connect-src': [
            "'self'",
            'https://cdn.jsdelivr.net',
            'https://api.coinbase.com',
            'https://api.coingecko.com',
            'https://api.coincap.io'
        ]
    }
    
    # Initialize Talisman with security headers
    Talisman(
        app,
        force_https=app.config.get('FORCE_HTTPS', True),
        strict_transport_security=True,
        session_cookie_secure=True,
        session_cookie_http_only=True,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src'],
        x_content_type_options=True,
        x_xss_protection=True,
        frame_options='DENY',
        referrer_policy='strict-origin-when-cross-origin'
    )

def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = os.getenv('API_KEY')
        if not api_key:
            return {'error': 'API key not configured'}, 500
            
        # In a real app, validate the API key from request headers
        # For example: request.headers.get('X-API-Key') == api_key
        return f(*args, **kwargs)
    return decorated_function

def configure_cors(app):
    """Configure CORS with production-safe defaults."""
    allowed_origins = os.getenv('ALLOWED_ORIGINS', '').split(',')
    if not any(allowed_origins):
        allowed_origins = None  # Fall back to same-origin
        
    from flask_cors import CORS
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "supports_credentials": True
            }
        }
    )
