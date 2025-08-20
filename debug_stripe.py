
#!/usr/bin/env python3

import os
import sys
from stripe_service import stripe_service
from database import db_manager
import logging

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

if __name__ == "__main__":
    main()
