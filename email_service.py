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
                        GoldenDoodleLM helps organizations create trauma-informed content that prioritizes safety, trust, and empowerment in all communications.
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

# Global email service instance
email_service = EmailService()

def generate_verification_token() -> str:
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    """Hash a token for database storage"""
    return hashlib.sha256(token.encode()).hexdigest()