import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

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

# Import routes after app creation to avoid circular imports
from routes import *
from database import init_databases
from auth import get_current_user

# Make get_current_user available in all templates
@app.context_processor
def inject_user():
    return dict(get_current_user=get_current_user)

if __name__ == '__main__':
    with app.app_context():
        init_databases()
    app.run(host='0.0.0.0', port=5000, debug=True)