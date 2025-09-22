#!/usr/bin/env python3
"""
Replit runner script for GoldenDoodleLM
This script loads environment variables from Replit's secrets and runs the app
"""
import os
import sys

print("🚀 Starting GoldenDoodleLM on Replit...")

# Check if BASE_URL is set correctly
base_url = os.environ.get('BASE_URL', 'https://goldendoodlelm.replit.app')
print(f"📊 BASE_URL: {base_url}")

# Check if required environment variables are set
required_vars = [
    'DATABASE_URL',
    'SESSION_SECRET', 
    'SENDGRID_API_KEY',
    'GOOGLE_API_KEY'
]

missing_vars = []
for var in required_vars:
    if not os.environ.get(var):
        missing_vars.append(var)

if missing_vars:
    print(f"❌ Missing required environment variables: {missing_vars}")
    print("Please set these in Replit's Secrets tab")
    sys.exit(1)

print("✅ All required environment variables are set")

# Import and run the Flask app
if __name__ == '__main__':
    try:
        from app import app
        from database import db_manager
        
        # Ensure all database tables exist on startup
        try:
            db_manager.ensure_chat_tables_exist()
            print("✓ Chat tables verified/created")
        except Exception as e:
            print(f"⚠️  Warning: Could not ensure chat tables exist: {e}")
        
        # Start the Flask server
        port = int(os.environ.get('PORT', 8080))
        print(f"🌐 Starting Flask server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)
