
#!/usr/bin/env python3
"""
Fix Sharon's beta invitation by adding/updating the organization name
"""

from invitation_manager import invitation_manager
from database import DatabaseManager

def fix_sharon_invitation():
    """Fix Sharon's invitation by adding the organization name"""
    
    email = "sharon@sackids.org"
    organization_name = "Sacramento Children's Museum"
    
    print(f"Looking up invitation for {email}...")
    
    # Get all invitations for this email
    invitations = invitation_manager.get_invitations_by_email(email)
    
    if not invitations:
        print(f"❌ No invitations found for {email}")
        print("\nCreating a new beta invitation...")
        
        # Create a new invitation with the correct organization name
        invite_code = invitation_manager.create_invitation(
            email=email,
            org_name=organization_name,
            invitation_type='beta',
            prefix='BETA'
        )
        
        print(f"✅ Created new beta invitation: {invite_code}")
        print(f"Registration URL: https://goldendoodlelm.ai/register?ref={invite_code}")
        return
    
    print(f"Found {len(invitations)} invitation(s)")
    
    # Find pending invitation
    pending = [inv for inv in invitations if inv['status'] == 'pending']
    
    if not pending:
        print("❌ No pending invitations found. Creating a new one...")
        invite_code = invitation_manager.create_invitation(
            email=email,
            org_name=organization_name,
            invitation_type='beta',
            prefix='BETA'
        )
        print(f"✅ Created new beta invitation: {invite_code}")
        print(f"Registration URL: https://goldendoodlelm.ai/register?ref={invite_code}")
        return
    
    # Update the organization name for pending invitation
    invitation = pending[0]
    invite_code = invitation['invite_code']
    current_org = invitation.get('organization_name', 'N/A')
    
    print(f"\nCurrent invitation details:")
    print(f"  Code: {invite_code}")
    print(f"  Current org name: {current_org}")
    print(f"  Status: {invitation['status']}")
    
    # Update the organization name in the database
    db = DatabaseManager()
    
    update_query = """
    UPDATE invitations 
    SET organization_name = %s
    WHERE invite_code = %s
    """
    
    db.execute_query(update_query, (organization_name, invite_code))
    
    print(f"\n✅ Updated invitation {invite_code}")
    print(f"   New organization name: {organization_name}")
    print(f"\nRegistration URL: https://goldendoodlelm.ai/register?ref={invite_code}")
    
    # Verify the update
    updated_inv = invitation_manager.get_invitation(invite_code)
    if updated_inv:
        print(f"\n✓ Verified: Organization is now '{updated_inv['organization_name']}'")

if __name__ == "__main__":
    fix_sharon_invitation()
