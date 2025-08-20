#!/usr/bin/env python3

import os
import sys
from stripe_service import stripe_service
from database import db_manager
import logging
from datetime import datetime
from flask import request, Flask # Assuming Flask is used for routes

# --- Flask App Setup (Assuming this context for routes) ---
# If this is not a Flask app, the route decorators need to be adapted.
# For this example, we'll assume a Flask app instance named 'app' exists.
# If you are using a different framework, please adjust accordingly.
app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_stripe_configuration():
    """Test basic Stripe configuration"""
    print("=== STRIPE CONFIGURATION TEST ===")

    # Check environment variables
    env_vars = {
        'STRIPE_SECRET_KEY_TEST': os.environ.get("STRIPE_SECRET_KEY_TEST"),
        'STRIPE_PUBLISHABLE_KEY_TEST': os.environ.get("STRIPE_PUBLISHABLE_KEY_TEST"),
        'STRIPE_WEBHOOK_SECRET': os.environ.get("STRIPE_WEBHOOK_SECRET")
    }

    for key, value in env_vars.items():
        if value:
            print(f"✓ {key}: {value[:20]}...")
        else:
            print(f"❌ {key}: NOT SET")

    # Test service initialization
    print(f"✓ Test mode: {stripe_service.test_mode}")
    print(f"✓ Publishable key available: {bool(stripe_service.get_publishable_key())}")

    return all(env_vars.values())

def test_customer_creation():
    """Test creating a Stripe customer"""
    print("\n=== CUSTOMER CREATION TEST ===")

    try:
        customer = stripe_service.create_customer(
            email="test-debug@example.com",
            name="Debug Test User",
            metadata={'test': 'debug'}
        )

        if customer:
            print(f"✓ Customer created: {customer['id']}")
            return customer['id']
        else:
            print("❌ Customer creation failed")
            return None
    except Exception as e:
        print(f"❌ Customer creation error: {e}")
        return None

def test_checkout_session(customer_id=None):
    """Test creating a checkout session"""
    print("\n=== CHECKOUT SESSION TEST ===")

    try:
        base_url = "https://your-replit-url.replit.dev"  # Replace with actual URL

        session = stripe_service.create_checkout_session(
            customer_email="test-debug@example.com",
            price_id="price_1RvL44Hynku0jyEH12IrEJuI",  # Solo plan
            success_url=f"{base_url}/test-success",
            cancel_url=f"{base_url}/test-cancel",
            customer_id=customer_id,
            metadata={'test': 'debug'}
        )

        if session:
            print(f"✓ Checkout session created: {session['id']}")
            print(f"✓ Checkout URL: {session['url']}")
            return session
        else:
            print("❌ Checkout session creation failed")
            return None
    except Exception as e:
        print(f"❌ Checkout session error: {e}")
        return None

def test_database_connection():
    """Test database connection for user creation"""
    print("\n=== DATABASE CONNECTION TEST ===")

    try:
        # Test basic connection
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def main():
    print("STRIPE INTEGRATION DEBUGGING")
    print("=" * 50)

    # Test configuration
    config_ok = test_stripe_configuration()
    if not config_ok:
        print("\n❌ CRITICAL: Stripe not properly configured!")
        return

    # Test database
    db_ok = test_database_connection()
    if not db_ok:
        print("\n❌ CRITICAL: Database connection failed!")
        return

    # Test customer creation
    customer_id = test_customer_creation()

    # Test checkout session
    session = test_checkout_session(customer_id)

    print("\n=== SUMMARY ===")
    if config_ok and db_ok and customer_id and session:
        print("✓ All Stripe tests passed!")
        print("✓ Issue is likely in frontend JavaScript or error handling")
    else:
        print("❌ Some tests failed - check the output above")

