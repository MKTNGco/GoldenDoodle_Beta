
#!/usr/bin/env python3
"""
Test script for the InvitationManager class.
Run this to see how the invitation system works.
"""

from invitation_manager import invitation_manager

def test_invitation_system():
    print("🧪 Testing Invitation Manager System")
    print("=" * 50)
    
    # Test 1: Create some invitations
    print("\n1. Creating invitations...")
    
    # Create beta invitation with BETA prefix
    beta_code = invitation_manager.create_invitation(
        email="user1@example.com",
        org_name="Tech Startup Inc",
        invitation_type="beta",
        prefix="BETA"
    )
    print(f"✓ Beta invitation created: {beta_code}")
    
    # Create team member invitation without prefix
    team_code = invitation_manager.create_invitation(
        email="user2@example.com",
        org_name="Marketing Agency LLC",
        invitation_type="team_member"
    )
    print(f"✓ Team invitation created: {team_code}")
    
    # Create referral invitation with REF prefix
    ref_code = invitation_manager.create_invitation(
        email="user3@example.com",
        org_name="Consulting Group",
        invitation_type="referral",
        prefix="REF"
    )
    print(f"✓ Referral invitation created: {ref_code}")
    
    # Test 2: Look up invitations
    print("\n2. Looking up invitations...")
    
    beta_invite = invitation_manager.get_invitation(beta_code)
    if beta_invite:
        print(f"✓ Found beta invitation for {beta_invite['invitee_email']}")
        print(f"  Organization: {beta_invite['organization_name']}")
        print(f"  Type: {beta_invite['invitation_type']}")
        print(f"  Status: {beta_invite['status']}")
    
    # Test 3: Mark invitation as accepted
    print("\n3. Accepting an invitation...")
    
    if invitation_manager.mark_accepted(team_code):
        print(f"✓ Successfully marked {team_code} as accepted")
        
        # Verify the status change
        updated_invite = invitation_manager.get_invitation(team_code)
        print(f"  Updated status: {updated_invite['status']}")
    
    # Test 4: Get invitations by status
    print("\n4. Getting invitations by status...")
    
    pending_invites = invitation_manager.get_invitations_by_status("pending")
    accepted_invites = invitation_manager.get_invitations_by_status("accepted")
    
    print(f"✓ Pending invitations: {len(pending_invites)}")
    print(f"✓ Accepted invitations: {len(accepted_invites)}")
    
    # Test 5: Get all invitations
    print("\n5. All invitations summary...")
    
    all_invites = invitation_manager.get_all_invitations()
    print(f"✓ Total invitations: {len(all_invites)}")
    
    for invite in all_invites:
        print(f"  {invite['invite_code']} - {invite['invitee_email']} ({invite['status']})")
    
    print("\n🎉 Test completed! Check invitations.json to see the stored data.")

if __name__ == "__main__":
    test_invitation_system()
