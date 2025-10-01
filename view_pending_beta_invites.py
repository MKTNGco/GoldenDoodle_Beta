
"""
View all pending beta invitations
"""
from invitation_manager import invitation_manager
from datetime import datetime

def view_pending_beta_invites():
    """View all pending beta invitations"""
    
    # Get all beta invitations
    all_invitations = invitation_manager.get_invitations_by_type('beta')
    
    # Filter for pending ones
    pending = [inv for inv in all_invitations if inv.get('status') == 'pending']
    
    print(f"\n{'='*80}")
    print(f"PENDING BETA INVITATIONS: {len(pending)}")
    print(f"{'='*80}\n")
    
    if not pending:
        print("No pending beta invitations found.")
        return
    
    for inv in pending:
        print(f"Email: {inv['invitee_email']}")
        print(f"Organization: {inv['organization_name']}")
        print(f"Invite Code: {inv['invite_code']}")
        print(f"Created: {inv['created_at']}")
        print(f"Status: {inv['status']}")
        
        # Check if expired
        created = datetime.fromisoformat(inv['created_at'])
        age_days = (datetime.now() - created).days
        print(f"Age: {age_days} days")
        
        print("-" * 80)
    
    print(f"\nTotal pending invitations: {len(pending)}")
    
    # Show invitation stats
    stats = invitation_manager.get_invitation_stats()
    print(f"\nOverall Stats:")
    print(f"  Total: {stats['total_invitations']}")
    print(f"  Pending: {stats['pending_invitations']}")
    print(f"  Accepted: {stats['accepted_invitations']}")
    print(f"  Acceptance Rate: {stats['acceptance_rate']}%")

if __name__ == "__main__":
    view_pending_beta_invites()