@app.route('/debug-stripe-full')
def debug_stripe_full():
    """Comprehensive Stripe debugging endpoint"""
    try:
        import os
        import traceback

        # Environment check
        env_status = {
            'STRIPE_SECRET_KEY_TEST': 'Set' if os.environ.get("STRIPE_SECRET_KEY_TEST") else 'Not Set',
            'STRIPE_PUBLISHABLE_KEY_TEST': 'Set' if os.environ.get("STRIPE_PUBLISHABLE_KEY_TEST") else 'Not Set',
            'STRIPE_WEBHOOK_SECRET': 'Set' if os.environ.get("STRIPE_WEBHOOK_SECRET") else 'Not Set'
        }

        # Service status
        service_status = {
            'test_mode': stripe_service.test_mode,
            'publishable_key_available': bool(stripe_service.get_publishable_key()),
            'price_mapping': stripe_service.plan_price_mapping
        }

        # Database test
        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            db_status = "✓ Connected"
        except Exception as db_e:
            db_status = f"❌ Error: {str(db_e)}"

        # Customer creation test
        customer_test = "Not tested"
        customer_id = None
        try:
            test_customer = stripe_service.create_customer(
                email="debug@example.com",
                name="Debug User",
                metadata={'debug': 'true'}
            )
            if test_customer:
                customer_test = f"✓ Success: {test_customer['id']}"
                customer_id = test_customer['id']
            else:
                customer_test = "❌ Failed to create"
        except Exception as cust_e:
            customer_test = f"❌ Error: {str(cust_e)}"

        # Test each price ID individually
        price_tests = {}
        for plan_name, price_id in stripe_service.plan_price_mapping.items():
            try:
                base_url = request.url_root.rstrip('/')
                test_session = stripe_service.create_checkout_session(
                    customer_email="debug@example.com",
                    price_id=price_id,
                    success_url=f"{base_url}/test-success",
                    cancel_url=f"{base_url}/test-cancel",
                    customer_id=customer_id,
                    metadata={'debug': 'true', 'plan': plan_name}
                )
                if test_session and test_session.get('url'):
                    price_tests[plan_name] = f"✓ Success: {test_session['id'][:20]}... URL: {test_session['url'][:50]}..."
                else:
                    price_tests[plan_name] = "❌ No URL returned"
            except Exception as price_e:
                price_tests[plan_name] = f"❌ Error: {str(price_e)}"

        # Test registration flow simulation
        registration_test = "Not tested"
        try:
            # Simulate the exact registration flow
            base_url = request.url_root.rstrip('/')
            success_url = f"{base_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&new_user=test_user_123"
            cancel_url = f"{base_url}/register?payment_cancelled=true"

            reg_session = stripe_service.create_checkout_session(
                customer_email="registration-test@example.com",
                price_id='price_1RvL44Hynku0jyEH12IrEJuI',  # Solo plan
                success_url=success_url,
                cancel_url=cancel_url,
                customer_id=customer_id,
                metadata={
                    'user_id': 'test_user_123',
                    'plan_id': 'solo',
                    'new_registration': 'true',
                    'trial_days': '0'
                }
            )

            if reg_session and reg_session.get('url'):
                registration_test = f"✓ Success: Registration flow URL created"
            else:
                registration_test = "❌ Registration flow failed"

        except Exception as reg_e:
            registration_test = f"❌ Registration flow error: {str(reg_e)}"

        # Current URL info
        url_info = {
            'base_url': request.url_root.rstrip('/'),
            'host': request.host,
            'is_https': request.is_secure,
            'user_agent': request.headers.get('User-Agent', 'Unknown')[:50] + '...'
        }

        # Recent errors from logs (if available)
        recent_errors = "Check server logs for recent Stripe errors"

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Stripe Debug Report</title>
            <style>
                body {{ font-family: monospace; margin: 40px; line-height: 1.4; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ccc; border-radius: 5px; }}
                .success {{ color: green; }}
                .error {{ color: red; }}
                .warning {{ color: orange; }}
                pre {{ background: #f5f5f5; padding: 10px; overflow: auto; border-radius: 3px; }}
                .test-link {{
                    display: inline-block;
                    margin: 5px 10px 5px 0;
                    padding: 8px 12px;
                    background: #007cba;
                    color: white;
                    text-decoration: none;
                    border-radius: 3px;
                }}
                .test-link:hover {{ background: #005a87; }}
            </style>
        </head>
        <body>
            <h1>🔍 Comprehensive Stripe Debug Report</h1>
            <p><em>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}</em></p>

            <div class="section">
                <h2>🔧 Environment Variables</h2>
                <pre>{env_status}</pre>
            </div>

            <div class="section">
                <h2>⚙️ Service Configuration</h2>
                <pre>{service_status}</pre>
            </div>

            <div class="section">
                <h2>🗄️ Database Status</h2>
                <pre>{db_status}</pre>
            </div>

            <div class="section">
                <h2>👤 Customer Creation Test</h2>
                <pre>{customer_test}</pre>
            </div>

            <div class="section">
                <h2>💳 Price ID Tests (Individual)</h2>
                <pre>{chr(10).join([f"{plan}: {result}" for plan, result in price_tests.items()])}</pre>
            </div>

            <div class="section">
                <h2>📝 Registration Flow Test</h2>
                <pre>{registration_test}</pre>
            </div>

            <div class="section">
                <h2>🌐 URL Information</h2>
                <pre>{url_info}</pre>
            </div>

            <div class="section">
                <h2>🚀 Quick Tests</h2>
                <a href="/test-stripe-direct" class="test-link">🔗 Direct Checkout Test</a>
                <a href="/test-stripe" class="test-link">📊 API Response Test</a>
                <a href="/register" class="test-link">📋 Registration Page</a>
                <a href="/debug-stripe-webhook" class="test-link">🔔 Webhook Test</a>
            </div>

            <div class="section">
                <h2>📋 Troubleshooting Checklist</h2>
                <pre>
✅ Check if all price IDs exist in your Stripe Dashboard
✅ Verify that products are active (not archived)
✅ Confirm webhook endpoint is configured correctly
✅ Test with different browsers/devices
✅ Check browser console for JavaScript errors
✅ Verify success/cancel URLs are accessible
✅ Test in both test and live mode
                </pre>
            </div>

            <div class="section">
                <h2>🔄 Next Steps</h2>
                <p>1. If price ID tests fail, check your Stripe Dashboard</p>
                <p>2. If registration flow test fails, check URL formatting</p>
                <p>3. Test actual user registration with developer tools open</p>
                <p>4. Monitor server logs during checkout attempts</p>
            </div>
        </body>
        </html>
        '''

    except Exception as e:
        return f'''
        <html>
        <body style="font-family: monospace; margin: 40px;">
            <h1>🚨 Debug Tool Error</h1>
            <pre style="background: #ffebee; padding: 15px; border-radius: 5px;">Error: {str(e)}</pre>
            <pre style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin-top: 20px;">Traceback: {traceback.format_exc()}</pre>
        </body>
        </html>
        ''', 500

@app.route('/debug-stripe-webhook')
def debug_stripe_webhook():
    """Test webhook configuration"""
    try:
        webhook_status = {
            'webhook_secret_configured': bool(os.environ.get('STRIPE_WEBHOOK_SECRET')),
            'webhook_endpoint': f"{request.url_root.rstrip('/')}/stripe-webhook",
            'test_payload': 'Ready to receive webhook events'
        }

        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Webhook Debug</title>
            <style>
                body {{ font-family: monospace; margin: 40px; }}
                pre {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>🔔 Stripe Webhook Debug</h1>
            <pre>{webhook_status}</pre>
            <p><strong>Configure this endpoint in your Stripe Dashboard:</strong></p>
            <p><code>{request.url_root.rstrip('/')}/stripe-webhook</code></p>
            <p><strong>Events to listen for:</strong></p>
            <ul>
                <li>customer.subscription.created</li>
                <li>customer.subscription.updated</li>
                <li>customer.subscription.deleted</li>
                <li>invoice.payment_succeeded</li>
                <li>invoice.payment_failed</li>
            </ul>
        </body>
        </html>
        '''
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    # This part is for running the script directly, not as part of a web framework.
    # If this is a Flask app, you'd typically use app.run()
    # For demonstration purposes, we'll call main() if executed directly.
    # In a Flask app, the routes are registered and the app is run separately.
    
    # Example of how you might run this if it were a standalone script:
    # test_stripe_configuration()
    # test_customer_creation()
    # test_checkout_session()
    # test_database_connection()
    # main()

    # If this code is part of a larger Flask application, the routes defined above
    # will be automatically handled when the Flask app is run.
    # You might have a separate file like 'app.py' that imports this and runs it.
    # For example:
    # from your_module import app
    # if __name__ == '__main__':
    #     app.run(debug=True)
    pass # Keep this if the Flask app is managed elsewhere