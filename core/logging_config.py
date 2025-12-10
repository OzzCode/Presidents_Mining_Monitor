import os
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
from pythonjsonlogger import jsonlogger
from flask import request

class RequestFormatter(jsonlogger.JsonFormatter):
    """Custom formatter that includes request details in logs."""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if request:
            log_record['url'] = request.url
            log_record['method'] = request.method
            log_record['ip'] = request.remote_addr
        else:
            log_record['url'] = None
            log_record['method'] = None
            log_record['ip'] = None

def configure_logging(app):
    """Configure application logging."""
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # JSON formatter for structured logging
    formatter = RequestFormatter(
        '%(asctime)s %(levelname)s %(name)s %(message)s %(url)s %(method)s %(ip)s',
        datefmt='%Y-%m-%dT%H:%M:%S%z'
    )
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if app.debug else logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
    
    # Remove all handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    root_logger.addHandler(file_handler)
    
    # Only add console handler in development
    if app.debug or app.testing:
        root_logger.addHandler(console_handler)
    
    # Configure SQLAlchemy logging
    if app.debug:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    else:
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Disable noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('werkzeug').setLevel(logging.WARNING if not app.debug else logging.INFO)
    
    # Add request logging
    @app.after_request
    def after_request(response):
        """Log all requests."""
        if request.path == '/health' or request.path.startswith('/static/'):
            return response
            
        logger = logging.getLogger('app.request')
        logger.info(
            '%s %s %s %s %s',
            request.remote_addr,
            request.method,
            request.scheme,
            request.full_path,
            response.status_code,
            extra={
                'request': {
                    'remote_addr': request.remote_addr,
                    'method': request.method,
                    'url': request.url,
                    'user_agent': request.user_agent.string,
                    'args': dict(request.args),
                    'form': dict(request.form) if request.form else None,
                    'json': request.get_json(silent=True),
                },
                'response': {
                    'status_code': response.status_code,
                    'content_length': response.content_length,
                    'mimetype': response.mimetype,
                },
            }
        )
        return response
    
    return app
