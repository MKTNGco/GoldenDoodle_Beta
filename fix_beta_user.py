
#!/usr/bin/env python3
"""
Script to fix the beta user pge@mktng.co who has incorrect subscription and tenant settings
"""

import sys
from database import db_manager
from models import SubscriptionLevel, TenantType
from beta_trial_manager import beta_trial_manager

def fix_beta_user():
    email = "pge@mktng.co"
    
    print(f"Fixing beta user: {email}")
    
    # Get the user
    user = db_manager.get_user_by_email(email)
    if not user:
        print(f"User {email} not found!")
        return False
    
    print(f"Current user state:")
    print(f"  - Subscription Level: {user.subscription_level}")
    print(f"  - Is Admin: {user.is_admin}")
    print(f"  - Email Verified: {user.email_verified}")
    
    # Get the tenant
    tenant = db_manager.get_tenant_by_id(user.tenant_id)
    if not tenant:
        print(f"Tenant not found!")
        return False
    
    print(f"Current tenant state:")
    print(f"  - Name: {tenant.name}")
    print(f"  - Type: {tenant.tenant_type}")
    print(f"  - Max Brand Voices: {tenant.max_brand_voices}")
    
    # Check beta trial
    trial = beta_trial_manager.get_beta_trial(email)
    if trial:
        print(f"Beta trial exists: {trial}")
    else:
        print("No beta trial found")
    
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # Update user to team subscription and admin status
        cursor.execute("""
            UPDATE users 
            SET subscription_level = 'team', is_admin = true, plan_id = 'team'
            WHERE email = %s
        """, (email,))
        
        # Update tenant to company type with more brand voices
        cursor.execute("""
            UPDATE tenants 
            SET tenant_type = 'company', max_brand_voices = 10
            WHERE tenant_id = %s
        """, (user.tenant_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Successfully updated user and tenant")
        
        # Verify changes
        updated_user = db_manager.get_user_by_email(email)
        updated_tenant = db_manager.get_tenant_by_id(user.tenant_id)
        
        print(f"Updated user state:")
        print(f"  - Subscription Level: {updated_user.subscription_level}")
        print(f"  - Is Admin: {updated_user.is_admin}")
        
        print(f"Updated tenant state:")
        print(f"  - Type: {updated_tenant.tenant_type}")
        print(f"  - Max Brand Voices: {updated_tenant.max_brand_voices}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating user: {e}")
        return False

if __name__ == "__main__":
    success = fix_beta_user()
    sys.exit(0 if success else 1)
