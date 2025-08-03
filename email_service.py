
import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent, HtmlContent
from typing import Optional
import secrets
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.api_key = os.environ.get('SENDGRID_API_KEY')
        self.from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@goldendoodlelm.com')
        self.from_name = os.environ.get('SENDGRID_FROM_NAME', 'GoldenDoodleLM')
        
        if not self.api_key:
            logger.warning("SendGrid API key not configured")
            self.client = None
        else:
            self.client = SendGridAPIClient(api_key=self.api_key)
    
    def send_verification_email(self, to_email: str, verification_token: str, first_name: str) -> bool:
        """Send email verification email"""
        if not self.client:
            logger.error("SendGrid client not configured")
            return False
        
        try:
            # Get the base URL for verification link
            base_url = os.environ.get('BASE_URL', 'https://goldendoodlelm.replit.app')
            verification_link = f"{base_url}/verify-email?token={verification_token}"
            
            # Email content
            subject = "Verify Your GoldenDoodleLM Account"
            
            plain_content = f"""
Hello {first_name},

Welcome to GoldenDoodleLM! Please verify your email address by clicking the link below:

{verification_link}

This link will expire in 24 hours.

If you didn't create an account with us, please ignore this email.

Best regards,
The GoldenDoodleLM Team
            """
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ background: #333; color: white; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to GoldenDoodleLM!</h1>
            <p>Your Compassionate Content Companion</p>
        </div>
        <div class="content">
            <h2>Hello {first_name},</h2>
            <p>Thank you for joining GoldenDoodleLM! We're excited to help you create trauma-informed, compassionate content.</p>
            <p>Please verify your email address by clicking the button below:</p>
            <a href="{verification_link}" class="button">Verify Email Address</a>
            <p>This verification link will expire in 24 hours.</p>
            <p>If you didn't create an account with us, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>The GoldenDoodleLM Team</p>
        </div>
    </div>
</body>
</html>
            """
            
            message = Mail(
                from_email=From(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=Subject(subject),
                plain_text_content=PlainTextContent(plain_content),
                html_content=HtmlContent(html_content)
            )
            
            response = self.client.send(message)
            logger.info(f"Verification email sent to {to_email}, status: {response.status_code}")
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {to_email}: {e}")
            return False
    
    def send_password_reset_email(self, to_email: str, reset_token: str, first_name: str) -> bool:
        """Send password reset email"""
        if not self.client:
            logger.error("SendGrid client not configured")
            return False
        
        try:
            base_url = os.environ.get('BASE_URL', 'https://goldendoodlelm.replit.app')
            reset_link = f"{base_url}/reset-password?token={reset_token}"
            
            subject = "Reset Your GoldenDoodleLM Password"
            
            plain_content = f"""
Hello {first_name},

You requested a password reset for your GoldenDoodleLM account.

Click the link below to reset your password:

{reset_link}

This link will expire in 1 hour.

If you didn't request this reset, please ignore this email.

Best regards,
The GoldenDoodleLM Team
            """
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ background: #333; color: white; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset</h1>
        </div>
        <div class="content">
            <h2>Hello {first_name},</h2>
            <p>You requested a password reset for your GoldenDoodleLM account.</p>
            <p>Click the button below to reset your password:</p>
            <a href="{reset_link}" class="button">Reset Password</a>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this reset, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>The GoldenDoodleLM Team</p>
        </div>
    </div>
</body>
</html>
            """
            
            message = Mail(
                from_email=From(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=Subject(subject),
                plain_text_content=PlainTextContent(plain_content),
                html_content=HtmlContent(html_content)
            )
            
            response = self.client.send(message)
            logger.info(f"Password reset email sent to {to_email}, status: {response.status_code}")
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {to_email}: {e}")
            return False

# Create global instance
email_service = EmailService()

def generate_verification_token() -> str:
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    """Hash a token for database storage"""
    return hashlib.sha256(token.encode()).hexdigest()
