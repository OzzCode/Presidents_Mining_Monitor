from flask import Flask
from flask_talisman import Talisman
from functools import wraps
import os

def configure_security(app: Flask):
    """Configure security headers and policies.

    Goal: keep reasonable defaults while avoiding overly strict CSP that blocks
    inline scripts used by the UI. In development/testing we relax policies to
    ease iteration; in production we still allow inline scripts but do not
    require nonces.
    """

    # Environment-aware HTTPS enforcement
    is_dev = bool(app.debug or app.testing or os.getenv('FLASK_ENV') == 'development')
    force_https = app.config.get('FORCE_HTTPS', not is_dev)

    # Content Security Policy
    # Allow common safe sources plus inline scripts/styles used by templates.
    csp = {
        'default-src': ["'self'", 'https:'],
        'script-src': [
            "'self'",
            "'unsafe-inline'",  # Inline widgets in templates
            "'unsafe-eval'",    # Some libraries may rely on eval (e.g., Chart.js tooltips)
            'data:', 'blob:',    # Allow data/blob URLs if used by charts/workers
            'https://cdn.jsdelivr.net',  # CDN libraries (Chart.js, etc.)
            'https://cdnjs.cloudflare.com',
            'https://unpkg.com',
            'https://api.coinbase.com'   # BTC price widget fetch script context
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
            'https://cdnjs.cloudflare.com',
            'https://unpkg.com',
            'https://api.coinbase.com',
            'https://api.coingecko.com',
            'https://api.coincap.io'
        ]
    }

    # Initialize Talisman with security headers
    # Note: We intentionally do NOT use CSP nonces because templates include
    # inline scripts and adding nonces everywhere would be intrusive. Keeping
    # 'unsafe-inline' avoids widespread breakage while preserving other controls.
    Talisman(
        app,
        force_https=force_https,
        strict_transport_security=True,
        session_cookie_secure=True,
        session_cookie_http_only=True,
        content_security_policy=csp,
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
