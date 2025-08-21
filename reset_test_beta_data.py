
#!/usr/bin/env python3
"""
Script to reset test beta data for development (USE WITH CAUTION)
"""

from invitation_manager import invitation_manager
from beta_trial_manager import beta_trial_manager
from database import db_manager

def reset_test_beta_data():
    """Reset test beta data - USE ONLY IN DEVELOPMENT"""
    
    test_emails = [
        "scott+test1@goldendoodlelm.ai",
        "scott+test2@goldendoodlelm.ai",
        "test1@goldendoodlelm.ai",
        "test2@goldendoodlelm.ai"
    ]
    
    print("⚠️  WARNING: This will delete test users and their data!")
    confirm = input("Type 'DELETE TEST DATA' to confirm: ")
    
    if confirm != "DELETE TEST DATA":
        print("Operation cancelled")
        return
    
    for email in test_emails:
        try:
            # Get user
            user = db_manager.get_user_by_email(email)
            if user:
                print(f"Deleting user: {email}")
                # Delete user (this should cascade to tenant and other data)
                db_manager.delete_user(user.user_id)
                print(f"✓ Deleted user: {email}")
            else:
                print(f"User not found: {email}")
                
        except Exception as e:
            print(f"❌ Error deleting {email}: {e}")
    
    print("✓ Test data reset complete")

if __name__ == "__main__":
    reset_test_beta_data()
