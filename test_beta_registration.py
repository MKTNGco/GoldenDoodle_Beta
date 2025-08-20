
#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from invitation_manager import invitation_manager
from beta_trial_manager import beta_trial_manager
from database import db_manager

def test_beta_registration():
    """Test beta user registration flow"""
    
    # Test email
    test_email = "scott@goldendoodlelm.ai"
    
    print(f"Testing beta registration for: {test_email}")
    
    # Check if there's a beta invitation for this email
    invitations = invitation_manager.get_invitations_by_email(test_email)
    beta_invitations = [inv for inv in invitations if inv.get('invitation_type') == 'beta']
    
    print(f"Found {len(beta_invitations)} beta invitations for {test_email}")
    
    if beta_invitations:
        for inv in beta_invitations:
            print(f"  - Code: {inv['invite_code']}, Status: {inv['status']}")
    
    # Check if user exists
    user = db_manager.get_user_by_email(test_email)
    if user:
        print(f"User exists: {user.email}, Subscription: {user.subscription_level}, Admin: {user.is_admin}")
        
        # Check tenant info
        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if tenant:
            print(f"Tenant: {tenant.name}, Type: {tenant.tenant_type}, Max voices: {tenant.max_brand_voices}")
        
        # Check beta trial
        trial = beta_trial_manager.get_beta_trial(test_email)
        if trial:
            print(f"Beta trial: Status={trial['status']}, Days={trial['trial_days']}, Type={trial['trial_type']}")
            print(f"Trial end: {trial['trial_end']}")
        else:
            print("No beta trial found")
    else:
        print("User does not exist yet")

if __name__ == "__main__":
    test_beta_registration()
