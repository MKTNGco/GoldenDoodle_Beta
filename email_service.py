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
        self.base_url = os.environ.get('BASE_URL', 'https://goldendoodlelm.replit.app')

        if not self.api_key:
            logger.warning("SendGrid API key not configured")
            self.client = None
        else:
            self.client = SendGridAPIClient(api_key=self.api_key)

    def send_verification_email(self, to_email: str, verification_token: str, first_name: str) -> bool:
        """Send email verification email"""
        logger.info(f"🔍 SEND VERIFICATION EMAIL DEBUG:")
        logger.info(f"  To email: {to_email}")
        logger.info(f"  First name: {first_name}")
        logger.info(f"  API key present: {bool(self.api_key)}")
        logger.info(f"  API key length: {len(self.api_key) if self.api_key else 0}")
        logger.info(f"  Client configured: {self.client is not None}")
        logger.info(f"  From email: {self.from_email}")
        logger.info(f"  Base URL: {self.base_url}")
        
        if not self.client:
            logger.error("🚨 SendGrid client not configured - API key missing or invalid")
            return False

        try:
            # Get the base URL for verification link
            base_url = os.environ.get('BASE_URL', 'https://goldendoodlelm.replit.app')
            # Ensure BASE_URL has protocol
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"https://{base_url}"
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
        .header {{ background: #32808c; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; }}
        .button {{ display: inline-block; background: #32808c; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
        .footer {{ background: #32808c; color: white; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
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
            <p>Thank you for joining GoldenDoodleLM! We're excited to help you create trauma-informed content that prioritizes safety, trust, and empowerment in all communications.</p>
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
            
            # Log response details for debugging
            if hasattr(response, 'body'):
                logger.info(f"SendGrid response body: {response.body}")
            if hasattr(response, 'headers'):
                logger.info(f"SendGrid response headers: {response.headers}")
                
            return response.status_code == 202

        except Exception as e:
            logger.error(f"🚨 Failed to send verification email to {to_email}: {e}")
            logger.error(f"🚨 Error type: {type(e).__name__}")
            
            # Log more details about the error
            if hasattr(e, 'status_code'):
                logger.error(f"🚨 SendGrid status code: {e.status_code}")
            if hasattr(e, 'body'):
                logger.error(f"🚨 SendGrid error body: {e.body}")
            if hasattr(e, 'headers'):
                logger.error(f"🚨 SendGrid error headers: {e.headers}")
                
            import traceback
            logger.error(f"🚨 Full traceback: {traceback.format_exc()}")
            return False

    def send_password_reset_email(self, to_email: str, reset_token: str, first_name: str) -> bool:
        """Send password reset email"""
        if not self.client:
            logger.error("SendGrid client not configured")
            return False

        try:
            base_url = os.environ.get('BASE_URL', 'https://goldendoodlelm.replit.app')
            # Ensure BASE_URL has protocol
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"https://{base_url}"
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
            logger.error(f"Error sending password reset email: {e}")
            return False

    def send_organization_invite_email(self, to_email: str, invite_token: str, organization_name: str, inviter_name: str) -> bool:
        """Send organization invite email"""
        try:
            invite_url = f"{self.base_url}/join-organization?token={invite_token}"

            subject = f"You're invited to join {organization_name} on GoldenDoodleLM"

            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #2c3e50; margin: 0;">GoldenDoodleLM</h1>
                    <p style="color: #7f8c8d; margin: 5px 0;">Trauma-Informed AI Content Generation</p>
                </div>

                <div style="background-color: #f8f9fa; padding: 30px; border-radius: 8px; margin-bottom: 30px;">
                    <h2 style="color: #2c3e50; margin-top: 0;">You're Invited!</h2>
                    <p style="color: #34495e; line-height: 1.6; margin-bottom: 20px;">
                        <strong>{inviter_name}</strong> has invited you to join <strong>{organization_name}</strong> on GoldenDoodleLM.
                    </p>
                    <p style="color: #34495e; line-height: 1.6; margin-bottom: 25px;">
                        GoldenDoodleLM helps organizations create content that prioritizes safety, trust, and empowerment in all communications.
                    </p>
                    <div style="text-align: center;">
                        <a href="{invite_url}" 
                           style="background-color: #3498db; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                            Accept Invitation
                        </a>
                    </div>
                </div>

                <div style="background-color: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ffc107; margin-bottom: 30px;">
                    <p style="color: #856404; margin: 0; font-size: 14px;">
                        <strong>Note:</strong> This invitation will expire in 7 days. If you already have a GoldenDoodleLM account, you'll be added to the organization. If not, you'll be guided through creating an account.
                    </p>
                </div>

                <div style="border-top: 1px solid #ecf0f1; padding-top: 20px; text-align: center;">
                    <p style="color: #7f8c8d; font-size: 12px; margin: 0;">
                        If you're having trouble with the button above, copy and paste this URL into your browser:<br>
                        <a href="{invite_url}" style="color: #3498db;">{invite_url}</a>
                    </p>
                </div>
            </div>
            """

            message = Mail(
                from_email=self.from_email,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )

            response = self.client.send(message)
            return response.status_code == 202

        except Exception as e:
            logger.error(f"Error sending organization invite email: {e}")
            return False

    def send_beta_invitation_email(self, to_email: str, invite_code: str, organization_name: str, invite_link: str = None) -> bool:
        """Send beta invitation email"""
        if not self.client:
            logger.error("SendGrid client not configured")
            return False

        try:
            # Use provided invite_link or generate one
            if not invite_link:
                base_url = os.environ.get('BASE_URL', 'https://goldendoodlelm.replit.app')
                # Ensure BASE_URL has protocol
                if not base_url.startswith(('http://', 'https://')):
                    base_url = f"https://{base_url}"
                invite_link = f"{base_url}/register?ref={invite_code}"

            subject = f"You're invited to try GoldenDoodleLM Beta for {organization_name}"

            plain_content = f"""
Hello from the GoldenDoodleLM team!

We're excited to invite {organization_name} to try GoldenDoodleLM Beta - your compassionate content companion for principled communications.

Join the Beta:
{invite_link}

About GoldenDoodleLM:
GoldenDoodleLM helps organizations create content that prioritizes safety, trust, and empowerment in all communications. Whether you're crafting emails, social media posts, or internal announcements, our AI ensures your message resonates with warmth and clarity.

What makes us different:
• Principled communications approach
• Brand voice consistency
• Safe and supportive content generation
• Built for organizations that care about their impact

Your invitation code: {invite_code}

Ready to get started? Click the link above or visit our registration page and enter your invitation code.

We can't wait to see what {organization_name} creates with GoldenDoodleLM!

Best regards,
The GoldenDoodleLM Team

---
Questions? Reply to this email or visit our support page.
            """

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #32808c 0%, #2a6b75 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; }}
        .highlight-box {{ background: #e8f4f5; border-left: 4px solid #32808c; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
        .button {{ display: inline-block; background: #32808c; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 20px 0; font-weight: bold; }}
        .button:hover {{ background: #2a6b75; }}
        .features {{ margin: 20px 0; }}
        .feature {{ margin: 10px 0; padding-left: 20px; position: relative; }}
        .feature:before {{ content: "✓"; position: absolute; left: 0; color: #32808c; font-weight: bold; }}
        .footer {{ background: #32808c; color: white; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
        .invite-code {{ background: #fff; border: 2px dashed #32808c; padding: 15px; text-align: center; font-family: monospace; font-size: 18px; font-weight: bold; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>You're Invited to GoldenDoodleLM Beta!</h1>
        <p>Compassionate Content for {organization_name}</p>
    </div>

    <div class="content">
        <p>Hello from the GoldenDoodleLM team!</p>

        <p>We're excited to invite <strong>{organization_name}</strong> to try GoldenDoodleLM Beta - your compassionate content companion for principled communications.</p>

        <div style="text-align: center;">
            <a href="{invite_link}" class="button">Join the Beta Now</a>
        </div>

        <div class="invite-code">
            Your invitation code: <span style="color: #32808c;">{invite_code}</span>
        </div>

        <div class="highlight-box">
            <h3 style="margin-top: 0; color: #32808c;">About GoldenDoodleLM</h3>
            <p>GoldenDoodleLM helps organizations create content that prioritizes safety, trust, and empowerment in all communications. Whether you're crafting emails, social media posts, or internal announcements, our AI ensures your message resonates with warmth and clarity.</p>
        </div>

        <h3 style="color: #32808c;">What makes us different:</h3>
        <div class="features">
            <div class="feature">Principled communications approach</div>
            <div class="feature">Brand voice consistency</div>
            <div class="feature">Safe and supportive content generation</div>
            <div class="feature">Built for organizations that care about their impact</div>
        </div>

        <p>Ready to get started? Click the button above or visit our registration page and enter your invitation code.</p>

        <p>We can't wait to see what <strong>{organization_name}</strong> creates with GoldenDoodleLM!</p>
    </div>

    <div class="footer">
        <p><strong>Best regards,</strong><br>The GoldenDoodleLM Team</p>
        <p style="font-size: 12px; margin-top: 15px;">Questions? Reply to this email or visit our support page.</p>
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
            logger.info(f"Beta invitation email sent to {to_email}, status: {response.status_code}")
            return response.status_code == 202

        except Exception as e:
            logger.error(f"Failed to send beta invitation email to {to_email}: {e}")
            return False

    def send_user_referral_email(self, to_email: str, invite_code: str, inviter_name: str, invitation_type: str, personal_message: str = "") -> bool:
        """Send user referral invitation email"""
        if not self.client:
            logger.error("SendGrid client not configured")
            return False

        try:
            base_url = os.environ.get('BASE_URL', 'https://goldendoodlelm.replit.app')
            # Ensure BASE_URL has protocol
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"https://{base_url}"
            invite_link = f"{base_url}/register?ref={invite_code}"

            # Format invitation type for display
            type_display = {
                'colleague': 'colleague',
                'friend': 'friend',
                'partner_organization': 'partner organization',
                'other': 'contact'
            }.get(invitation_type, 'contact')

            subject = f"{inviter_name} invited you to try GoldenDoodleLM"

            # Build personal message section
            personal_section = ""
            if personal_message:
                personal_section = f"""
                <div class="highlight-box">
                    <h3 style="margin-top: 0; color: #32808c;">Personal Message from {inviter_name}:</h3>
                    <p style="font-style: italic;">{personal_message.replace(chr(10), '<br>')}</p>
                </div>
                """

            plain_content = f"""
Hello!

{inviter_name} thinks you'd be interested in GoldenDoodleLM and has invited you to try our platform.

{f"Personal message: {personal_message}" if personal_message else ""}

Join GoldenDoodleLM:
{invite_link}

About GoldenDoodleLM:
GoldenDoodleLM helps organizations create content that prioritizes safety, trust, and empowerment in all communications. Whether you're crafting emails, social media posts, or internal announcements, our AI ensures your message resonates with warmth and clarity.

What makes us different:
• Principled communications approach
• Brand voice consistency
• Safe and supportive content generation
• Built for organizations that care about their impact

Your invitation code: {invite_code}

Ready to get started? Click the link above or visit our registration page and enter your invitation code.

Best regards,
The GoldenDoodleLM Team
            """

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #32808c 0%, #2a6b75 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; }}
        .highlight-box {{ background: #e8f4f5; border-left: 4px solid #32808c; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
        .button {{ display: inline-block; background: #32808c; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 20px 0; font-weight: bold; }}
        .button:hover {{ background: #2a6b75; }}
        .features {{ margin: 20px 0; }}
        .feature {{ margin: 10px 0; padding-left: 20px; position: relative; }}
        .feature:before {{ content: "✓"; position: absolute; left: 0; color: #32808c; font-weight: bold; }}
        .footer {{ background: #32808c; color: white; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
        .invite-code {{ background: #fff; border: 2px dashed #32808c; padding: 15px; text-align: center; font-family: monospace; font-size: 18px; font-weight: bold; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>You're Invited to GoldenDoodleLM!</h1>
        <p>A personal invitation from {inviter_name}</p>
    </div>

    <div class="content">
        <p>Hello!</p>

        <p><strong>{inviter_name}</strong> thinks you'd be interested in GoldenDoodleLM and has invited you to try our platform.</p>

        {personal_section}

        <div style="text-align: center;">
            <a href="{invite_link}" class="button">Accept Invitation</a>
        </div>

        <div class="invite-code">
            Your invitation code: <span style="color: #32808c;">{invite_code}</span>
        </div>

        <div class="highlight-box">
            <h3 style="margin-top: 0; color: #32808c;">About GoldenDoodleLM</h3>
            <p>GoldenDoodleLM helps organizations create content that prioritizes safety, trust, and empowerment in all communications. Whether you're crafting emails, social media posts, or internal announcements, our AI ensures your message resonates with warmth and clarity.</p>
        </div>

        <h3 style="color: #32808c;">What makes us different:</h3>
        <div class="features">
            <div class="feature">Principled communications approach</div>
            <div class="feature">Brand voice consistency</div>
            <div class="feature">Safe and supportive content generation</div>
            <div class="feature">Built for organizations that care about their impact</div>
        </div>

        <p>Ready to get started? Click the button above or visit our registration page and enter your invitation code.</p>
    </div>

    <div class="footer">
        <p><strong>Best regards,</strong><br>The GoldenDoodleLM Team</p>
        <p style="font-size: 12px; margin-top: 15px;">You received this invitation because {inviter_name} thought you'd be interested in GoldenDoodleLM.</p>
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
            logger.info(f"User referral email sent to {to_email}, status: {response.status_code}")
            return response.status_code == 202

        except Exception as e:
            logger.error(f"Failed to send user referral email to {to_email}: {e}")
            return False

    def send_beta_welcome_email(self, to_email: str, verification_token: str, first_name: str) -> bool:
        """Send a welcome email to beta users with verification link"""
        try:
            # Create verification URL
            verification_url = f"{self.base_url}/verify-email?token={verification_token}"

            # Email content
            subject = "🎉 Welcome to GoldenDoodleLM Beta - Verify Your Account"

            text_content = f"""
Hello {first_name},

🎉 Welcome to the GoldenDoodleLM Beta Program!

Your ORGANIZATION account has been created successfully with a 90-day free trial of "The Organization" plan - no payment required!

✅ WHAT YOU GET (FREE FOR 90 DAYS):
• Full access to all premium features
• Up to 10 brand voices for your organization
• Ability to invite unlimited team members (they get free access too!)
• All content creation tools and templates
• Priority support during beta

🚀 NEXT STEPS:
1. Click the verification link below
2. Sign in to your new organization account
3. Start creating trauma-informed content immediately
4. Invite your team members using the invite feature (they'll bypass payment too!)

VERIFY YOUR ACCOUNT: {verification_url}

This verification link will expire in 24 hours.

After verification, you can sign in and start using all features immediately - no payment or trial setup required!

Questions? Reply to this email and we'll help you get started.

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
        .header {{ background: #32808c; color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; }}
        .beta-benefits {{ background: #e8f5e8; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745; }}
        .button {{ display: inline-block; background: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }}
        .footer {{ background: #32808c; color: white; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
        .steps {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #ffc107; }}
        .highlight {{ background: #d4edda; padding: 10px; border-radius: 5px; margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Welcome to GoldenDoodleLM Beta!</h1>
            <p>Your Organization Account is Ready</p>
        </div>
        <div class="content">
            <h2>Hello {first_name},</h2>
            <p><strong>Congratulations!</strong> Your <em>Organization account</em> has been created successfully.</p>

            <div class="highlight">
                <p><strong>🎁 You're getting "The Organization" plan FREE for 90 days!</strong><br>
                <em>No payment required - just verify your email and start creating.</em></p>
            </div>

            <div class="beta-benefits">
                <h3>✅ What You Get (FREE for 90 Days):</h3>
                <ul>
                    <li><strong>Full premium features</strong> - All content tools and templates</li>
                    <li><strong>Up to 10 brand voices</strong> - Create distinct voices for different purposes</li>
                    <li><strong>Team collaboration</strong> - Invite unlimited team members (they get free access too!)</li>
                    <li><strong>Priority support</strong> - Direct access to our team during beta</li>
                    <li><strong>No payment walls</strong> - Everything unlocked immediately</li>
                </ul>
            </div>

            <div class="steps">
                <h3>🚀 Get Started in 2 Minutes:</h3>
                <ol>
                    <li><strong>Click the button below</strong> to verify your email</li>
                    <li><strong>Sign in</strong> to your organization account</li>
                    <li><strong>Start creating</strong> trauma-informed content immediately</li>
                    <li><strong>Invite your team</strong> (they'll bypass payment too!)</li>
                </ol>
            </div>

            <p style="text-align: center;">
                <a href="{verification_url}" class="button">🚀 Verify Email & Start Creating</a>
            </p>

            <p style="text-align: center; font-size: 14px; color: #666;">
                <em>This verification link expires in 24 hours</em>
            </p>
        </div>
        <div class="footer">
            <p><strong>Ready to transform your content creation?</strong><br>
            Questions? Reply to this email for immediate help.<br><br>Best regards,<br>The GoldenDoodleLM Team</p>
        </div>
    </div>
</body>
</html>
            """

            message = Mail(
                from_email=From(self.from_email, self.from_name),
                to_emails=To(to_email),
                subject=Subject(subject),
                plain_text_content=PlainTextContent(text_content),
                html_content=HtmlContent(html_content)
            )

            response = self.client.send(message)
            logger.info(f"Beta welcome email sent to {to_email}, status: {response.status_code}")
            return response.status_code == 202

        except Exception as e:
            logger.error(f"Failed to send beta welcome email to {to_email}: {e}")
            return False

    def send_referral_welcome_email(self, to_email: str, verification_token: str, first_name: str) -> bool:
        """Send referral welcome email with verification link"""
        if not self.client:
            logger.error("SendGrid client not configured")
            return False

        try:
            base_url = os.environ.get('BASE_URL', 'https://goldendoodlelm.replit.app')
            # Ensure BASE_URL has protocol
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"https://{base_url}"
            verify_link = f"{base_url}/verify-email?token={verification_token}"

            subject = f"Welcome to GoldenDoodleLM, {first_name}!"

            plain_content = f"""
Hello {first_name},

Welcome to GoldenDoodleLM! Thanks for joining through a friend's referral.

Your account has been created successfully. Please verify your email address to complete your registration:
{verify_link}

Once you verify your email, you can sign in and start creating compassionate content with GoldenDoodleLM.

Best regards,
The GoldenDoodleLM Team

---
Questions? Reply to this email or contact our support team.
            """

            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; }}
        .header {{ background: linear-gradient(135deg, #32808c 0%, #2a6b75 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; }}
        .button {{ display: inline-block; background: #32808c; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; margin: 20px 0; font-weight: bold; }}
        .button:hover {{ background: #2a6b75; }}
        .footer {{ background: #32808c; color: white; padding: 20px; text-align: center; border-radius: 0 0 8px 8px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Welcome to GoldenDoodleLM!</h1>
        <p>Thanks for joining, {first_name}!</p>
    </div>

    <div class="content">
        <p>Hello {first_name},</p>

        <p>Welcome to GoldenDoodleLM! Thanks for joining through a friend's referral.</p>

        <p>Your account has been created successfully. Please verify your email address to complete your registration:</p>

        <div style="text-align: center;">
            <a href="{verify_link}" class="button">Verify Email & Get Started</a>
        </div>

        <p>Once you verify your email, you can sign in and start creating compassionate content with GoldenDoodleLM.</p>
    </div>

    <div class="footer">
        <p><strong>Best regards,</strong><br>The GoldenDoodleLM Team</p>
        <p style="font-size: 12px; margin-top: 15px;">Questions? Reply to this email or contact our support team.</p>
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
            logger.info(f"Referral welcome email sent to {to_email}, status: {response.status_code}")
            return response.status_code == 202

        except Exception as e:
            logger.error(f"Failed to send referral welcome email to {to_email}: {e}")
            return False

    def send_feedback_email(self, feedback_data: dict, attachments: list = None) -> bool:
        """Send feedback email to support"""
        try:
            support_email = os.environ.get('SUPPORT_EMAIL', 'support@goldendoodlelm.ai')

            # Format feedback type for display
            feedback_types = {
                'bug': 'Bug Report',
                'feature': 'Feature Request', 
                'general': 'General Feedback',
                'support': 'Support Request',
                'other': 'Other'
            }

            feedback_type_display = feedback_types.get(feedback_data.get('feedback_type', 'other'), 'Other')
            # Create email subject from feedback type
            subject = f"[{feedback_type_display}] New {feedback_type_display} Submission"

            # Build email content
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #32808c; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                    <h2>New Feedback Submission</h2>
                </div>

                <div style="background-color: #f9f9f9; padding: 20px; border-radius: 0 0 8px 8px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold; width: 120px;">Type:</td>
                            <td style="padding: 8px 0;">{feedback_type_display}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">Subject:</td>
                            <td style="padding: 8px 0;">{feedback_data.get('subject', 'N/A')}</td>
                        </tr>
            """

            # Add user information
            if feedback_data.get('user_info'):
                user_info = feedback_data['user_info']
                html_content += f"""
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">User:</td>
                            <td style="padding: 8px 0;">{user_info.get('name', 'N/A')} ({user_info.get('email', 'N/A')})</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">User ID:</td>
                            <td style="padding: 8px 0;">{user_info.get('user_id', 'N/A')}</td>
                        </tr>
                """
            elif feedback_data.get('email') or feedback_data.get('name'):
                html_content += f"""
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">Contact:</td>
                            <td style="padding: 8px 0;">{feedback_data.get('name', 'Anonymous')} ({feedback_data.get('email', 'No email provided')})</td>
                        </tr>
                """
            else:
                html_content += """
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">Contact:</td>
                            <td style="padding: 8px 0;">Anonymous submission</td>
                        </tr>
                """

            html_content += f"""
                        <tr>
                            <td style="padding: 8px 0; font-weight: bold;">Timestamp:</td>
                            <td style="padding: 8px 0;">{feedback_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))}</td>
                        </tr>
                    </table>

                    <div style="margin-top: 20px;">
                        <h3 style="color: #32808c; margin-bottom: 10px;">Message:</h3>
                        <div style="background-color: white; padding: 15px; border-radius: 5px; border-left: 4px solid #32808c;">
                            {feedback_data.get('message', 'No message provided').replace(chr(10), '<br>')}
                        </div>
                    </div>
            """

            # Add system information if provided
            if feedback_data.get('system_info'):
                html_content += f"""
                    <div style="margin-top: 20px;">
                        <h3 style="color: #32808c; margin-bottom: 10px;">System Information:</h3>
                        <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; font-family: monospace; font-size: 12px;">
                            <pre style="margin: 0; white-space: pre-wrap;">{feedback_data['system_info']}</pre>
                        </div>
                    </div>
                """

            # Add attachment info
            if attachments:
                html_content += f"""
                    <div style="margin-top: 20px;">
                        <h3 style="color: #32808c; margin-bottom: 10px;">Attachments:</h3>
                        <ul>
                """
                for attachment in attachments:
                    html_content += f"""
                            <li>{attachment['filename']} ({attachment['size']} bytes)</li>
                    """
                html_content += """
                        </ul>
                    </div>
                """

            html_content += """
                </div>
            </div>
            """

            # Create plain text version
            plain_content = f"""
New Feedback Submission

Type: {feedback_type_display}
Subject: {feedback_data.get('subject', 'N/A')}
"""

            if feedback_data.get('user_info'):
                user_info = feedback_data['user_info']
                plain_content += f"User: {user_info.get('name', 'N/A')} ({user_info.get('email', 'N/A')})\n"
                plain_content += f"User ID: {user_info.get('user_id', 'N/A')}\n"
            elif feedback_data.get('email') or feedback_data.get('name'):
                plain_content += f"Contact: {feedback_data.get('name', 'Anonymous')} ({feedback_data.get('email', 'No email provided')})\n"
            else:
                plain_content += "Contact: Anonymous submission\n"

            plain_content += f"Timestamp: {feedback_data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'))}\n\n"
            plain_content += f"Message:\n{feedback_data.get('message', 'No message provided')}\n"

            if feedback_data.get('system_info'):
                plain_content += f"\nSystem Information:\n{feedback_data['system_info']}\n"

            if attachments:
                plain_content += "\nAttachments:\n"
                for attachment in attachments:
                    plain_content += f"- {attachment['filename']} ({attachment['size']} bytes)\n"

            message = Mail(
                from_email=From(self.from_email, self.from_name),
                to_emails=To(support_email),
                subject=Subject(subject),
                plain_text_content=PlainTextContent(plain_content),
                html_content=HtmlContent(html_content)
            )

            # Add attachments if provided
            if attachments:
                from sendgrid.helpers.mail import Attachment, FileContent, FileName, FileType, Disposition
                import base64

                for attachment_data in attachments:
                    try:
                        # Encode file content
                        encoded_content = base64.b64encode(attachment_data['content']).decode()

                        attachment = Attachment(
                            FileContent(encoded_content),
                            FileName(attachment_data['filename']),
                            FileType(attachment_data.get('content_type', 'application/octet-stream')),
                            Disposition('attachment')
                        )
                        message.add_attachment(attachment)
                    except Exception as e:
                        logger.error(f"Error adding attachment {attachment_data['filename']}: {e}")

            response = self.client.send(message)
            logger.info(f"Feedback email sent to {support_email}, status: {response.status_code}")
            return response.status_code == 202

        except Exception as e:
            logger.error(f"Error sending feedback email: {e}")
            return False

def detect_email_system():
    """Detect which email system is configured"""
    sendgrid_key = os.environ.get('SENDGRID_API_KEY')

    systems = {
        'sendgrid': {
            'configured': bool(sendgrid_key),
            'from_email': os.environ.get('SENDGRID_FROM_EMAIL'),
            'from_name': os.environ.get('SENDGRID_FROM_NAME'),
            'base_url': os.environ.get('BASE_URL')
        }
    }

    # Determine which system is active
    active_system = None
    if systems['sendgrid']['configured']:
        active_system = 'sendgrid'

    return {
        'active_system': active_system,
        'systems': systems,
        'ready': active_system is not None
    }

# Global email service instance
email_service = EmailService()

def generate_verification_token() -> str:
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    """Hash a token for database storage"""
    return hashlib.sha256(token.encode()).hexdigest()