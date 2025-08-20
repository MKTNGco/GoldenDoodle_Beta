
#!/usr/bin/env python3
"""
Configuration script for GoldenDoodleLM beta mode
"""

import os
import sys

def enable_beta_mode():
    """Enable beta mode by disabling Stripe"""
    print("🚀 Enabling Beta Mode...")
    print("- Disabling Stripe payment processing")
    print("- Users can register for any plan without payment")
    print("- All plans will be treated as free during beta")
    
    # This would typically set environment variables
    # In Replit, you would set this in the Secrets tab
    print("\n📝 To enable beta mode:")
    print("1. Go to the Secrets tab in Replit")
    print("2. Add a new secret: STRIPE_DISABLED = true")
    print("3. Restart your application")
    
    return True

def disable_beta_mode():
    """Disable beta mode by enabling Stripe"""
    print("💳 Disabling Beta Mode...")
    print("- Enabling Stripe payment processing")
    print("- Users will be charged for premium plans")
    
    print("\n📝 To disable beta mode:")
    print("1. Go to the Secrets tab in Replit")
    print("2. Remove the STRIPE_DISABLED secret or set it to 'false'")
    print("3. Restart your application")
    
    return True

def check_current_mode():
    """Check current mode"""
    stripe_disabled = os.environ.get('STRIPE_DISABLED', 'false').lower() == 'true'
    
    if stripe_disabled:
        print("🚀 Beta Mode is ENABLED")
        print("- Stripe is disabled")
        print("- Users can register without payment")
    else:
        print("💳 Production Mode is ENABLED")
        print("- Stripe is enabled")
        print("- Users will be charged for premium plans")
    
    return stripe_disabled

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python configure_beta.py [enable|disable|status]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "enable":
        enable_beta_mode()
    elif command == "disable":
        disable_beta_mode()
    elif command == "status":
        check_current_mode()
    else:
        print("Invalid command. Use: enable, disable, or status")
        sys.exit(1)
