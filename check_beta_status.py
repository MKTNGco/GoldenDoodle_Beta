
#!/usr/bin/env python3
"""
Script to check the status of beta invitations and users
"""

from invitation_manager import invitation_manager
from beta_trial_manager import beta_trial_manager
from database import db_manager

def check_beta_status():
    """Check current beta invitation and user status"""
    
    print("=== BETA INVITATION STATUS ===")
    
    # Get all beta invitations
    beta_invitations = invitation_manager.get_invitations_by_type('beta')
    
    print(f"Total beta invitations: {len(beta_invitations)}")
    
    for inv in beta_invitations:
        print(f"Email: {inv['invitee_email']}")
        print(f"Code: {inv['invite_code']}")
        print(f"Status: {inv['status']}")
        print(f"Organization: {inv['organization_name']}")
        print(f"Created: {inv['created_at']}")
        
        # Check if user exists
        user = db_manager.get_user_by_email(inv['invitee_email'])
        if user:
            print(f"✓ User registered: {user.subscription_level}")
            # Check beta trial
            trial = beta_trial_manager.get_beta_trial(inv['invitee_email'])
            if trial:
                print(f"✓ Beta trial: {trial['status']} (ends: {trial['trial_end']})")
            else:
                print("❌ No beta trial found")
        else:
            print("❌ User not registered yet")
        
        print("---")
    
    print("\n=== BETA TRIAL STATISTICS ===")
    trial_stats = beta_trial_manager.get_beta_trial_stats()
    print(f"Active trials: {trial_stats.get('active_trials', 0)}")
    print(f"Total trials: {trial_stats.get('total_trials', 0)}")
    print(f"Expired trials: {trial_stats.get('expired_trials', 0)}")

if __name__ == "__main__":
    check_beta_status()
