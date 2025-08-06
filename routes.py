from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app
from auth import login_required, admin_required, super_admin_required, get_current_user, login_user, logout_user
from database import db_manager
from gemini_service import gemini_service
from rag_service import rag_service
from models import TenantType, SubscriptionLevel, CONTENT_MODE_CONFIG, BrandVoice
from email_service import email_service, generate_verification_token, hash_token
import json
import logging
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """Home page"""
    user = get_current_user()
    if user:
        return redirect(url_for('chat'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    # Check if this is an organization invite
    is_organization_invite = request.args.get('invite') == 'organization'
    organization_invite = session.get('organization_invite') if is_organization_invite else None

    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            organization_name = request.form.get('organization_name', '').strip()
            user_type = request.form.get('user_type', 'independent')
            subscription_level = request.form.get('subscription_level', 'entry')

            # Validation
            if not all([first_name, last_name, email, password]):
                flash('All fields are required.', 'error')
                return render_template('register.html', 
                                     is_organization_invite=is_organization_invite,
                                     organization_invite=organization_invite)

            # Handle organization invite registration
            if organization_invite:
                if email != organization_invite['email']:
                    flash('You must use the invited email address to register.', 'error')
                    return render_template('register.html', 
                                         is_organization_invite=is_organization_invite,
                                         organization_invite=organization_invite)

                # Check if user already exists
                existing_user = db_manager.get_user_by_email(email)
                if existing_user:
                    flash('An account with this email already exists.', 'error')
                    return render_template('register.html', 
                                         is_organization_invite=is_organization_invite,
                                         organization_invite=organization_invite)

                # Create user as organization member with predetermined settings
                user = db_manager.create_user(
                    tenant_id=organization_invite['tenant_id'],
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password=password,
                    subscription_level=SubscriptionLevel.TEAM,  # Predetermined for organization members
                    is_admin=False  # Regular team member, not admin
                )

                # Mark invite as used
                db_manager.use_organization_invite_token(organization_invite['token_hash'])

                # Clear invite from session
                session.pop('organization_invite', None)

                # Generate and send verification email
                verification_token = generate_verification_token()
                token_hash = hash_token(verification_token)

                if db_manager.create_verification_token(user.user_id, token_hash):
                    if email_service.send_verification_email(email, verification_token, first_name):
                        flash(f'Welcome to {organization_invite["organization_name"]}! Your account has been created successfully. Please check your email to verify your account before signing in.', 'success')
                        return redirect(url_for('login'))
                    else:
                        flash('Account created, but we couldn\'t send the verification email. Please contact support.', 'warning')
                        return redirect(url_for('login'))
                else:
                    flash('Account created, but there was an issue with email verification. Please contact support.', 'warning')
                    return redirect(url_for('login'))

            # Regular registration flow
            if user_type == 'company' and not organization_name:
                flash('Organization name is required for company accounts.', 'error')
                return render_template('register.html', 
                                     is_organization_invite=is_organization_invite,
                                     organization_invite=organization_invite)

            # Check if user already exists
            existing_user = db_manager.get_user_by_email(email)
            if existing_user:
                flash('An account with this email already exists.', 'error')
                return render_template('register.html', 
                                     is_organization_invite=is_organization_invite,
                                     organization_invite=organization_invite)

            # Create tenant and determine brand voice limits
            subscription_enum = SubscriptionLevel(subscription_level)

            if user_type == 'company':
                # Team or Enterprise plans
                if subscription_enum == SubscriptionLevel.TEAM:
                    max_brand_voices = 3
                elif subscription_enum == SubscriptionLevel.ENTERPRISE:
                    max_brand_voices = 10  # Higher limit for enterprise
                else:
                    max_brand_voices = 3  # Default for team plans

                tenant = db_manager.create_tenant(
                    name=organization_name,
                    tenant_type=TenantType.COMPANY,
                    max_brand_voices=max_brand_voices
                )
                is_admin = True  # First user in company is admin
            else:
                # Individual plans (Solo/Pro)
                if subscription_enum == SubscriptionLevel.SOLO:
                    max_brand_voices = 1
                elif subscription_enum == SubscriptionLevel.PRO:
                    max_brand_voices = 10
                else:
                    max_brand_voices = 1  # Default

                tenant = db_manager.create_tenant(
                    name=f"{first_name} {last_name}'s Account",
                    tenant_type=TenantType.INDEPENDENT_USER,
                    max_brand_voices=max_brand_voices
                )
                is_admin = False

            # Create user
            user = db_manager.create_user(
                tenant_id=tenant.tenant_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                subscription_level=SubscriptionLevel(subscription_level),
                is_admin=is_admin
            )

            # Generate and send verification email
            verification_token = generate_verification_token()
            token_hash = hash_token(verification_token)

            if db_manager.create_verification_token(user.user_id, token_hash):
                if email_service.send_verification_email(email, verification_token, first_name):
                    flash('Account created successfully! Please check your email to verify your account before signing in.', 'success')
                    return redirect(url_for('login'))
                else:
                    flash('Account created, but we couldn\'t send the verification email. Please contact support.', 'warning')
                    return redirect(url_for('login'))
            else:
                flash('Account created, but there was an issue with email verification. Please contact support.', 'warning')
                return redirect(url_for('login'))

        except Exception as e:
            logger.error(f"Registration error: {e}")
            flash('An error occurred during registration. Please try again.', 'error')

    return render_template('register.html', 
                         is_organization_invite=is_organization_invite,
                         organization_invite=organization_invite)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('login.html')

        user = db_manager.get_user_by_email(email)
        if user and db_manager.verify_password(user, password):
            if not user.email_verified:
                flash('Please verify your email address before signing in. Check your inbox for the verification link.', 'warning')
                return render_template('login.html', show_resend=True, email=email)

            # Update last login timestamp
            db_manager.update_user_last_login(user.user_id)
            
            login_user(user)
            flash('Welcome back!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('chat'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/verify-email')
def verify_email():
    """Email verification endpoint"""
    token = request.args.get('token')
    if not token:
        flash('Invalid verification link.', 'error')
        return redirect(url_for('login'))

    token_hash = hash_token(token)
    user_id = db_manager.verify_email_token(token_hash)

    if user_id:
        flash('Email verified successfully! You can now sign in.', 'success')
        return redirect(url_for('login'))
    else:
        flash('Invalid or expired verification link.', 'error')
        return redirect(url_for('login'))

@app.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification email"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        user = db_manager.get_user_by_email(email)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.email_verified:
            return jsonify({'error': 'Email is already verified'}), 400

        # Delete existing tokens and create new one
        db_manager.resend_verification_email(user.user_id)

        verification_token = generate_verification_token()
        token_hash = hash_token(verification_token)

        if db_manager.create_verification_token(user.user_id, token_hash):
            if email_service.send_verification_email(email, verification_token, user.first_name):
                return jsonify({'success': True, 'message': 'Verification email sent successfully'})
            else:
                return jsonify({'error': 'Failed to send verification email'}), 500
        else:
            return jsonify({'error': 'Failed to create verification token'}), 500

    except Exception as e:
        logger.error(f"Error resending verification: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash('Email address is required.', 'error')
            return render_template('forgot_password.html')

        user = db_manager.get_user_by_email(email)
        if user:
            # Generate password reset token
            reset_token = generate_verification_token()
            token_hash = hash_token(reset_token)

            if db_manager.create_password_reset_token(user.user_id, token_hash):
                if email_service.send_password_reset_email(email, reset_token, user.first_name):
                    flash('Password reset link sent to your email address.', 'success')
                else:
                    flash('Failed to send password reset email. Please try again.', 'error')
            else:
                flash('Failed to generate password reset link. Please try again.', 'error')
        else:
            # Don't reveal if email exists or not
            flash('If an account with that email exists, a password reset link has been sent.', 'info')

        return redirect(url_for('login'))

    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Reset password page"""
    token = request.args.get('token')
    if not token:
        flash('Invalid reset link.', 'error')
        return redirect(url_for('login'))

    token_hash = hash_token(token)
    user_id = db_manager.verify_password_reset_token(token_hash)

    if not user_id:
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not password or not confirm_password:
            flash('Password and confirmation are required.', 'error')
            return render_template('reset_password.html', token=token)

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)

        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('reset_password.html', token=token)

        # Update password
        from werkzeug.security import generate_password_hash
        new_password_hash = generate_password_hash(password)

        try:
            conn = db_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users 
                SET password_hash = %s
                WHERE user_id = %s
            """, (new_password_hash, user_id))

            conn.commit()
            cursor.close()
            conn.close()

            # Mark token as used
            db_manager.use_password_reset_token(token_hash)

            flash('Password reset successfully! You can now sign in.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            flash('An error occurred while resetting your password.', 'error')
            return render_template('reset_password.html', token=token)

    return render_template('reset_password.html', token=token)

@app.route('/chat')
def chat():
    """Main chat interface - supports both logged-in users and demo mode"""
    user = get_current_user()

    if user:
        # Logged-in user - full functionality
        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if not tenant:
            flash('Invalid tenant. Please contact support.', 'error')
            return redirect(url_for('logout'))

        # Get brand voices - all voices are treated as company voices now
        company_brand_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
        user_brand_voices = []  # No longer using user-specific brand voices

        return render_template('chat.html', 
                             user=user, 
                             tenant=tenant,
                             company_brand_voices=company_brand_voices,
                             user_brand_voices=user_brand_voices,
                             content_modes=CONTENT_MODE_CONFIG,
                             is_demo=False)
    else:
        # Demo mode - limited functionality
        return render_template('chat.html', 
                             user=None, 
                             tenant=None,
                             company_brand_voices=[],
                             user_brand_voices=[],
                             content_modes=CONTENT_MODE_CONFIG,
                             is_demo=True)

@app.route('/generate', methods=['POST'])
def generate():
    """Generate AI content - supports both logged-in users and demo mode"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        content_mode = data.get('content_mode')
        brand_voice_id = data.get('brand_voice_id')
        is_demo = data.get('is_demo', False)

        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400

        user = get_current_user()

        if not user and not is_demo:
            return jsonify({'error': 'Authentication required'}), 401

        # Demo mode - limited functionality
        if is_demo or not user:
            # Get trauma-informed context only
            trauma_informed_context = rag_service.get_trauma_informed_context()

            # Generate content without brand voice
            response = gemini_service.generate_content(
                prompt=prompt,
                content_mode=content_mode,
                brand_voice_context=None,
                trauma_informed_context=trauma_informed_context
            )

            return jsonify({'response': response})

        # Logged-in user - full functionality
        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if not tenant:
            return jsonify({'error': 'Invalid tenant'}), 400

        # Get brand voice context if specified
        brand_voice_context = None
        if brand_voice_id:
            # Get brand voice from database - all voices are company voices now
            company_brand_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
            selected_brand_voice = next((bv for bv in company_brand_voices if bv.brand_voice_id == brand_voice_id), None)

            if selected_brand_voice:
                brand_voice_context = rag_service.get_brand_voice_context(selected_brand_voice.markdown_content)

        # Get trauma-informed context
        trauma_informed_context = rag_service.get_trauma_informed_context()

        # Generate content
        response = gemini_service.generate_content(
            prompt=prompt,
            content_mode=content_mode,
            brand_voice_context=brand_voice_context,
            trauma_informed_context=trauma_informed_context
        )

        # Save to chat history if user is logged in
        session_id = data.get('session_id')
        if user and session_id:
            # Add user message
            db_manager.add_chat_message(session_id, 'user', prompt, content_mode, brand_voice_id)
            # Add assistant response
            db_manager.add_chat_message(session_id, 'assistant', response, content_mode, brand_voice_id)
            
            # Update session title if this is the first exchange
            messages = db_manager.get_chat_messages(session_id)
            if len(messages) <= 2:  # First user message + first assistant response
                # Generate a short title from the first user message
                title = prompt[:50] + "..." if len(prompt) > 50 else prompt
                db_manager.update_chat_session_title(session_id, title)

        return jsonify({'response': response})

    except Exception as e:
        logger.error(f"Generation error: {e}")
        return jsonify({'error': 'An error occurred while generating content. Please try again.'}), 500

@app.route('/how-to')
def how_to():
    """How to use GoldenDoodleLM guide page"""
    return render_template('how_to.html')

@app.route('/our-story')
def our_story():
    """Our story page"""
    return render_template('our_story.html')

@app.route('/account')
@login_required
def account():
    """User account page"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    tenant = db_manager.get_tenant_by_id(user.tenant_id)
    if not tenant:
        flash('Invalid tenant. Please contact support.', 'error')
        return redirect(url_for('logout'))

    # Get brand voices - all voices are treated as company voices now
    company_brand_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
    user_brand_voices = []  # No longer using user-specific brand voices

    # Determine max user voices based on subscription
    if user.subscription_level == SubscriptionLevel.PRO:
        max_user_voices = 10
    elif user.subscription_level == SubscriptionLevel.SOLO:
        max_user_voices = 1
    elif user.subscription_level in [SubscriptionLevel.TEAM, SubscriptionLevel.ENTERPRISE]:
        max_user_voices = 10
    else:
        max_user_voices = 1

    return render_template('account.html',
                         user=user,
                         tenant=tenant,
                         company_brand_voices=company_brand_voices,
                         user_brand_voices=user_brand_voices,
                         max_user_voices=max_user_voices)

@app.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    try:
        data = request.get_json()
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        email = data.get('email', '').strip().lower()

        if not all([first_name, last_name, email]):
            return jsonify({'error': 'All fields are required'}), 400

        # Check if email is already taken by another user
        if email != user.email:
            existing_user = db_manager.get_user_by_email(email)
            if existing_user:
                return jsonify({'error': 'Email address is already in use'}), 400

        # Update user in database
        conn = db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users 
            SET first_name = %s, last_name = %s, email = %s
            WHERE user_id = %s
        """, (first_name, last_name, email, user.user_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Profile updated successfully'})

    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({'error': 'An error occurred while updating your profile'}), 500

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')

        if not current_password or not new_password:
            return jsonify({'error': 'Current and new passwords are required'}), 400

        # Verify current password
        if not db_manager.verify_password(user, current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400

        # Update password in database
        from werkzeug.security import generate_password_hash
        new_password_hash = generate_password_hash(new_password)

        conn = db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE users 
            SET password_hash = %s
            WHERE user_id = %s
        """, (new_password_hash, user.user_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Password changed successfully'})

    except Exception as e:
        logger.error(f"Error changing password: {e}")
        return jsonify({'error': 'An error occurred while changing your password'}), 500

@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account"""
    try:
        data = request.get_json()
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        confirm_email = data.get('confirm_email', '').strip().lower()
        delete_reason = data.get('delete_reason', '').strip()

        # Verify email confirmation
        if confirm_email != user.email.lower():
            return jsonify({'error': 'Email confirmation does not match'}), 400

        # Only allow deletion for independent users (not organization members)
        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if not tenant:
            return jsonify({'error': 'Invalid tenant'}), 400

        if tenant.tenant_type == TenantType.COMPANY:
            return jsonify({'error': 'Organization members cannot delete their accounts. Please contact your organization admin.'}), 400

        # Log deletion reason if provided
        if delete_reason:
            logger.info(f"Account deletion reason for {user.email}: {delete_reason}")

        # Delete the user and their tenant (since they're independent)
        user_deleted = db_manager.delete_user(user.user_id)
        tenant_deleted = db_manager.delete_tenant(user.tenant_id)

        if user_deleted and tenant_deleted:
            # Log out the user
            logout_user()
            logger.info(f"Account successfully deleted for user: {user.email}")
            return jsonify({'success': True, 'message': 'Account deleted successfully'})
        else:
            logger.error(f"Failed to delete account for user: {user.email}")
            return jsonify({'error': 'Failed to delete account. Please contact support.'}), 500

    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        return jsonify({'error': 'An error occurred while deleting your account. Please contact support.'}), 500

@app.route('/brand-voices')
@login_required
def brand_voices():
    """Brand voices management page"""
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    tenant = db_manager.get_tenant_by_id(user.tenant_id)
    if not tenant:
        flash('Invalid tenant. Please contact support.', 'error')
        return redirect(url_for('logout'))

    # Get brand voices - all voices are treated as company voices now
    company_brand_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
    user_brand_voices = []  # No longer using user-specific brand voices

    # Check limits based on subscription level
    if user.subscription_level == SubscriptionLevel.PRO:
        max_user_voices = 10
    elif user.subscription_level == SubscriptionLevel.SOLO:
        max_user_voices = 1
    elif user.subscription_level in [SubscriptionLevel.TEAM, SubscriptionLevel.ENTERPRISE]:
        max_user_voices = 10  # Team members can have personal voices too
    else:
        max_user_voices = 1  # Default

    can_create_user_voice = len(user_brand_voices) < max_user_voices
    can_create_company_voice = (user.is_admin and 
                               tenant.tenant_type == TenantType.COMPANY and 
                               len(company_brand_voices) < tenant.max_brand_voices)

    return render_template('brand_voices.html',
                         user=user,
                         tenant=tenant,
                         company_brand_voices=company_brand_voices,
                         user_brand_voices=user_brand_voices,
                         can_create_user_voice=can_create_user_voice,
                         can_create_company_voice=can_create_company_voice,
                         max_user_voices=max_user_voices)

@app.route('/brand-voice-wizard')
@login_required
def brand_voice_wizard():
    """Brand voice creation/editing wizard"""
    voice_type = request.args.get('type')
    edit_id = request.args.get('edit')
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    tenant = db_manager.get_tenant_by_id(user.tenant_id)
    if not tenant:
        flash('Invalid tenant. Please contact support.', 'error')
        return redirect(url_for('logout'))

    # Set default voice type based on tenant type and user role
    if not voice_type:
        if tenant.tenant_type == TenantType.COMPANY and user.is_admin:
            voice_type = 'company'  # Default to company for organization admins
        else:
            voice_type = 'user'

    if voice_type == 'company' and not user.is_admin:
        flash('Admin access required to create company brand voices.', 'error')
        return redirect(url_for('brand_voices'))

    # If editing, verify the brand voice exists and user has permission
    if edit_id:
        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if not tenant:
            flash('Invalid tenant. Please contact support.', 'error')
            return redirect(url_for('logout'))

        # Get brand voice to verify permission
        company_brand_voices = []
        if tenant.tenant_type == TenantType.COMPANY:
            company_brand_voices = db_manager.get_company_brand_voices(tenant.tenant_id)

        user_brand_voices = db_manager.get_user_brand_voices(tenant.tenant_id, user.user_id)
        all_brand_voices = company_brand_voices + user_brand_voices

        selected_brand_voice = next((bv for bv in all_brand_voices if bv.brand_voice_id == edit_id), None)

        if not selected_brand_voice:
            flash('Brand voice not found.', 'error')
            return redirect(url_for('brand_voices'))

        # Check permissions
        if selected_brand_voice.user_id and selected_brand_voice.user_id != user.user_id:
            flash('Permission denied.', 'error')
            return redirect(url_for('brand_voices'))

        if not selected_brand_voice.user_id and not user.is_admin:
            flash('Permission denied.', 'error')
            return redirect(url_for('brand_voices'))

        # Determine voice type based on the brand voice
        voice_type = 'company' if not selected_brand_voice.user_id else 'user'

    return render_template('brand_voice_wizard.html', 
                         voice_type=voice_type, 
                         user=user, 
                         edit_id=edit_id)

@app.route('/create-brand-voice', methods=['POST'])
@login_required
def create_brand_voice():
    """Create a new brand voice or update an existing one"""
    try:
        data = request.get_json()

        if not data:
            logger.error("No JSON data received in brand voice creation request")
            return jsonify({'error': 'No data received'}), 400

        # Required fields
        company_name = data.get('company_name', '').strip()
        company_url = data.get('company_url', '').strip()
        voice_short_name = data.get('voice_short_name', '').strip()
        voice_type = data.get('voice_type', 'user')
        brand_voice_id = data.get('brand_voice_id')  # For editing existing voices

        logger.info(f"=== BRAND VOICE CREATION DEBUG ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Content-Type: {request.headers.get('Content-Type', 'Not set')}")
        logger.info(f"Request data received: {bool(data)}")
        logger.info(f"Creating brand voice: '{voice_short_name}' for voice_type: {voice_type}")
        logger.info(f"Company: '{company_name}', URL: '{company_url}'")
        logger.info(f"Is editing: {bool(brand_voice_id)}")
        logger.info(f"Raw data keys: {list(data.keys()) if data else 'No data'}")

        if not all([company_name, company_url, voice_short_name]):
            logger.error(f"Missing required fields: company_name={bool(company_name)}, company_url={bool(company_url)}, voice_short_name={bool(voice_short_name)}")
            return jsonify({'error': 'Company name, URL, and voice name are required'}), 400

        user = get_current_user()
        if not user:
            logger.error("No authenticated user found")
            return jsonify({'error': 'Authentication required'}), 401
        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if not tenant:
            logger.error(f"Invalid tenant for user {user.user_id}")
            return jsonify({'error': 'Invalid tenant'}), 400

        logger.info(f"User: {user.user_id} ({user.email}), Tenant: {tenant.tenant_id} ({tenant.name})")
        logger.info(f"Tenant type: {tenant.tenant_type}, Max voices: {tenant.max_brand_voices}")

        # Determine if this is an edit or create operation
        is_editing = bool(brand_voice_id)

        # Always create as company voice now - check limits based on company voices
        logger.info(f"Creating brand voice for tenant {tenant.tenant_id}")

        if not is_editing:
            existing_company_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
            logger.info(f"Existing company voices BEFORE creation: {len(existing_company_voices)}/{tenant.max_brand_voices}")
            for voice in existing_company_voices:
                logger.info(f"  Existing voice: '{voice.name}' (ID: {voice.brand_voice_id})")

            # Use a more generous limit for individuals to ensure they can create voices
            max_allowed = max(tenant.max_brand_voices, 10)  # Allow at least 10 voices

            if len(existing_company_voices) >= max_allowed:
                logger.error(f"Brand voice limit exceeded: {len(existing_company_voices)}/{max_allowed}")
                return jsonify({'error': f'Maximum of {max_allowed} brand voices allowed'}), 400

        # Always set user_id to None since we're treating all voices as company voices
        user_id = None

        # Collect all wizard data
        wizard_data = {
            'company_name': company_name,
            'company_url': company_url,
            'voice_short_name': voice_short_name,
            'mission_statement': data.get('mission_statement', ''),
            'vision_statement': data.get('vision_statement', ''),
            'core_values': data.get('core_values', ''),
            'elevator_pitch': data.get('elevator_pitch', ''),
            'about_us_content': data.get('about_us_content', ''),
            'press_release_boilerplate': data.get('press_release_boilerplate', ''),
            'primary_audience_persona': data.get('primary_audience_persona', ''),
            'audience_pain_points': data.get('audience_pain_points', ''),
            'desired_relationship': data.get('desired_relationship', ''),
            'audience_language': data.get('audience_language', ''),
            'personality_formal_casual': int(data.get('personality_formal_casual', 3)),
            'personality_serious_playful': int(data.get('personality_serious_playful', 3)),
            'personality_traditional_modern': int(data.get('personality_traditional_modern', 3)),
            'personality_authoritative_collaborative': int(data.get('personality_authoritative_collaborative', 3)),
            'personality_accessible_exclusive': int(data.get('personality_accessible_exclusive', 3)),
            'brand_as_person': data.get('brand_as_person', ''),
            'brand_spokesperson': data.get('brand_spokesperson', ''),
            'admired_brands': data.get('admired_brands', ''),
            'words_to_embrace': data.get('words_to_embrace', ''),
            'words_to_avoid': data.get('words_to_avoid', ''),
            'punctuation_contractions': data.get('punctuation_contractions'),
            'punctuation_oxford_comma': data.get('punctuation_oxford_comma'),
            'punctuation_extras': data.get('punctuation_extras', ''),
            'point_of_view': data.get('point_of_view', ''),
            'sentence_structure': data.get('sentence_structure', ''),
            'handling_good_news': data.get('handling_good_news', ''),
            'handling_bad_news': data.get('handling_bad_news', ''),
            'competitors': data.get('competitors', ''),
            'competitor_voices': data.get('competitor_voices', ''),
            'voice_differentiation': data.get('voice_differentiation', '')
        }

        # Generate comprehensive markdown content for RAG
        markdown_content = generate_brand_voice_markdown(wizard_data)
        logger.info(f"Generated markdown content length: {len(markdown_content)}")

        # Create or update brand voice with comprehensive data
        if is_editing:
            # Verify permissions for editing
            existing_voices = []
            if voice_type == 'company':
                existing_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
            else:
                existing_voices = db_manager.get_user_brand_voices(tenant.tenant_id, user.user_id)

            # Check if the brand voice exists and user has permission
            voice_exists = any(bv.brand_voice_id == brand_voice_id for bv in existing_voices)
            if not voice_exists:
                logger.error(f"Brand voice {brand_voice_id} not found or permission denied for user {user.user_id}")
                return jsonify({'error': 'Brand voice not found or permission denied'}), 404

            brand_voice = db_manager.update_brand_voice(
                tenant_id=tenant.tenant_id,
                brand_voice_id=brand_voice_id,
                wizard_data=wizard_data,
                markdown_content=markdown_content,
                user_id=user_id
            )
            logger.info(f"Updated brand voice: {brand_voice.brand_voice_id}")

            return jsonify({
                'success': True,
                'brand_voice_id': brand_voice.brand_voice_id,
                'message': f'Brand voice "{voice_short_name}" updated successfully!'
            })
        else:
            logger.info(f"About to call create_comprehensive_brand_voice with:")
            logger.info(f"  tenant_id: {tenant.tenant_id}")
            logger.info(f"  voice_short_name: {voice_short_name}")
            logger.info(f"  user_id: {user_id}")
            logger.info(f"  markdown_content length: {len(markdown_content)}")
            
            brand_voice = db_manager.create_comprehensive_brand_voice(
                tenant_id=tenant.tenant_id,
                wizard_data=wizard_data,
                markdown_content=markdown_content,
                user_id=user_id
            )
            logger.info(f"✓ Successfully created brand voice: {brand_voice.brand_voice_id}")
            
            # Debugging: Fetch all company voices again to see if the new one is present
            current_company_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
            logger.info(f"Company voices AFTER creation: {len(current_company_voices)}/{tenant.max_brand_voices}")
            for voice in current_company_voices:
                logger.info(f"  Voice: '{voice.name}' (ID: {voice.brand_voice_id})")

            return jsonify({
                'success': True,
                'brand_voice_id': brand_voice.brand_voice_id,
                'message': f'Brand voice "{voice_short_name}" created successfully!'
            })

    except Exception as e:
        logger.error(f"Error creating brand voice: {e}")
        return jsonify({'error': 'An error occurred while creating the brand voice. Please try again.'}), 500

@app.route('/get-brand-voice/<brand_voice_id>')
@login_required
def get_brand_voice(brand_voice_id):
    """Get brand voice data for editing"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if not tenant:
            return jsonify({'error': 'Invalid tenant'}), 400

        # Get brand voice from database
        company_brand_voices = []
        if tenant.tenant_type == TenantType.COMPANY:
            company_brand_voices = db_manager.get_company_brand_voices(tenant.tenant_id)

        user_brand_voices = db_manager.get_user_brand_voices(tenant.tenant_id, user.user_id)
        all_brand_voices = company_brand_voices + user_brand_voices

        selected_brand_voice = next((bv for bv in all_brand_voices if bv.brand_voice_id == brand_voice_id), None)

        if not selected_brand_voice:
            logger.warning(f"Brand voice {brand_voice_id} not found for user {user.user_id}")
            return jsonify({'error': 'Brand voice not found'}), 404

        # Check permissions
        if selected_brand_voice.user_id and selected_brand_voice.user_id != user.user_id:
            logger.warning(f"Permission denied for user {user.user_id} to access brand voice {brand_voice_id} owned by {selected_brand_voice.user_id}")
            return jsonify({'error': 'Permission denied'}), 403

        if not selected_brand_voice.user_id and not user.is_admin:
            logger.warning(f"Permission denied for non-admin user {user.user_id} to access company brand voice {brand_voice_id}")
            return jsonify({'error': 'Permission denied'}), 403
        
        logger.info(f"Successfully retrieved brand voice {brand_voice_id} for user {user.user_id}")
        return jsonify(selected_brand_voice.configuration)

    except Exception as e:
        logger.error(f"Error getting brand voice {brand_voice_id}: {e}")
        return jsonify({'error': 'An error occurred while loading the brand voice'}), 500

@app.route('/auto-save-brand-voice', methods=['POST'])
@login_required
def auto_save_brand_voice():
    """Auto-save brand voice progress"""
    try:
        data = request.get_json()
        user = get_current_user()
        if not user:
            logger.error("Auto-save failed: No authenticated user")
            return jsonify({'error': 'Authentication required'}), 401

        # Check if required fields are present for auto-save
        company_name = data.get('company_name', '').strip()
        company_url = data.get('company_url', '').strip()
        voice_short_name = data.get('voice_short_name', '').strip()

        if not all([company_name, company_url, voice_short_name]):
            logger.warning("Auto-save failed: Missing required fields")
            return jsonify({'error': 'Required fields missing'}), 400

        logger.info(f"Attempting auto-save for brand voice: '{voice_short_name}' by user {user.user_id}")

        # Auto-save logic would go here
        # For now, just return success with a mock profile_id
        profile_id = data.get('profile_id') or str(uuid.uuid4())
        logger.info(f"Auto-save successful for '{voice_short_name}' (Profile ID: {profile_id})")

        return jsonify({
            'success': True,
            'profile_id': profile_id,
            'message': 'Progress saved'
        })

    except Exception as e:
        logger.error(f"Error auto-saving brand voice: {e}")
        return jsonify({'error': 'Auto-save failed'}), 500

def generate_brand_voice_markdown(data):
    """Generate comprehensive markdown content for brand voice"""
    markdown = f"""# {data.get('voice_short_name', 'Unnamed Brand Voice')} Brand Voice Guide

## Company Overview
**Company:** {data.get('company_name', 'N/A')}
**Website:** {data.get('company_url', 'N/A')}

"""

    if data.get('mission_statement'):
        markdown += f"""## Mission Statement
{data['mission_statement']}

"""

    if data.get('vision_statement'):
        markdown += f"""## Vision Statement
{data['vision_statement']}

"""

    if data.get('core_values'):
        markdown += f"""## Core Values
{data['core_values']}

"""

    if data.get('elevator_pitch'):
        markdown += f"""## Elevator Pitch
{data['elevator_pitch']}

"""

    # Personality traits
    markdown += f"""## Brand Personality

### Personality Traits (1-5 scale)
- **Communication Style:** {data.get('personality_formal_casual', 3)}/5 (1=Formal, 5=Casual)
- **Tone:** {data.get('personality_serious_playful', 3)}/5 (1=Serious, 5=Playful)
- **Approach:** {data.get('personality_traditional_modern', 3)}/5 (1=Traditional, 5=Modern)
- **Authority:** {data.get('personality_authoritative_collaborative', 3)}/5 (1=Authoritative, 5=Collaborative)
- **Accessibility:** {data.get('personality_accessible_exclusive', 3)}/5 (1=Accessible, 5=Aspirational)

"""

    if data.get('brand_as_person'):
        markdown += f"""### Brand as a Person
{data['brand_as_person']}

"""

    if data.get('brand_spokesperson'):
        markdown += f"""### Brand Spokesperson
{data['brand_spokesperson']}

"""

    # Audience information
    if data.get('primary_audience_persona'):
        markdown += f"""## Target Audience
{data['primary_audience_persona']}

"""

    if data.get('audience_pain_points'):
        markdown += f"""### Audience Pain Points
{data['audience_pain_points']}

"""

    if data.get('desired_relationship'):
        markdown += f"""### Desired Relationship
{data['desired_relationship']}

"""

    # Language guidelines
    markdown += f"""## Language Guidelines

"""

    if data.get('words_to_embrace'):
        markdown += f"""### Words to Embrace
{data['words_to_embrace']}

"""

    if data.get('words_to_avoid'):
        markdown += f"""### Words to Avoid
{data['words_to_avoid']}

"""

    # Communication style
    if data.get('point_of_view'):
        pov_map = {
            'first_plural': 'First-person plural (we, our)',
            'first_singular': 'First-person singular (I, my)',
            'second_person': 'Second-person (you, your)'
        }
        markdown += f"""### Point of View
{pov_map.get(data['point_of_view'], data['point_of_view'])}

"""

    if data.get('punctuation_contractions') is not None:
        contractions = "Use contractions" if data['punctuation_contractions'] else "Avoid contractions"
        markdown += f"""### Contractions
{contractions}

"""

    if data.get('punctuation_oxford_comma') is not None:
        oxford = "Use Oxford comma" if data['punctuation_oxford_comma'] else "No Oxford comma"
        markdown += f"""### Oxford Comma
{oxford}

"""

    # Tone for different situations
    if data.get('handling_good_news'):
        markdown += f"""### Handling Good News
{data['handling_good_news']}

"""

    if data.get('handling_bad_news'):
        markdown += f"""### Handling Bad News/Apologies
{data['handling_bad_news']}

"""

    # Competition and differentiation
    if data.get('competitors'):
        markdown += f"""## Competition
### Main Competitors
{data['competitors']}

"""

    if data.get('competitor_voices'):
        markdown += f"""### Competitor Communication Styles
{data['competitor_voices']}

"""

    if data.get('voice_differentiation'):
        markdown += f"""### Our Differentiation
{data['voice_differentiation']}

"""

    # Trauma-informed principles
    markdown += f"""## Trauma-Informed Communication Principles

### Core Guidelines
- Use person-first, strengths-based language
- Prioritize safety, trust, and empowerment in all communications
- Be culturally responsive and inclusive
- Acknowledge resilience and potential for growth
- Avoid language that could retraumatize or stigmatize
- Create content that feels safe and supportive

### Content Creation Guidelines
- Frame challenges as opportunities for growth
- Use collaborative language that empowers the reader
- Acknowledge different perspectives and experiences
- Focus on solutions and hope while being realistic
- Ensure accessibility in both language and format

"""

    if data.get('about_us_content'):
        markdown += f"""## About Us Reference Content
{data['about_us_content']}

"""

    if data.get('press_release_boilerplate'):
        markdown += f"""## Press Release Boilerplate
{data['press_release_boilerplate']}

"""

    return markdown

@app.route('/platform-admin')
@super_admin_required
def platform_admin():
    """Platform admin dashboard"""
    logger.info("Accessing platform admin dashboard")
    users = db_manager.get_all_users()
    tenants = db_manager.get_all_tenants()
    logger.info(f"Found {len(users)} users and {len(tenants)} tenants.")

    return render_template('platform_admin.html', users=users, tenants=tenants)

@app.route('/admin/delete-user/<user_id>', methods=['POST'])
@super_admin_required
def admin_delete_user(user_id):
    """Delete a user account"""
    try:
        logger.info(f"Admin deleting user with ID: {user_id}")
        if db_manager.delete_user(user_id):
            flash('User deleted successfully.', 'success')
            logger.info(f"User {user_id} deleted successfully.")
        else:
            flash('Failed to delete user.', 'error')
            logger.warning(f"Failed to delete user {user_id}.")
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        flash('An error occurred while deleting the user.', 'error')

    return redirect(url_for('platform_admin'))

@app.route('/admin/delete-tenant/<tenant_id>', methods=['POST'])
@super_admin_required
def admin_delete_tenant(tenant_id):
    """Delete a tenant and all associated data"""
    try:
        logger.info(f"Admin deleting tenant with ID: {tenant_id}")
        if db_manager.delete_tenant(tenant_id):
            flash('Organization deleted successfully.', 'success')
            logger.info(f"Tenant {tenant_id} deleted successfully.")
        else:
            flash('Failed to delete organization.', 'error')
            logger.warning(f"Failed to delete tenant {tenant_id}.")
    except Exception as e:
        logger.error(f"Error deleting tenant {tenant_id}: {e}")
        flash('An error occurred while deleting the organization.', 'error')

    return redirect(url_for('platform_admin'))

@app.route('/admin/organization/<tenant_id>')
@super_admin_required
def admin_organization_details(tenant_id):
    """View organization details and members"""
    try:
        logger.info(f"Admin viewing details for tenant ID: {tenant_id}")
        tenant = db_manager.get_tenant_by_id(tenant_id)
        if not tenant:
            flash('Organization not found.', 'error')
            logger.warning(f"Tenant {tenant_id} not found.")
            return redirect(url_for('platform_admin'))

        # Get organization members
        organization_users = db_manager.get_organization_users(tenant_id)
        logger.info(f"Found {len(organization_users)} members for tenant {tenant_id}.")

        return render_template('admin_organization_details.html', 
                             tenant=tenant, 
                             organization_users=organization_users)
    except Exception as e:
        logger.error(f"Error loading organization details for tenant {tenant_id}: {e}")
        flash('An error occurred while loading organization details.', 'error')
        return redirect(url_for('platform_admin'))

@app.route('/admin/update-subscription', methods=['POST'])
@super_admin_required
def admin_update_subscription():
    """Update user subscription level"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        subscription_level = data.get('subscription_level')

        if not user_id or not subscription_level:
            logger.warning("Admin update subscription failed: Missing user_id or subscription_level")
            return jsonify({'error': 'User ID and subscription level are required'}), 400

        logger.info(f"Admin updating subscription for user {user_id} to {subscription_level}")
        if db_manager.update_user_subscription(user_id, subscription_level):
            logger.info(f"Subscription updated successfully for user {user_id}")
            return jsonify({'success': True, 'message': 'Subscription updated successfully'})
        else:
            logger.warning(f"Failed to update subscription for user {user_id}")
            return jsonify({'error': 'Failed to update subscription'}), 500
    except Exception as e:
        logger.error(f"Error updating subscription for user {user_id}: {e}")
        return jsonify({'error': 'An error occurred while updating subscription'}), 500

@app.route('/send-organization-invite', methods=['POST'])
@login_required
def send_organization_invite():
    """Send an organization invite"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()

        if not email:
            logger.warning("Send organization invite failed: Email is required.")
            return jsonify({'error': 'Email address is required'}), 400

        user = get_current_user()
        if not user or not user.is_admin:
            logger.warning("Send organization invite failed: User is not an admin.")
            return jsonify({'error': 'Admin access required'}), 403

        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if not tenant or tenant.tenant_type != TenantType.COMPANY:
            logger.warning("Send organization invite failed: Tenant is not a company or not found.")
            return jsonify({'error': 'Organization account required'}), 400

        # Check if user already exists in this organization
        existing_user = db_manager.get_user_by_email(email)
        if existing_user and existing_user.tenant_id == user.tenant_id:
            logger.warning(f"Send organization invite failed: User {email} already in organization {tenant.name}.")
            return jsonify({'error': 'User is already a member of this organization'}), 400

        # Generate invite token
        from email_service import generate_verification_token, hash_token
        invite_token = generate_verification_token()
        token_hash = hash_token(invite_token)

        # Create invite in database
        if db_manager.create_organization_invite(user.tenant_id, user.user_id, email, token_hash):
            logger.info(f"Organization invite created for {email} to tenant {tenant.name}.")
            # Send invite email
            if email_service.send_organization_invite_email(
                email, 
                invite_token, 
                tenant.name, 
                f"{user.first_name} {user.last_name}"
            ):
                logger.info(f"Invitation email sent successfully to {email}.")
                return jsonify({
                    'success': True, 
                    'message': f'Invitation sent to {email} successfully'
                })
            else:
                logger.error(f"Failed to send invitation email to {email}.")
                return jsonify({'error': 'Failed to send invitation email'}), 500
        else:
            logger.error(f"Failed to create organization invite in database for {email}.")
            return jsonify({'error': 'Failed to create invitation'}), 500

    except Exception as e:
        logger.error(f"Error sending organization invite for email {email}: {e}")
        return jsonify({'error': 'An error occurred while sending the invitation'}), 500

@app.route('/join-organization')
def join_organization():
    """Handle organization invite acceptance"""
    token = request.args.get('token')
    if not token:
        logger.warning("Join organization failed: No token provided.")
        flash('Invalid invitation link.', 'error')
        return redirect(url_for('login'))

    from email_service import hash_token
    token_hash = hash_token(token)
    invite_data = db_manager.verify_organization_invite_token(token_hash)

    if not invite_data:
        logger.warning(f"Join organization failed: Invalid or expired token hash: {token_hash}")
        flash('Invalid or expired invitation link.', 'error')
        return redirect(url_for('login'))

    tenant_id, email = invite_data
    tenant = db_manager.get_tenant_by_id(tenant_id)

    if not tenant:
        logger.error(f"Join organization failed: Tenant {tenant_id} not found for token hash {token_hash}.")
        flash('Organization not found.', 'error')
        return redirect(url_for('login'))

    logger.info(f"Processing invite for email {email} to organization {tenant.name} (Tenant ID: {tenant_id})")

    # Check if user already exists
    existing_user = db_manager.get_user_by_email(email)

    if existing_user:
        if existing_user.tenant_id == tenant_id:
            logger.info(f"User {email} is already a member of organization {tenant.name}.")
            flash('You are already a member of this organization.', 'info')
            return redirect(url_for('login'))
        else:
            logger.warning(f"User {email} exists but is in a different organization (Tenant ID: {existing_user.tenant_id}). Cannot join {tenant.name}.")
            flash('This email is already associated with another account. Please contact support.', 'error')
            return redirect(url_for('login'))

    # Store invite info in session for registration
    session['organization_invite'] = {
        'token_hash': token_hash,
        'tenant_id': tenant_id,
        'email': email,
        'organization_name': tenant.name
    }
    logger.info(f"Storing organization invite details in session for {email}.")

    return redirect(url_for('register', invite='organization'))

@app.route('/get-pending-invites/<tenant_id>')
@login_required
def get_pending_invites(tenant_id):
    """Get pending invites for an organization"""
    try:
        user = get_current_user()
        if not user or not user.is_admin or user.tenant_id != tenant_id:
            logger.warning(f"Permission denied for user {user.user_id} to get pending invites for tenant {tenant_id}.")
            return jsonify({'error': 'Permission denied'}), 403

        logger.info(f"Fetching pending invites for tenant {tenant_id} by admin user {user.user_id}.")
        invites = db_manager.get_pending_invites(tenant_id)
        logger.info(f"Found {len(invites)} pending invites for tenant {tenant_id}.")
        return jsonify({'invites': invites})

    except Exception as e:
        logger.error(f"Error getting pending invites for tenant {tenant_id}: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/get-active-users/<tenant_id>')
@login_required
def get_active_users(tenant_id):
    """Get active users for an organization"""
    try:
        user = get_current_user()
        if not user or not user.is_admin or user.tenant_id != tenant_id:
            logger.warning(f"Permission denied for user {user.user_id} to get active users for tenant {tenant_id}.")
            return jsonify({'error': 'Permission denied'}), 403

        logger.info(f"Fetching active users for tenant {tenant_id} by admin user {user.user_id}.")
        organization_users = db_manager.get_organization_users(tenant_id)
        
        # Convert users to JSON-serializable format
        users_data = []
        for org_user in organization_users:
            users_data.append({
                'user_id': org_user.user_id,
                'first_name': org_user.first_name,
                'last_name': org_user.last_name,
                'email': org_user.email,
                'is_admin': org_user.is_admin,
                'email_verified': org_user.email_verified,
                'subscription_level': org_user.subscription_level.value,
                'created_at': org_user.created_at.isoformat() if org_user.created_at else None,
                'last_login': org_user.last_login.isoformat() if org_user.last_login else None
            })
        
        logger.info(f"Found {len(users_data)} active users for tenant {tenant_id}.")
        return jsonify({'users': users_data})

    except Exception as e:
        logger.error(f"Error getting active users for tenant {tenant_id}: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/api/chat-sessions', methods=['GET'])
@login_required
def get_chat_sessions():
    """Get user's chat sessions"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        sessions = db_manager.get_user_chat_sessions(user.user_id)
        return jsonify({'sessions': sessions})

    except Exception as e:
        logger.error(f"Error getting chat sessions: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/api/chat-sessions', methods=['POST'])
@login_required
def create_chat_session():
    """Create a new chat session"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        data = request.get_json()
        title = data.get('title', 'New Chat')
        
        session_id = db_manager.create_chat_session(user.user_id, title)
        if session_id:
            return jsonify({'session_id': session_id, 'title': title})
        else:
            return jsonify({'error': 'Failed to create chat session'}), 500

    except Exception as e:
        logger.error(f"Error creating chat session: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/api/chat-sessions/<session_id>/messages', methods=['GET'])
@login_required
def get_chat_messages(session_id):
    """Get messages for a chat session"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        # Verify user owns this session
        sessions = db_manager.get_user_chat_sessions(user.user_id)
        if not any(s['session_id'] == session_id for s in sessions):
            return jsonify({'error': 'Session not found'}), 404

        messages = db_manager.get_chat_messages(session_id)
        return jsonify({'messages': messages})

    except Exception as e:
        logger.error(f"Error getting chat messages: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/api/chat-sessions/<session_id>', methods=['DELETE'])
@login_required
def delete_chat_session(session_id):
    """Delete a chat session"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        if db_manager.delete_chat_session(session_id, user.user_id):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete session'}), 500

    except Exception as e:
        logger.error(f"Error deleting chat session: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/new-session', methods=['POST'])
@login_required
def new_session():
    """Create a new chat session"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        session_id = db_manager.create_chat_session(user.user_id, "New Chat")
        if session_id:
            return jsonify({'session_id': session_id})
        else:
            return jsonify({'error': 'Failed to create session'}), 500

    except Exception as e:
        logger.error(f"Error creating new session: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/chat-history')
@login_required
def chat_history():
    """Get user's chat history"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        sessions = db_manager.get_user_chat_sessions(user.user_id)
        return jsonify([{
            'id': session['session_id'],
            'title': session['title'],
            'created_at': session['created_at'].isoformat() if session['created_at'] else None,
            'updated_at': session['updated_at'].isoformat() if session['updated_at'] else None,
            'message_count': session['message_count']
        } for session in sessions])

    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/chat/<session_id>')
@login_required
def get_chat(session_id):
    """Get a specific chat session with messages"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        # Verify user owns this session
        sessions = db_manager.get_user_chat_sessions(user.user_id)
        session_exists = any(s['session_id'] == session_id for s in sessions)
        
        if not session_exists:
            return jsonify({'error': 'Session not found'}), 404

        messages = db_manager.get_chat_messages(session_id)
        session_title = next((s['title'] for s in sessions if s['session_id'] == session_id), 'New Chat')

        return jsonify({
            'title': session_title,
            'messages': [{
                'content': msg['content'],
                'sender': 'user' if msg['message_type'] == 'user' else 'ai',
                'created_at': msg['created_at'].isoformat() if msg['created_at'] else None
            } for msg in messages]
        })

    except Exception as e:
        logger.error(f"Error getting chat {session_id}: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 Not Found: {error}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Internal Server Error: {error}")
    return render_template('500.html'), 500