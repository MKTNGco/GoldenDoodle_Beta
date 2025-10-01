
"""
Resend beta invitations to specific email addresses
"""
from invitation_manager import invitation_manager
from email_service import email_service
import sys

def resend_beta_invites(emails_to_resend):
    """
    Resend beta invitations to specific email addresses
    
    Args:
        emails_to_resend: List of email addresses to resend invites to
    """
    
    print(f"\n{'='*80}")
    print(f"RESENDING BETA INVITATIONS")
    print(f"{'='*80}\n")
    
    success_count = 0
    failed_count = 0
    
    for email in emails_to_resend:
        email = email.strip().lower()
        
        # Find existing invitation
        invitations = invitation_manager.get_invitations_by_email(email)
        beta_invites = [inv for inv in invitations if inv.get('invitation_type') == 'beta']
        
        if not beta_invites:
            print(f"❌ No beta invitation found for {email}")
            failed_count += 1
            continue
        
        # Get the most recent beta invite
        invite = beta_invites[0]
        invite_code = invite['invite_code']
        org_name = invite['organization_name']
        
        print(f"📧 Resending to {email}...")
        print(f"   Organization: {org_name}")
        print(f"   Code: {invite_code}")
        
        # Send email
        try:
            email_sent = email_service.send_beta_invitation_email(
                email, 
                invite_code, 
                org_name
            )
            
            if email_sent:
                print(f"✅ Successfully sent to {email}")
                success_count += 1
            else:
                print(f"❌ Failed to send to {email}")
                failed_count += 1
                
        except Exception as e:
            print(f"❌ Error sending to {email}: {e}")
            failed_count += 1
        
        print("-" * 80)
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Successfully sent: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    # Example usage - replace with actual emails
    emails = [
        # Add the emails you want to resend to
        # "user1@example.com",
        # "user2@example.com",
    ]
    
    if not emails:
        print("Please edit this file and add the email addresses you want to resend invitations to.")
        sys.exit(1)
    
    resend_beta_invites(emails)
