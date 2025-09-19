import os
import logging
from flask import Flask, request
from werkzeug.middleware.proxy_fix import ProxyFix

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "goldendoodlelm-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Email service configuration
app.config['SENDGRID_API_KEY'] = os.environ.get('SENDGRID_API_KEY')
app.config['SENDGRID_FROM_EMAIL'] = os.environ.get('SENDGRID_FROM_EMAIL')

# Crisp chat configuration
app.config['CRISP_WEBSITE_ID'] = os.environ.get('CRISP_WEBSITE_ID')
app.config['CRISP_API_KEY'] = os.environ.get('CRISP_API_KEY')

# Crisp Marketplace Plugin configuration
app.config['CRISP_MARKETPLACE_ID'] = os.environ.get('CRISP_MARKETPLACE_ID')
app.config['CRISP_MARKETPLACE_KEY'] = os.environ.get('CRISP_MARKETPLACE_KEY')

from database import init_databases
from auth import get_current_user
from analytics_service import analytics_service
from routes import *

# AUTOMATIC PAGE VIEW TRACKING FOR DAU/WAU
@app.before_request
def track_page_views():
    """Automatically track every page view for DAU/WAU metrics"""
    # Skip tracking for static files, favicons, etc.
    if (request.path.startswith('/static') or 
        request.path.startswith('/favicon') or 
        request.path.endswith('.css') or 
        request.path.endswith('.js') or
        request.path.endswith('.ico')):
        return

    # This creates your DAU/WAU data automatically
    analytics_service.track_page_view()

# Add security headers
@app.after_request
def add_security_headers(response):
    # Add Content Security Policy to allow inline scripts for development
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https: blob:; "
        "style-src 'self' 'unsafe-inline' https:; "
        "img-src 'self' data: https: blob:; "
        "font-src 'self' https: data:; "
        "connect-src 'self' https: wss: ws:; "
        "frame-src 'self' https:; "
        "worker-src 'self' blob:;"
    )
    return response

# Make get_current_user available in all templates
@app.context_processor
def inject_user():
    return dict(get_current_user=get_current_user)

if __name__ == '__main__':
    with app.app_context():
        init_databases()
    app.run(host='0.0.0.0', port=5001, debug=True)