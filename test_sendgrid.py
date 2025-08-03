
import os
from email_service import email_service, generate_verification_token

def test_sendgrid_configuration():
    """Test SendGrid configuration and connectivity"""
    print("=== SendGrid Configuration Test ===")
    
    # Check environment variables
    api_key = os.environ.get('SENDGRID_API_KEY')
    from_email = os.environ.get('SENDGRID_FROM_EMAIL')
    from_name = os.environ.get('SENDGRID_FROM_NAME')
    base_url = os.environ.get('BASE_URL')
    
    print(f"API Key configured: {'✓' if api_key else '✗'}")
    print(f"From Email: {from_email or 'Not configured'}")
    print(f"From Name: {from_name or 'Not configured'}")
    print(f"Base URL: {base_url or 'Not configured'}")
    print()
    
    if not api_key:
        print("❌ SendGrid API key not configured. Please add SENDGRID_API_KEY to Secrets.")
        return False
    
    if not from_email:
        print("❌ From email not configured. Please add SENDGRID_FROM_EMAIL to Secrets.")
        return False
    
    return True

def test_verification_email():
    """Test sending a verification email"""
    print("=== Testing Verification Email ===")
    
    if not test_sendgrid_configuration():
        return
    
    # Test email (replace with your email for testing)
    test_email = input("Enter your email address for testing: ").strip()
    if not test_email:
        print("❌ No email provided")
        return
    
    # Generate test token
    verification_token = generate_verification_token()
    
    print(f"Sending verification email to: {test_email}")
    print(f"Test token: {verification_token}")
    
    success = email_service.send_verification_email(
        to_email=test_email,
        verification_token=verification_token,
        first_name="Test User"
    )
    
    if success:
        print("✅ Verification email sent successfully!")
        print(f"Check your inbox at {test_email}")
    else:
        print("❌ Failed to send verification email")
        print("Check the console logs for error details")

def test_password_reset_email():
    """Test sending a password reset email"""
    print("\n=== Testing Password Reset Email ===")
    
    if not test_sendgrid_configuration():
        return
    
    # Test email (replace with your email for testing)
    test_email = input("Enter your email address for testing: ").strip()
    if not test_email:
        print("❌ No email provided")
        return
    
    # Generate test token
    reset_token = generate_verification_token()
    
    print(f"Sending password reset email to: {test_email}")
    print(f"Test token: {reset_token}")
    
    success = email_service.send_password_reset_email(
        to_email=test_email,
        reset_token=reset_token,
        first_name="Test User"
    )
    
    if success:
        print("✅ Password reset email sent successfully!")
        print(f"Check your inbox at {test_email}")
    else:
        print("❌ Failed to send password reset email")
        print("Check the console logs for error details")

if __name__ == "__main__":
    print("GoldenDoodleLM SendGrid Email Test")
    print("=" * 40)
    
    # Test configuration first
    if test_sendgrid_configuration():
        print("✅ Configuration looks good!")
        print()
        
        while True:
            print("Choose a test:")
            print("1. Test verification email")
            print("2. Test password reset email")
            print("3. Test both emails")
            print("4. Exit")
            
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == "1":
                test_verification_email()
            elif choice == "2":
                test_password_reset_email()
            elif choice == "3":
                test_verification_email()
                test_password_reset_email()
            elif choice == "4":
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please try again.")
            
            print("\n" + "=" * 40)
    else:
        print("❌ Configuration issues found. Please fix them and try again.")
