#!/usr/bin/env python3
"""
Runner script for GoldenDoodleLM with environment variables
"""
import os
import sys

# Set environment variables BEFORE any other imports
os.environ['SESSION_SECRET'] = "ppK/clC9+qI4ewvXlGviksVJNvQFzgQp1teOT4WPBXsQ68hMgaWpdB4zj2fpq2i3D8rlnlPWVLTcDpgmPhM3lQ=="
os.environ['DATABASE_URL'] = "postgresql://neondb_owner:npg_vc9gITCbSw4o@ep-silent-glitter-a54ivu6n.us-east-2.aws.neon.tech/neondb?sslmode=require"
os.environ['PGDATABASE'] = "neondb"
os.environ['PGHOST'] = "ep-silent-glitter-a54ivu6n.us-east-2.aws.neon.tech"
os.environ['PGPORT'] = "5432"
os.environ['PGUSER'] = "neondb_owner"
os.environ['PGPASSWORD'] = "npg_vc9gITCbSw4o"
os.environ['BASE_URL'] = "https://goldendoodlelm.replit.app"
os.environ['SENDGRID_FROM_NAME'] = "GoldenDoodleLM Team"
os.environ['SENDGRID_FROM_EMAIL'] = "hassanshakoor308@gmail.com"
os.environ['MAIL_DEFAULT_SENDER'] = "GoldenDoodleLM <hassanshakoor308@gmail.com>"
os.environ['MAIL_PASSWORD'] = "bdcijjcolrbrlqop"
os.environ['MAIL_USERNAME'] = "hassanshakoor308@gmail.com"
os.environ['MAIL_USE_TLS'] = "true"
os.environ['MAIL_PORT'] = "587"
os.environ['MAIL_SERVER'] = "smtp.gmail.com"
os.environ['STRIPE_PUBLISHABLE_KEY_TEST'] = "pk_test_51RvJi4Hynku0jyEHqlqc2tqw8rwMD8cGWgv3Xl0aN65hvO35UMC1ome5AZF8hNlS9gmKIxltMnuo745QcMJUt0ao00t0wT6xKk"
os.environ['STRIPE_SECRET_KEY_TEST'] = "sk_test_51RvJi4Hynku0jyEHxxWRohw4ihvUmiDTIaDT9vRQzPsIzJg3piTduklOeIemUQ4HRUg2e5c0Xalr0ZW5SRmbHmno00V3BzIAwJ"
os.environ['STRIPE_WEBHOOK_SECRET'] = "whsec_RSFCjjUjziaxm7Qlic3Q3Bk5QbmFaD9E"
os.environ['POSTHOG_API_KEY'] = "phc_kzVGXsZAW8fpD38LMIpTHbC8lLWScokrTM6HUxWZ64u"
os.environ['STRIPE_DISABLED'] = "true"
os.environ['CRISP_WEBSITE_ID'] = "4b0e8211-783b-4a70-a1ff-d86eb1289958"
os.environ['CRISP_MARKETPLACE_ID'] = "54d7f6c0-5f86-49a3-90e5-1b159a7f0f30"
os.environ['CRISP_MARKETPLACE_KEY'] = "f4c98b6f13368e9e67ce31b04f8dac120879a6c134a7b9162654d68892064936"
os.environ['CRISP_WEBHOOK_SIGNING_SECRET'] = "cd29906cada3ca89ecdf5a5a233c5111"
os.environ['GOOGLE_API_KEY'] = "AIzaSyAFILczEWk44lC6FP3JmKnxjXwsSHg0rB0"
os.environ['GEMINI_API_KEY'] = "AIzaSyAFILczEWk44lC6FP3JmKnxjXwsSHg0rB0"
os.environ['SENDGRID_API_KEY'] = "dummy-sendgrid-api-key"
os.environ['STRIPE_PUBLIC_KEY'] = "dummy-stripe-public-key"
os.environ['STRIPE_SECRET_KEY'] = "dummy-stripe-secret-key"
os.environ['CRISP_API_KEY'] = "dummy-crisp-api-key"

print("🚀 Starting GoldenDoodleLM with environment variables set...")
print("📊 Database URL configured")
print("🔑 Session secret configured")
print("📧 Email service configured")
print("💳 Stripe configured (disabled)")
print("📈 Analytics configured")
print("💬 Crisp chat configured")
print("🤖 Google API key set (test mode)")

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
        print("🌐 Starting Flask server on http://localhost:6000")
        app.run(host='0.0.0.0', port=6000, debug=True)
        
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)
