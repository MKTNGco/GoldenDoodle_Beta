import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('MAIL_PORT', '587'))
        self.smtp_username = os.environ.get('MAIL_USERNAME')
        self.smtp_password = os.environ.get('MAIL_PASSWORD')
        self.from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'hassanshakoor308@gmail.com')
        self.from_name = os.environ.get('SENDGRID_FROM_NAME', 'GoldenDoodleLM')
        self.base_url = os.environ.get('BASE_URL', 'https://goldendoodlelm.replit.app')

        if not self.smtp_username or not self.smtp_password:
            logger.warning("SMTP credentials not configured")
            self.smtp_enabled = False
        else:
            self.smtp_enabled = True

    def _send_email(self, to_email: str, subject: str, html_content: str, plain_content: str = None) -> bool:
        """Send email via SMTP"""
        if not self.smtp_enabled:
            logger.error("SMTP not configured")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email

            # Add plain text version if provided
            if plain_content:
                part1 = MIMEText(plain_content, 'plain')
                msg.attach(part1)

            # Add HTML version
            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)

            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            text = msg.as_string()
            server.sendmail(self.from_email, to_email, text)
            server.quit()

            logger.info(f"Email sent to {to_email} via SMTP")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def send_verification_email(self, to_email: str, verification_token: str, first_name: str) -> bool:
        """Send email verification email"""
        try:
            verification_link = f"{self.base_url}/verify-email?token={verification_token}"

            subject = "Verify Your GoldenDoodleLM Account"

            plain_content = f"""
Hello {first_name},

Welcome to GoldenDoodleLM! Please verify your email address by clicking the link below:

{verification_link}

This verification link will expire in 24 hours.

If you didn't create an account with us, please ignore this email.

Best regards,
The GoldenDoodleLM Team
"""

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Account</title>
</head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2c5aa0;">Welcome to GoldenDoodleLM!</h1>
        <p style="color: #666; font-size: 18px;">Your Compassionate Content Companion</p>
    </div>
    
    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
        <h2 style="color: #2c5aa0; margin-top: 0;">Hello {first_name},</h2>
        <p>Thank you for joining GoldenDoodleLM! We're excited to help you create trauma-informed content that prioritizes safety, trust, and empowerment in all communications.</p>
        <p>Please verify your email address by clicking the button below:</p>
    </div>
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="{verification_link}" 
           style="background: #2c5aa0; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
            Verify Email Address
        </a>
    </div>
    
    <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px;">
        <p style="margin: 0; color: #856404; font-size: 14px;">
            <strong>Important:</strong> This verification link will expire in 24 hours.
        </p>
    </div>
    
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px;">
        <p>If you didn't create an account with us, please ignore this email.</p>
        <p>Best regards,<br>The GoldenDoodleLM Team</p>
    </div>
</body>
</html>
"""

            return self._send_email(to_email, subject, html_content, plain_content)

        except Exception as e:
            logger.error(f"Failed to send verification email to {to_email}: {e}")
            return False

# Create global instance
email_service = EmailService()
