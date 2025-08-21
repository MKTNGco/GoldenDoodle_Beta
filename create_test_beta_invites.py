
#!/usr/bin/env python3
"""
Script to create test beta invitations for development
"""

from invitation_manager import invitation_manager

def create_test_beta_invites():
    """Create multiple test beta invitations"""
    
    test_emails = [
        "scott+test1@goldendoodlelm.ai",
        "scott+test2@goldendoodlelm.ai", 
        "scott+beta1@goldendoodlelm.ai",
        "scott+beta2@goldendoodlelm.ai",
        "test1@goldendoodlelm.ai",
        "test2@goldendoodlelm.ai",
        "demo@goldendoodlelm.ai",
        "staging@goldendoodlelm.ai"
    ]
    
    created_codes = []
    
    for email in test_emails:
        try:
            # Create beta invitation
            invite_code = invitation_manager.create_invitation(
                email=email,
                org_name=f"Test Organization for {email.split('@')[0]}",
                invitation_type='beta',
                prefix='BETA'
            )
            
            created_codes.append({
                'email': email,
                'invite_code': invite_code,
                'registration_url': f"https://your-repl-url.replit.dev/register?ref={invite_code}"
            })
            
            print(f"✓ Created beta invitation for {email}: {invite_code}")
            
        except Exception as e:
            print(f"❌ Failed to create invitation for {email}: {e}")
    
    print(f"\n📧 Created {len(created_codes)} beta invitations:")
    for item in created_codes:
        print(f"Email: {item['email']}")
        print(f"Code: {item['invite_code']}")
        print(f"URL: {item['registration_url']}")
        print("---")

if __name__ == "__main__":
    create_test_beta_invites()
