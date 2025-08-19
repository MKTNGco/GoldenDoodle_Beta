#!/usr/bin/env python3
"""
Test script for the InvitationManager class.
Run this to see how the invitation system works.
"""

from invitation_manager import invitation_manager

def test_invitation_system():
    print("=== Testing Invitation Manager ===\n")

    # Test 1: Create test invitation
    print("1. Creating invitation...")
    code = invitation_manager.create_invitation("test@example.com", "Test Org", "beta")
    print(f"Generated code: {code}\n")

    # Test 2: Look up invitation
    print("2. Looking up invitation...")
    invitation = invitation_manager.get_invitation(code)
    print(f"Found invitation: {invitation}\n")

    # Test 3: Mark as accepted
    print("3. Marking as accepted...")
    success = invitation_manager.mark_accepted(code)
    print(f"Marked as accepted: {success}\n")

    # Test 4: Look up again to see updated status
    print("4. Looking up invitation after acceptance...")
    updated_invitation = invitation_manager.get_invitation(code)
    print(f"Updated invitation: {updated_invitation}\n")

    # Test 5: Create invitation with prefix
    print("5. Creating invitation with prefix...")
    beta_code = invitation_manager.create_invitation("beta@example.com", "Beta Org", "beta", prefix="BETA")
    print(f"Generated beta code: {beta_code}\n")

    # Test 6: Get all invitations
    print("6. Getting all invitations...")
    all_invitations = invitation_manager.get_all_invitations()
    print(f"Total invitations: {len(all_invitations)}")
    for inv in all_invitations:
        print(f"  - {inv['invite_code']}: {inv['invitee_email']} ({inv['status']})")

if __name__ == "__main__":
    test_invitation_system()