
#!/usr/bin/env python3
"""
Script to fix existing beta users who have incorrect subscription and tenant settings
"""

import sys
from database import db_manager
from models import SubscriptionLevel, TenantType
from beta_trial_manager import beta_trial_manager
from invitation_manager import invitation_manager

def fix_all_beta_users():
    """Fix all users who registered via beta invitations but have wrong settings"""
    
    print("=== FIXING BETA USERS ===")
    
    # Get all beta invitations that were accepted
    beta_invitations = invitation_manager.get_invitations_by_type('beta')
    accepted_beta_invites = [inv for inv in beta_invitations if inv['status'] == 'accepted']
    
    print(f"Found {len(accepted_beta_invites)} accepted beta invitations")
    
    fixed_count = 0
    
    for invite in accepted_beta_invites:
        email = invite['invitee_email']
        print(f"\nChecking user: {email}")
        
        user = db_manager.get_user_by_email(email)
        if not user:
            print(f"  ❌ User not found for {email}")
            continue
            
        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if not tenant:
            print(f"  ❌ Tenant not found for {email}")
            continue
            
        print(f"  Current state: {user.subscription_level}, Admin: {user.is_admin}")
        print(f"  Tenant: {tenant.name}, Type: {tenant.tenant_type}, Max voices: {tenant.max_brand_voices}")
        
        # Check if user needs fixing
        needs_fixing = (
            user.subscription_level != SubscriptionLevel.TEAM or
            not user.is_admin or
            tenant.tenant_type != TenantType.COMPANY or
            tenant.max_brand_voices < 10
        )
        
        if not needs_fixing:
            print(f"  ✓ User {email} is already correctly configured")
            continue
            
        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # Update user to team subscription and admin status
            cursor.execute("""
                UPDATE users 
                SET subscription_level = 'team', is_admin = true, plan_id = 'team'
                WHERE user_id = %s
            """, (user.user_id,))
            
            # Update tenant to company type with more brand voices
            cursor.execute("""
                UPDATE tenants 
                SET tenant_type = 'company', max_brand_voices = 10,
                    name = CASE 
                        WHEN name LIKE '%Personal Account' OR name LIKE '%''s Account' 
                        THEN %s
                        ELSE name 
                    END
                WHERE tenant_id = %s
            """, (f"{user.first_name} {user.last_name}'s Beta Organization", user.tenant_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"  ✅ Fixed user {email}")
            fixed_count += 1
            
        except Exception as e:
            print(f"  ❌ Error fixing user {email}: {e}")
            
    print(f"\n=== SUMMARY ===")
    print(f"Fixed {fixed_count} beta users")

if __name__ == "__main__":
    fix_all_beta_users()
