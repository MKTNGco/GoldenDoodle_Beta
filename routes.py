from flask import render_template, request, redirect, url_for, flash, session, jsonify
from urllib.parse import urlparse
from app import app
from auth import login_required, admin_required, super_admin_required, get_current_user, login_user, logout_user
from database import db_manager
from gemini_service import gemini_service
from rag_service import rag_service
from models import TenantType, SubscriptionLevel, CONTENT_MODE_CONFIG, BrandVoice
from email_service import email_service, generate_verification_token, hash_token
from stripe_service import stripe_service
from analytics_service import analytics_service
import uuid
from datetime import datetime, timedelta
import secrets
import traceback
import stripe
import os
import logging
import psycopg2.extras
import user_source_tracker

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

    # Check for invitation codes via URL parameters
    invitation_code = request.args.get('ref') or request.args.get('invite')
    invitation_data = None

    if invitation_code and invitation_code != 'organization':
        # Look up invitation in the invitations.json file
        from invitation_manager import invitation_manager
        invitation_data = invitation_manager.get_invitation(invitation_code)

        if invitation_data and invitation_data['status'] == 'pending':
            logger.info(f"Valid invitation found for code: {invitation_code}")
        elif invitation_data:
            logger.warning(f"Invitation {invitation_code} found but status is: {invitation_data['status']}")
            flash(f'This invitation has already been {invitation_data["status"]}.', 'warning')
            invitation_data = None
        else:
            logger.warning(f"Invalid invitation code: {invitation_code}")
            flash('Invalid or expired invitation code.', 'error')

    # Handle payment cancellation
    if request.args.get('payment_cancelled'):
        flash('Payment was cancelled. You can complete your registration with a free plan or try again with a paid plan.', 'info')

    if request.method == 'POST':
        # Check if this is an AJAX request expecting JSON
        expects_json = (request.is_json or 
                       'application/json' in request.headers.get('Accept', '') or 
                       request.headers.get('Content-Type') == 'application/x-www-form-urlencoded')

        try:
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            organization_name = request.form.get('organization_name', '').strip()
            user_type = request.form.get('user_type', 'independent')
            subscription_level = request.form.get('subscription_level', 'free')

            # Validation
            if not all([first_name, last_name, email, password]):
                if expects_json:
                    return jsonify({'error': 'All fields are required.', 'retry': True}), 400
                flash('All fields are required.', 'error')
                return render_template('register.html', 
                                     is_organization_invite=is_organization_invite,
                                     organization_invite=organization_invite)

            # Handle organization invite registration
            if organization_invite:
                if email != organization_invite['email']:
                    if expects_json:
                        return jsonify({'error': 'You must use the invited email address to register.', 'retry': True}), 400
                    flash('You must use the invited email address to register.', 'error')
                    return render_template('register.html', 
                                         is_organization_invite=is_organization_invite,
                                         organization_invite=organization_invite)

                # Check if user already exists
                existing_user = db_manager.get_user_by_email(email)
                if existing_user:
                    if expects_json:
                        return jsonify({'error': 'An account with this email already exists.', 'retry': True}), 400
                    flash('An account with this email already exists.', 'error')
                    return render_template('register.html', 
                                         is_organization_invite=is_organization_invite,
                                         organization_invite=organization_invite)

                # Create user as organization member with predetermined settings
                user_id = db_manager.create_user(
                    tenant_id=organization_invite['tenant_id'],
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password=password,
                    subscription_level=SubscriptionLevel.TEAM,  # Predetermined for organization members
                    is_admin=False  # Regular team member, not admin
                )

                # Track user registration event
                analytics_service.track_user_event(
                    user_id=str(user_id),
                    event_name='User Registered',
                    properties={
                        'email': email,
                        'first_name': first_name,
                        'tenant_type': TenantType.COMPANY.value,  # Company type for organization members
                        'subscription_level': SubscriptionLevel.TEAM.value # Team level for organization members
                    }
                )

                # Mark invite as used
                db_manager.use_organization_invite_token(organization_invite['token_hash'])

                # Clear invite from session
                session.pop('organization_invite', None)

                # Generate and send verification email
                verification_token = generate_verification_token()
                token_hash = hash_token(verification_token)

                if db_manager.create_verification_token(user_id, token_hash):
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
                if expects_json:
                    return jsonify({'error': 'Organization name is required for company accounts.', 'retry': True}), 400
                flash('Organization name is required for company accounts.', 'error')
                return render_template('register.html', 
                                     is_organization_invite=is_organization_invite,
                                     organization_invite=organization_invite)

            # Check if user already exists  
            existing_user = db_manager.get_user_by_email(email)
            if existing_user:
                if expects_json:
                    return jsonify({'error': 'An account with this email already exists.', 'retry': True}), 400
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
            user_id = db_manager.create_user(
                tenant_id=tenant.tenant_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
                subscription_level=SubscriptionLevel(subscription_level),
                is_admin=is_admin
            )

            # Track user registration event
            analytics_service.track_user_event(
                user_id=str(user_id),
                event_name='User Registered',
                properties={
                    'email': email,
                    'first_name': first_name,
                    'tenant_type': user_type,
                    'subscription_level': subscription_level
                }
            )

            # Track user registration and source (non-critical)
            try:
                user_source_tracker.track_user_signup(
                    user_email=email,
                    signup_source='free_registration',
                    invite_code=invitation_code if invitation_data else None
                )
                logger.info(f"Tracked signup source for {email}")
            except Exception as tracking_error:
                logger.warning(f"Failed to track signup source for {email}: {tracking_error}")

            # Check if this is a paid plan - redirect to checkout immediately
            if subscription_level in ['solo', 'team', 'professional']:
                try:
                    # Create or get Stripe customer
                    customer = stripe_service.create_customer(
                        email=email,
                        name=f"{first_name} {last_name}",
                        metadata={'user_id': user_id}
                    )

                    if customer:
                        db_manager.update_user_stripe_info(user_id, stripe_customer_id=customer['id'])

                    # Map subscription level to Stripe price ID
                    price_mapping = {
                        'solo': 'price_1RvL44Hynku0jyEH12IrEJuI',
                        'team': 'price_1RvL4sHynku0jyEH4go1pRLM',
                        'professional': 'price_1RvL79Hynku0jyEHm7b89IPr'
                    }

                    price_id = price_mapping.get(subscription_level)
                    if not price_id:
                        # Clean up user and tenant
                        try:
                            db_manager.delete_user(user_id)
                            db_manager.delete_tenant(tenant.tenant_id)
                        except:
                            pass
                        return jsonify({
                            'error': 'Invalid subscription plan selected.',
                            'retry': True
                        }), 400

                    # Create checkout session with improved URLs for Replit
                    base_url = request.url_root.rstrip('/')

                    # Ensure we're using the correct host for Replit
                    if 'replit.dev' in base_url and not base_url.startswith('https://'):
                        base_url = base_url.replace('http://', 'https://')

                    success_url = f"{base_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&new_user={user_id}"
                    cancel_url = f"{base_url}/register?payment_cancelled=true"

                    logger.info(f"Using base URL: {base_url}")
                    logger.info(f"Full success URL: {success_url}")
                    logger.info(f"Full cancel URL: {cancel_url}")

                    logger.info(f"Creating Stripe checkout session for user {user_id}")
                    logger.info(f"Price ID: {price_id}")
                    logger.info(f"Customer ID: {customer['id'] if customer else 'None'}")

                    logger.info(f"About to create Stripe checkout session:")
                    logger.info(f"  - Email: {email}")
                    logger.info(f"  - Price ID: {price_id}")
                    logger.info(f"  - Success URL: {success_url}")
                    logger.info(f"  - Cancel URL: {cancel_url}")

                    # For now, set trial to 0 days for testing Stripe integration
                    # TODO: Change to 7 days once Stripe integration is confirmed working
                    trial_days = '0'  # Set to '0' for testing, '7' for production trial

                    stripe_session = stripe_service.create_checkout_session(
                        customer_email=email,
                        price_id=price_id,
                        success_url=success_url,
                        cancel_url=cancel_url,
                        customer_id=customer['id'] if customer else None,
                        metadata={
                            'user_id': user_id,
                            'plan_id': subscription_level,
                            'new_registration': 'true',
                            'trial_days': trial_days
                        }
                    )

                    logger.info(f"Stripe session creation result: {stripe_session}")

                    # Additional validation
                    if stripe_session:
                        if not stripe_session.get('url'):
                            logger.error("❌ Stripe session created but URL is missing")
                        elif not stripe_session.get('url').startswith('https://'):
                            logger.error(f"❌ Invalid checkout URL format: {stripe_session.get('url')}")
                        else:
                            logger.info("✓ Stripe session validation passed")

                    if stripe_session and stripe_session.get('url'):
                        # Store pending registration in session for post-payment verification
                        session['pending_registration'] = {
                            'user_id': user_id,
                            'email': email,
                            'first_name': first_name,
                            'needs_verification': True
                        }

                        logger.info(f"✓ Stripe checkout session created: {stripe_session['id']}")
                        logger.info(f"✓ Checkout URL: {stripe_session['url']}")

                        # Return clean JSON response
                        return jsonify({
                            'success': True,
                            'redirect_to_stripe': True,
                            'checkout_url': stripe_session['url'],
                            'session_id': stripe_session['id']
                        })
                    else:
                        logger.error("❌ Stripe session created but no URL returned")
                        # Delete the user since payment setup failed
                        try:
                            db_manager.delete_user(user_id)
                            db_manager.delete_tenant(tenant.tenant_id)
                        except:
                            pass
                        return jsonify({
                            'error': 'Payment session creation failed. Please try again.',
                            'retry': True
                        }), 400

                except Exception as stripe_error:
                    logger.error(f"❌ Stripe error: {stripe_error}")
                    # Clean up user and tenant on failure
                    try:
                        db_manager.delete_user(user_id)
                        db_manager.delete_tenant(tenant.tenant_id)
                    except:
                        pass
                    return jsonify({
                        'error': f'Payment processing error: {str(stripe_error)}',
                        'retry': True
                    }), 400

            # Mark invitation as accepted if this was from an invitation
            if invitation_data:
                try:
                    from invitation_manager import invitation_manager
                    invitation_manager.mark_accepted(invitation_code)
                    logger.info(f"Marked invitation {invitation_code} as accepted")
                except Exception as inv_error:
                    logger.warning(f"Failed to mark invitation as accepted: {inv_error}")

            # For free plans or fallback, send verification email
            verification_token = generate_verification_token()
            token_hash = hash_token(verification_token)

            if db_manager.create_verification_token(user_id, token_hash):
                if email_service.send_verification_email(email, verification_token, first_name):
                    if invitation_data:
                        flash(f'Welcome! Your account has been created successfully. Please check your email to verify your account before signing in.', 'success')
                    else:
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
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            # Always return JSON for AJAX requests
            if expects_json:
                return jsonify({
                    'error': 'An error occurred during registration. Please try again.',
                    'retry': True
                }), 500
            else:
                flash('An error occurred during registration. Please try again.', 'error')

    return render_template('register.html', 
                         is_organization_invite=is_organization_invite,
                         organization_invite=organization_invite,
                         invitation_data=invitation_data,
                         invitation_code=invitation_code)

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

            # Track user login event
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='User Login',
                properties={
                    'email': user.email,
                    'subscription_level': user.subscription_level
                }
            )

            login_user(user)
            flash('Welcome back!', 'success')
            next_page = request.args.get('next')
            if next_page:
                # Validate redirect URL to prevent open redirect attacks
                parsed_url = urlparse(next_page)
                if parsed_url.netloc and parsed_url.netloc != request.host:
                    # External redirect detected, ignore and use default
                    return redirect(url_for('chat'))
            return redirect(next_page) if next_page else redirect(url_for('chat'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    user = get_current_user() # Get user before logging out
    logout_user()
    if user:
        # Track user logout event
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='User Logout',
            properties={
                'email': user.email
            }
        )
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
        # Track email verification event
        user = db_manager.get_user_by_id(user_id) # Fetch user to get details
        if user:
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Email Verified',
                properties={
                    'email': user.email
                }
            )
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
                # Track resend verification email event
                analytics_service.track_user_event(
                    user_id=str(user.user_id),
                    event_name='Verification Email Resent',
                    properties={
                        'email': user.email
                    }
                )
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
                    # Track password reset request event
                    analytics_service.track_user_event(
                        user_id=str(user.user_id),
                        event_name='Password Reset Requested',
                        properties={
                            'email': user.email
                        }
                    )
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

            # Track password reset success
            user = db_manager.get_user_by_id(user_id)
            if user:
                analytics_service.track_user_event(
                    user_id=str(user.user_id),
                    event_name='Password Reset Success',
                    properties={
                        'email': user.email
                    }
                )

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

        # Track user visit to chat page
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Visited Chat Page',
            properties={
                'subscription_level': user.subscription_level.value
            }
        )

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
        logger.info("=== /generate route called ===")
        data = request.get_json()
        logger.info(f"Request data received: {bool(data)}")

        prompt = data.get('prompt', '').strip()
        conversation_history = data.get('conversation_history', [])
        content_mode = data.get('content_mode')
        brand_voice_id = data.get('brand_voice_id')
        is_demo = data.get('is_demo', False)
        session_id = data.get('session_id') # Added for tracking

        logger.info(f"Prompt length: {len(prompt)}")
        logger.info(f"Content mode: {content_mode}")
        logger.info(f"Brand voice ID: {brand_voice_id}")
        logger.info(f"Is demo: {is_demo}")
        logger.info(f"Conversation history length: {len(conversation_history)}")

        if not prompt:
            logger.warning("No prompt provided")
            return jsonify({'error': 'Prompt is required'}), 400

        user = get_current_user()
        logger.info(f"Current user: {user.user_id if user else 'None'}")

        if not user and not is_demo:
            logger.warning("No user and not demo mode")
            return jsonify({'error': 'Authentication required'}), 401

        # Demo mode - limited functionality
        if is_demo or not user:
            # Get trauma-informed context only
            trauma_informed_context = rag_service.get_trauma_informed_context()

            # Generate content without brand voice but with conversation history
            response = gemini_service.generate_content_with_history(
                prompt=prompt,
                conversation_history=conversation_history,
                content_mode=content_mode,
                brand_voice_context=None,
                trauma_informed_context=trauma_informed_context
            )

            # Track demo generation event
            analytics_service.track_user_event(
                user_id='anonymous_demo_user', # Use a placeholder for anonymous users
                event_name='Chat Message Generated (Demo)',
                properties={
                    'content_mode': content_mode,
                    'prompt_length': len(prompt),
                    'response_length': len(response)
                }
            )

            return jsonify({'response': response})

        # Logged-in user - enforce plan limits
        # Estimate tokens needed (rough estimate: 1 token ≈ 4 characters)
        estimated_tokens = max(len(prompt) // 4, 100)  # Minimum 100 tokens
        # Add history tokens to estimate
        for msg in conversation_history:
            estimated_tokens += len(msg.get('content', '')) // 4

        # Check user limits before proceeding
        limits_check = db_manager.check_user_limits(user.user_id, content_mode, estimated_tokens)
        if not limits_check['allowed']:
            return jsonify({'error': limits_check['error']}), 403

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

        # Generate content with conversation history
        logger.info(f"=== CALLING GEMINI SERVICE ===")
        logger.info(f"About to call gemini_service.generate_content_with_history")
        logger.info(f"Prompt: {prompt[:100]}...")
        logger.info(f"Content mode: {content_mode}")
        logger.info(f"Brand voice context length: {len(brand_voice_context) if brand_voice_context else 0}")
        logger.info(f"Trauma informed context length: {len(trauma_informed_context) if trauma_informed_context else 0}")

        try:
            response = gemini_service.generate_content_with_history(
                prompt=prompt,
                conversation_history=conversation_history,
                content_mode=content_mode,
                brand_voice_context=brand_voice_context,
                trauma_informed_context=trauma_informed_context
            )

            logger.info(f"✓ Gemini service returned response of length: {len(response) if response else 0}")
            logger.info(f"Response preview: {response[:100] if response else 'No response'}")
        except Exception as gemini_error:
            logger.error(f"❌ Error in Gemini service call: {gemini_error}")
            raise

        # Update token usage (rough calculation: input + output tokens)
        response_tokens = len(response) // 4  # Rough estimate
        total_tokens_used = estimated_tokens + response_tokens
        db_manager.update_user_token_usage(user.user_id, total_tokens_used)

        # Save to chat history if user is logged in
        if session_id: # Use session_id from request data
            # Verify session belongs to user before saving
            user_sessions = db_manager.get_user_chat_sessions(user.user_id)
            session_belongs_to_user = any(s['session_id'] == session_id for s in user_sessions)

            if not session_belongs_to_user:
                logger.warning(f"Session {session_id} does not belong to user {user.user_id}")
                return jsonify({'error': 'Invalid session'}), 400

            logger.info(f"Saving message to session {session_id} for user {user.user_id}")

            # Check chat history limits first
            user_plan = db_manager.get_user_plan(user.user_id)
            if user_plan and user_plan['chat_history_limit'] != -1:  # -1 means unlimited
                if len(user_sessions) >= user_plan['chat_history_limit']:
                    # Don't save to history if limit reached
                    pass
                else:
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
            else:
                # Unlimited history - save normally
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

        # Track chat generation event
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Chat Message Generated',
            properties={
                'content_mode': content_mode,
                'has_brand_voice': bool(brand_voice_id),
                'prompt_length': len(prompt),
                'response_length': len(response),
                'session_id': str(session_id)
            }
        )

        logger.info(f"=== ROUTE COMPLETING SUCCESSFULLY ===")
        return jsonify({'response': response})

    except Exception as e:
        logger.error(f"❌ Generation error: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'An error occurred while generating content. Please try again.'}), 500

@app.route('/how-to')
def how_to():
    """How to use GoldenDoodleLM guide page"""
    return render_template('how_to.html')

@app.route('/our-story')
def our_story():
    """Our story page - tells the story of GoldenDoodleLM"""
    return render_template('our_story.html')

@app.route('/pricing')
def pricing():
    """Pricing page with four-tier pricing model"""
    return render_template('pricing.html')

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

    # Track user visit to account page
    analytics_service.track_user_event(
        user_id=str(user.user_id),
        event_name='Visited Account Page',
        properties={
            'subscription_level': user.subscription_level
        }
    )

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

        # Track profile update event
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Profile Updated',
            properties={
                'email': email,
                'first_name': first_name,
                'last_name': last_name
            }
        )

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

        # Track password change event
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Password Changed',
            properties={
                'email': user.email
            }
        )

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
            # Track account deletion event
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Account Deleted',
                properties={
                    'email': user.email,
                    'delete_reason': delete_reason
                }
            )
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

    # Track user visit to brand voices page
    analytics_service.track_user_event(
        user_id=str(user.user_id),
        event_name='Visited Brand Voices Page',
        properties={
            'subscription_level': user.subscription_level,
            'is_admin': user.is_admin,
            'tenant_type': tenant.tenant_type
        }
    )

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

    # Track user visit to brand voice wizard
    analytics_service.track_user_event(
        user_id=str(user.user_id),
        event_name='Visited Brand Voice Wizard',
        properties={
            'voice_type': voice_type,
            'editing': bool(edit_id)
        }
    )

    return render_template('brand_voice_wizard.html', 
                         voice_type=voice_type, 
                         user=user, 
                         edit_id=edit_id)

@app.route('/create-brand-voice', methods=['POST'])
@login_required
def create_brand_voice():
    """Create a new brand voice or update an existing one"""
    try:
        logger.info("=== BRAND VOICE CREATION REQUEST RECEIVED ===")

        data = request.get_json()

        if not data:
            logger.error("No JSON data received in brand voice creation request")
            return jsonify({'error': 'No data received'}), 400

        # Required fields
        company_name = data.get('company_name', '').strip()
        company_url = data.get('company_url', '').strip()
        voice_short_name = data.get('voice_short_name', '').strip()
        voice_type = data.get('voice_type', 'user') # Although we always create as company, this might be used for context
        brand_voice_id = data.get('brand_voice_id')  # For editing existing voices

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
        user_id_for_db = None 

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
                user_id=user_id_for_db
            )
            logger.info(f"Updated brand voice: {brand_voice.brand_voice_id}")

            return_message = f'Brand voice "{voice_short_name}" updated successfully!'

        else:
            brand_voice = db_manager.create_comprehensive_brand_voice(
                tenant_id=tenant.tenant_id,
                wizard_data=wizard_data,
                markdown_content=markdown_content,
                user_id=user_id_for_db
            )
            logger.info(f"✓ Successfully created brand voice: {brand_voice.brand_voice_id}")

            # Debugging: Fetch all company voices again to see if the new one is present
            current_company_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
            logger.info(f"Company voices AFTER creation: {len(current_company_voices)}/{tenant.max_brand_voices}")
            for voice in current_company_voices:
                logger.info(f"  Voice: '{voice.name}' (ID: {voice.brand_voice_id})")

            return_message = f'Brand voice "{voice_short_name}" created successfully!'

        # Track brand voice creation/update event
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Brand Voice Created' if not is_editing else 'Brand Voice Updated',
            properties={
                'brand_voice_name': voice_short_name,
                'brand_voice_id': str(brand_voice.brand_voice_id),
                'is_company_voice': True, # Always company voice now
                'is_editing': is_editing
            }
        )

        return jsonify({
            'success': True,
            'brand_voice_id': brand_voice.brand_voice_id,
            'message': return_message
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

@app.route('/delete-brand-voice/<brand_voice_id>', methods=['POST'])
@login_required
def delete_brand_voice(brand_voice_id):
    """Delete a brand voice"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if not tenant:
            return jsonify({'error': 'Invalid tenant'}), 400

        # Get brand voice from database to check permissions
        company_brand_voices = []
        if tenant.tenant_type == TenantType.COMPANY:
            company_brand_voices = db_manager.get_company_brand_voices(tenant.tenant_id)

        user_brand_voices = db_manager.get_user_brand_voices(tenant.tenant_id, user.user_id)
        all_brand_voices = company_brand_voices + user_brand_voices

        selected_brand_voice = next((bv for bv in all_brand_voices if bv.brand_voice_id == brand_voice_id), None)

        if not selected_brand_voice:
            return jsonify({'error': 'Brand voice not found'}), 404

        # Check permissions
        if selected_brand_voice.user_id and selected_brand_voice.user_id != user.user_id:
            return jsonify({'error': 'Permission denied'}), 403

        if not selected_brand_voice.user_id and not user.is_admin:
            return jsonify({'error': 'Permission denied'}), 403

        # Delete the brand voice
        if db_manager.delete_brand_voice(tenant.tenant_id, brand_voice_id, selected_brand_voice.user_id):
            # Track brand voice deletion event
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Brand Voice Deleted',
                properties={
                    'brand_voice_id': str(brand_voice_id),
                    'brand_voice_name': selected_brand_voice.name,
                    'is_company_voice': selected_brand_voice.user_id is None
                }
            )
            logger.info(f"Successfully deleted brand voice {brand_voice_id} for user {user.user_id}")
            return jsonify({'success': True, 'message': 'Brand voice deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete brand voice'}), 500

    except Exception as e:
        logger.error(f"Error deleting brand voice {brand_voice_id}: {e}")
        return jsonify({'error': 'An error occurred while deleting the brand voice'}), 500

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

        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if not tenant:
            return jsonify({'error': 'Invalid tenant'}), 400

        # Generate comprehensive markdown content for RAG
        markdown_content = generate_brand_voice_markdown(data)

        # Get or create profile_id
        profile_id = data.get('profile_id')
        is_editing = bool(profile_id)

        if profile_id:
            # Update existing draft
            try:
                brand_voice = db_manager.update_brand_voice(
                    tenant_id=tenant.tenant_id,
                    brand_voice_id=profile_id,
                    wizard_data=data,
                    markdown_content=markdown_content,
                    user_id=None  # Always create as company voice
                )
                logger.info(f"Updated draft brand voice: {brand_voice.brand_voice_id}")
            except Exception as update_error:
                logger.warning(f"Failed to update existing draft, creating new one: {update_error}")
                # If update fails, create a new one
                brand_voice = db_manager.create_comprehensive_brand_voice(
                    tenant_id=tenant.tenant_id,
                    wizard_data=data,
                    markdown_content=markdown_content,
                    user_id=None
                )
                profile_id = brand_voice.brand_voice_id
        else:
            # Check if a brand voice with this name already exists to avoid duplicates
            existing_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
            existing_voice = next((v for v in existing_voices if v.name == voice_short_name), None)

            if existing_voice:
                # Update the existing voice instead of creating a duplicate
                try:
                    brand_voice = db_manager.update_brand_voice(
                        tenant_id=tenant.tenant_id,
                        brand_voice_id=existing_voice.brand_voice_id,
                        wizard_data=data,
                        markdown_content=markdown_content,
                        user_id=None
                    )
                    profile_id = brand_voice.brand_voice_id
                    logger.info(f"Updated existing brand voice instead of creating duplicate: {brand_voice.brand_voice_id}")
                except Exception as update_error:
                    logger.warning(f"Failed to update existing voice, creating new one: {update_error}")
                    # If update fails, create a new one
                    brand_voice = db_manager.create_comprehensive_brand_voice(
                        tenant_id=tenant.tenant_id,
                        wizard_data=data,
                        markdown_content=markdown_content,
                        user_id=None
                    )
                    profile_id = brand_voice.brand_voice_id
            else:
                # Create new draft
                brand_voice = db_manager.create_comprehensive_brand_voice(
                    tenant_id=tenant.tenant_id,
                    wizard_data=data,
                    markdown_content=markdown_content,
                    user_id=None
                )
                profile_id = brand_voice.brand_voice_id

        # Track auto-save event
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Brand Voice Auto-Saved',
            properties={
                'brand_voice_name': voice_short_name,
                'profile_id': profile_id,
                'is_editing': is_editing
            }
        )

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

    # Track admin access
    analytics_service.track_user_event(
        user_id='platform_admin', # Placeholder for admin user
        event_name='Visited Platform Admin Dashboard'
    )

    return render_template('platform_admin.html', users=users, tenants=tenants)

@app.route('/admin/delete-user/<user_id>', methods=['POST'])
@super_admin_required
def admin_delete_user(user_id):
    """Delete a user account"""
    try:
        logger.info(f"Admin deleting user with ID: {user_id}")
        # Get user details before deletion for tracking
        user_to_delete = db_manager.get_user_by_id(user_id)
        email = user_to_delete.email if user_to_delete else 'unknown'

        if db_manager.delete_user(user_id):
            # Track user deletion by admin
            analytics_service.track_user_event(
                user_id='platform_admin',
                event_name='User Deleted by Admin',
                properties={
                    'deleted_user_id': user_id,
                    'deleted_user_email': email
                }
            )
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
        # Get tenant details before deletion for tracking
        tenant_to_delete = db_manager.get_tenant_by_id(tenant_id)
        tenant_name = tenant_to_delete.name if tenant_to_delete else 'unknown'

        if db_manager.delete_tenant(tenant_id):
            # Track tenant deletion by admin
            analytics_service.track_user_event(
                user_id='platform_admin',
                event_name='Tenant Deleted by Admin',
                properties={
                    'deleted_tenant_id': tenant_id,
                    'deleted_tenant_name': tenant_name
                }
            )
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

        # Track admin viewing organization details
        analytics_service.track_user_event(
            user_id='platform_admin',
            event_name='Viewed Organization Details',
            properties={
                'organization_id': tenant_id,
                'organization_name': tenant.name
            }
        )

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
        user_before_update = db_manager.get_user_by_id(user_id) # Get user before update for tracking

        if db_manager.update_user_subscription(user_id, subscription_level):
            # Track subscription update by admin
            analytics_service.track_user_event(
                user_id='platform_admin',
                event_name='User Subscription Updated by Admin',
                properties={
                    'user_id': user_id,
                    'previous_subscription': user_before_update.subscription_level if user_before_update else 'unknown',
                    'new_subscription': subscription_level
                }
            )
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
                # Track organization invite sent
                analytics_service.track_user_event(
                    user_id=str(user.user_id),
                    event_name='Organization Invite Sent',
                    properties={
                        'organization_id': tenant.tenant_id,
                        'invited_email': email
                    }
                )
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

    # Track organization invite accepted
    analytics_service.track_user_event(
        user_id=f'invited_user_{email}', # Use email as identifier for unregisted user
        event_name='Organization Invite Accepted',
        properties={
            'organization_id': tenant_id,
            'organization_name': tenant.name,
            'invited_email': email
        }
    )

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

        # Track viewing pending invites
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Viewed Pending Organization Invites',
            properties={
                'organization_id': tenant_id,
                'invite_count': len(invites)
            }
        )

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

        # Track viewing active users
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Viewed Organization Users',
            properties={
                'organization_id': tenant_id,
                'user_count': len(users_data)
            }
        )

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

        # Track fetching chat sessions
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Fetched Chat Sessions',
            properties={
                'session_count': len(sessions)
            }
        )

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
            logger.info(f"Created new chat session {session_id} for user {user.user_id}")
            # Track new chat session creation
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Created New Chat Session',
                properties={
                    'session_id': str(session_id),
                    'session_title': title
                }
            )
            return jsonify({'session_id': session_id, 'title': title})
        else:
            logger.error(f"Failed to create chat session for user {user.user_id}")
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

        # Track fetching chat messages
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Fetched Chat Messages',
            properties={
                'session_id': str(session_id),
                'message_count': len(messages)
            }
        )

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
            # Track chat session deletion
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Deleted Chat Session',
                properties={
                    'session_id': str(session_id)
                }
            )
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
            logger.info(f"Created new chat session {session_id} for user {user.user_id}")
            # Track new session creation via this endpoint
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Created New Chat Session',
                properties={
                    'session_id': str(session_id),
                    'session_title': 'New Chat'
                }
            )
            return jsonify({'session_id': session_id, 'success': True})
        else:
            logger.error(f"Failed to create chat session for user {user.user_id}")
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

        # Track fetching chat history
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Fetched Chat History',
            properties={
                'session_count': len(sessions)
            }
        )

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

        # Track fetching specific chat
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Fetched Specific Chat',
            properties={
                'session_id': str(session_id),
                'session_title': session_title,
                'message_count': len(messages)
            }
        )

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

@app.route('/api/get-plans', methods=['GET'])
def get_plans():
    """Get all pricing plans"""
    try:
        logger.info("Getting pricing plans...")
        plans = db_manager.get_all_pricing_plans()
        logger.info(f"Retrieved {len(plans)} pricing plans")

        if not plans:
            logger.warning("No pricing plans found, attempting to populate...")
            db_manager.populate_pricing_plans()
            plans = db_manager.get_all_pricing_plans()
            logger.info(f"After population: {len(plans)} pricing plans")

        # Track fetching plans
        analytics_service.track_user_event(
            user_id='anonymous_user' if not get_current_user() else str(get_current_user().user_id),
            event_name='Fetched Pricing Plans',
            properties={
                'plan_count': len(plans)
            }
        )

        return jsonify(plans)
    except Exception as e:
        logger.error(f"Error getting pricing plans: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'An error occurred while loading pricing plans'}), 500

@app.route('/api/user-plan', methods=['GET'])
@login_required
def get_user_plan():
    """Get current user's plan and usage"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        plan = db_manager.get_user_plan(user.user_id)
        usage = db_manager.get_user_token_usage(user.user_id)

        # Track fetching user plan
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Fetched User Plan',
            properties={
                'plan_name': plan.get('plan_name') if plan else None,
                'monthly_tokens': usage.get('tokens_used_month') if usage else None
            }
        )

        return jsonify({
            'plan': plan,
            'usage': usage
        })
    except Exception as e:
        logger.error(f"Error getting user plan: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 Not Found: {error}")
    # Track 404 errors
    user_id = get_current_user().user_id if get_current_user() else 'anonymous_user'
    analytics_service.track_user_event(
        user_id=str(user_id),
        event_name='Page Not Found (404)',
        properties={
            'path': request.path,
            'error_message': str(error)
        }
    )
    return render_template('404.html'), 404

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create Stripe checkout session"""
    try:
        data = request.get_json()
        plan_id = data.get('plan_id')

        if not plan_id or plan_id == 'free':
            return jsonify({'error': 'Invalid plan selected'}), 400

        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        # Map plan_id to Stripe price_id 
        price_mapping = {
            'solo': 'price_1RvL44Hynku0jyEH12IrEJuI',    # The Practitioner
            'team': 'price_1RvL4sHynku0jyEH4go1pRLM',     # The Organization
            'professional': 'price_1RvL79Hynku0jyEHm7b89IPr' # The Powerhouse
        }

        price_id = price_mapping.get(plan_id)
        if not price_id:
            return jsonify({'error': 'Plan not available'}), 400

        # Create or get Stripe customer
        stripe_customer_id = user.stripe_customer_id if hasattr(user, 'stripe_customer_id') else None

        if not stripe_customer_id:
            customer = stripe_service.create_customer(
                email=user.email,
                name=f"{user.first_name} {user.last_name}",
                metadata={'user_id': user.user_id}
            )
            if customer:
                stripe_customer_id = customer['id']
                db_manager.update_user_stripe_info(user.user_id, stripe_customer_id=stripe_customer_id)

        # Create checkout session
        base_url = request.url_root.rstrip('/')
        success_url = f"{base_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{base_url}/pricing"

        session = stripe_service.create_checkout_session(
            customer_email=user.email,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            customer_id=stripe_customer_id,
            metadata={
                'user_id': user.user_id,
                'plan_id': plan_id
            }
        )

        if session:
            # Track checkout session creation
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Created Checkout Session',
                properties={
                    'plan_id': plan_id,
                    'price_id': price_id,
                    'session_id': session.get('id')
                }
            )
            return jsonify({'checkout_url': session['url']})
        else:
            return jsonify({'error': 'Failed to create checkout session'}), 500

    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/payment-success')
def payment_success():
    """Handle successful payment"""
    session_id = request.args.get('session_id')
    new_user_id = request.args.get('new_user')

    if not session_id:
        flash('Invalid payment session.', 'error')
        return redirect(url_for('pricing'))

    # Handle new user registration flow
    if new_user_id and 'pending_registration' in session:
        pending_reg = session.get('pending_registration')
        if pending_reg and pending_reg['user_id'] == new_user_id:
            # Payment successful for new user - verify email and log them in
            verification_token = generate_verification_token()
            token_hash = hash_token(verification_token)

            # Mark email as verified since they completed payment
            db_manager.mark_email_verified(new_user_id)

            # Get the user and log them in
            user = db_manager.get_user_by_id(new_user_id)
            if user:
                login_user(user)
                session.pop('pending_registration', None)

                # Track successful new user registration via payment
                analytics_service.track_user_event(
                    user_id=str(user.user_id),
                    event_name='User Registered (Paid)',
                    properties={
                        'email': user.email,
                        'subscription_level': user.subscription_level
                    }
                )

                # Track user signup source for paid registration (non-critical)
                try:
                    user_source_tracker.track_user_signup(
                        user_email=user.email,
                        signup_source=f'paid_{user.subscription_level.value}',
                        invite_code=None
                    )
                    logger.info(f"Tracked paid signup for {user.email}")
                except Exception as tracking_error:
                    logger.warning(f"Failed to track paid signup for {user.email}: {tracking_error}")

                flash('Welcome to GoldenDoodleLM! Your subscription is active.', 'success')
                return redirect(url_for('chat'))
            else:
                flash('Account setup completed. Please sign in with your credentials.', 'info')
                return redirect(url_for('login'))

    # Regular logged-in user payment success
    user = get_current_user()
    if user:
        # Track successful payment for existing user
        analytics_service.track_user_event(
            user_id=str(user.user_id),
            event_name='Payment Successful',
            properties={
                'subscription_level': user.subscription_level,
                'session_id': session_id
            }
        )
        flash('Payment successful! Your subscription is being activated.', 'success')
        return redirect(url_for('account'))

    # Fallback
    flash('Payment completed. Please sign in to access your account.', 'success')
    return redirect(url_for('login')) # Redirect to login for unauthenticated users after payment

@app.route('/analytics')
@super_admin_required
def analytics_dashboard():
    """Analytics dashboard for user tracking"""
    # Track admin access to analytics dashboard
    analytics_service.track_user_event(
        user_id='platform_admin',
        event_name='Visited Analytics Dashboard'
    )
    return render_template('analytics_dashboard.html')

@app.route('/analytics/users', methods=['GET'])
@super_admin_required
def analytics_users():
    """Get user analytics data"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # User registration trends
        cursor.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as new_users,
                subscription_level,
                tenant_type
            FROM users u
            JOIN tenants t ON u.tenant_id = t.tenant_id
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at), subscription_level, tenant_type
            ORDER BY date DESC
        """)
        registration_trends = cursor.fetchall()

        # Active users (based on last_login)
        cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE last_login >= NOW() - INTERVAL '1 day') as daily_active,
                COUNT(*) FILTER (WHERE last_login >= NOW() - INTERVAL '7 days') as weekly_active,
                COUNT(*) FILTER (WHERE last_login >= NOW() - INTERVAL '30 days') as monthly_active,
                COUNT(*) as total_users
            FROM users
        """)
        active_users = cursor.fetchone()

        # Subscription distribution
        cursor.execute("""
            SELECT subscription_level, COUNT(*) as count
            FROM users
            GROUP BY subscription_level
        """)
        subscription_dist = cursor.fetchall()

        # Token usage patterns
        cursor.execute("""
            SELECT 
                AVG(tokens_used_month) as avg_monthly_tokens,
                MAX(tokens_used_month) as max_monthly_tokens,
                COUNT(*) FILTER (WHERE tokens_used_month > 0) as active_token_users
            FROM user_token_usage
        """)
        token_usage = cursor.fetchone()

        cursor.close()
        conn.close()

        # Track viewing user analytics
        analytics_service.track_user_event(
            user_id='platform_admin',
            event_name='Viewed User Analytics'
        )

        return jsonify({
            'registration_trends': [dict(row) for row in registration_trends],
            'active_users': dict(active_users),
            'subscription_distribution': [dict(row) for row in subscription_dist],
            'token_usage': dict(token_usage) if token_usage else {}
        })

    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return jsonify({'error': 'Failed to get analytics'}), 500

@app.route('/analytics/usage', methods=['GET'])
@super_admin_required
def analytics_usage():
    """Get detailed usage analytics"""
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Chat session statistics
        cursor.execute("""
            SELECT 
                DATE(cs.created_at) as date,
                COUNT(DISTINCT cs.session_id) as sessions_created,
                COUNT(DISTINCT cs.user_id) as unique_users,
                AVG(message_counts.msg_count) as avg_messages_per_session
            FROM chat_sessions cs
            LEFT JOIN (
                SELECT session_id, COUNT(*) as msg_count
                FROM chat_messages
                GROUP BY session_id
            ) message_counts ON cs.session_id = message_counts.session_id
            WHERE cs.created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(cs.created_at)
            ORDER BY date DESC
        """)
        chat_stats = cursor.fetchall()

        # Brand voice usage
        cursor.execute("""
            SELECT 
                COUNT(*) as total_brand_voices,
                COUNT(DISTINCT tenant_id) as tenants_with_voices
            FROM brand_voices
        """)
        brand_voice_stats = cursor.fetchone()

        cursor.close()
        conn.close()

        # Track viewing usage analytics
        analytics_service.track_user_event(
            user_id='platform_admin',
            event_name='Viewed Usage Analytics'
        )

        return jsonify({
            'chat_statistics': [dict(row) for row in chat_stats],
            'brand_voice_stats': dict(brand_voice_stats) if brand_voice_stats else {}
        })

    except Exception as e:
        logger.error(f"Error getting usage analytics: {e}")
        return jsonify({'error': 'Failed to get usage analytics'}), 500

    return redirect(url_for('login'))

@app.route('/billing-portal', methods=['POST'])
@login_required
def create_billing_portal():
    """Create Stripe billing portal session"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401

        stripe_customer_id = getattr(user, 'stripe_customer_id', None)
        if not stripe_customer_id:
            return jsonify({'error': 'No billing account found'}), 400

        return_url = f"{request.url_root}account"
        portal_url = stripe_service.create_billing_portal_session(
            customer_id=stripe_customer_id,
            return_url=return_url
        )

        if portal_url:
            # Track access to billing portal
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Accessed Billing Portal'
            )
            return jsonify({'url': portal_url})
        else:
            return jsonify({'error': 'Failed to create billing portal'}), 500

    except Exception as e:
        logger.error(f"Error creating billing portal: {e}")
        return jsonify({'error': 'An error occurred'}), 500

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    try:
        payload = request.data
        signature = request.headers.get('Stripe-Signature')

        event = stripe_service.verify_webhook_signature(payload, signature)
        if not event:
            return jsonify({'error': 'Invalid signature'}), 400

        logger.info(f"Received Stripe webhook: {event['type']}")

        # Handle different event types
        if event['type'] == 'customer.subscription.created':
            handle_subscription_created(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            handle_payment_failed(event['data']['object'])

        return jsonify({'status': 'success'})

    except Exception as e:
        logger.error(f"Error handling Stripe webhook: {e}")
        return jsonify({'error': 'Webhook handler error'}), 500

def handle_subscription_created(subscription):
    """Handle subscription created event"""
    try:
        customer_id = subscription['customer']
        subscription_id = subscription['id']
        status = subscription['status']
        current_period_end = datetime.fromtimestamp(subscription['current_period_end'])

        user = db_manager.get_user_by_stripe_customer_id(customer_id)
        if user:
            db_manager.update_user_stripe_info(
                user.user_id,
                stripe_subscription_id=subscription_id,
                subscription_status=status,
                current_period_end=current_period_end
            )
            # Track subscription creation via webhook
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Subscription Created (via Webhook)',
                properties={
                    'subscription_id': subscription_id,
                    'status': status,
                    'plan_id': subscription.get('plan', {}).get('id') # Extract plan ID if available
                }
            )
            logger.info(f"Updated subscription for user {user.user_id}: {subscription_id}")

    except Exception as e:
        logger.error(f"Error handling subscription created: {e}")

def handle_subscription_updated(subscription):
    """Handle subscription updated event"""
    try:
        customer_id = subscription['customer']
        subscription_id = subscription['id']
        status = subscription['status']
        current_period_end = datetime.fromtimestamp(subscription['current_period_end'])

        user = db_manager.get_user_by_stripe_customer_id(customer_id)
        if user:
            db_manager.update_user_stripe_info(
                user.user_id,
                subscription_status=status,
                current_period_end=current_period_end
            )
            # Track subscription update via webhook
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Subscription Updated (via Webhook)',
                properties={
                    'subscription_id': subscription_id,
                    'status': status
                }
            )
            logger.info(f"Updated subscription status for user {user.user_id}: {status}")

    except Exception as e:
        logger.error(f"Error handling subscription updated: {e}")

def handle_subscription_deleted(subscription):
    """Handle subscription cancelled/deleted event"""
    try:
        customer_id = subscription['customer']

        user = db_manager.get_user_by_stripe_customer_id(customer_id)
        if user:
            db_manager.update_user_stripe_info(
                user.user_id,
                subscription_status='cancelled',
                stripe_subscription_id=None
            )
            # Track subscription deletion via webhook
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Subscription Deleted (via Webhook)',
                properties={
                    'status': 'cancelled'
                }
            )
            logger.info(f"Cancelled subscription for user {user.user_id}")

    except Exception as e:
        logger.error(f"Error handling subscription deleted: {e}")

def handle_payment_succeeded(invoice):
    """Handle successful payment"""
    try:
        customer_id = invoice['customer']
        subscription_id = invoice.get('subscription')

        user = db_manager.get_user_by_stripe_customer_id(customer_id)
        if user:
            # Update user status based on payment success
            db_manager.update_user_stripe_info(
                user.user_id,
                subscription_status='active' # Ensure status is active after successful payment
            )
            # Track payment success via webhook
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Payment Succeeded (via Webhook)',
                properties={
                    'invoice_id': invoice.get('id'),
                    'subscription_id': subscription_id
                }
            )
            logger.info(f"Payment succeeded for user {user.user_id}")

    except Exception as e:
        logger.error(f"Error handling payment succeeded: {e}")

def handle_payment_failed(invoice):
    """Handle failed payment"""
    try:
        customer_id = invoice['customer']

        user = db_manager.get_user_by_stripe_customer_id(customer_id)
        if user:
            db_manager.update_user_stripe_info(
                user.user_id,
                subscription_status='past_due'
            )
            # Track payment failure via webhook
            analytics_service.track_user_event(
                user_id=str(user.user_id),
                event_name='Payment Failed (via Webhook)',
                properties={
                    'invoice_id': invoice.get('id'),
                    'due_amount': invoice.get('amount_due')
                }
            )
            logger.info(f"Payment failed for user {user.user_id}")

    except Exception as e:
        logger.error(f"Error handling payment failed: {e}")

@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f"404 Not Found: {error}")
    # Track 404 errors
    user_id = get_current_user().user_id if get_current_user() else 'anonymous_user'
    analytics_service.track_user_event(
        user_id=str(user_id),
        event_name='Page Not Found (404)',
        properties={
            'path': request.path,
            'error_message': str(error)
        }
    )
    return render_template('404.html'), 404

@app.route('/test-stripe')
def test_stripe():
    """Test Stripe configuration"""
    try:
        # Test if Stripe keys are configured
        test_mode = stripe_service.test_mode
        api_key_configured = bool(stripe_service.get_publishable_key())

        # Try to create a test customer
        test_customer = None
        customer_creation_test = 'failed'
        try:
            test_customer = stripe_service.create_customer(
                email="test@example.com",
                name="Test User",
                metadata={'test': 'true'}
            )
            if test_customer:
                customer_creation_test = 'success'
        except Exception as ce:
            logger.error(f"Stripe customer creation test failed: {ce}")
            customer_creation_test = f"failed: {str(ce)}"

        # Try to create a test checkout session
        test_checkout = None
        checkout_error = None
        checkout_session_test = 'failed'

        try:
            if test_customer:
                test_checkout = stripe_service.create_checkout_session(
                    customer_email="test@example.com",
                    price_id='price_1RvL44Hynku0jyEH12IrEJuI',  # Solo plan
                    success_url=f"{request.url_root.rstrip('/')}/test-success",
                    cancel_url=f"{request.url_root.rstrip('/')}/test-cancel",
                    customer_id=test_customer['id'],
                    metadata={'test': 'true'}
                )
                if test_checkout:
                    checkout_session_test = 'success'
        except Exception as checkout_ex:
            logger.error(f"Stripe checkout session test failed: {checkout_ex}")
            checkout_error = str(checkout_ex)
            checkout_session_test = f"failed: {str(checkout_ex)}"

        # Track Stripe test execution
        analytics_service.track_user_event(
            user_id='platform_admin', # Assuming this test is run by an admin
            event_name='Ran Stripe Test',
            properties={
                'test_mode': test_mode,
                'api_key_configured': api_key_configured,
                'customer_creation_test': customer_creation_test,
                'checkout_session_test': checkout_session_test
            }
        )

        return jsonify({
            'stripe_configured': True,
            'test_mode': test_mode,
            'api_key_configured': api_key_configured,
            'customer_creation_test': customer_creation_test,
            'checkout_session_test': checkout_session_test,
            'checkout_error': checkout_error,
            'checkout_url': test_checkout.get('url') if test_checkout else None,
            'publishable_key': stripe_service.get_publishable_key()[:20] + "..." if stripe_service.get_publishable_key() else 'Not set',
            'price_ids': stripe_service.plan_price_mapping
        })

    except Exception as e:
        logger.error(f"Stripe test failed: {e}")
        # Track Stripe test failure
        analytics_service.track_user_event(
            user_id='platform_admin',
            event_name='Stripe Test Failed',
            properties={'error': str(e)}
        )
        return jsonify({
            'stripe_configured': False,
            'error': str(e)
        }), 500

@app.route('/test-stripe-direct')
def test_stripe_direct():
    """Create a direct test checkout session and redirect to it"""
    try:
        base_url = request.url_root.rstrip('/')

        # Create a simple test checkout session
        test_checkout = stripe_service.create_checkout_session(
            customer_email="test@example.com",
            price_id='price_1RvL44Hynku0jyEH12IrEJuI',  # Solo plan
            success_url=f"{base_url}/test-success",
            cancel_url=f"{base_url}/test-cancel",
            metadata={'test': 'direct_test'}
        )

        if test_checkout and test_checkout.get('url'):
            # Track direct Stripe test execution
            analytics_service.track_user_event(
                user_id='platform_admin',
                event_name='Ran Direct Stripe Test',
                properties={'checkout_url_exists': True}
            )
            # Return an HTML page that immediately redirects
            return f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Stripe Test Redirect</title>
                <meta http-equiv="refresh" content="0; url={test_checkout['url']}">
            </head>
            <body>
                <p>Redirecting to Stripe checkout... <a href="{test_checkout['url']}">Click here if you're not redirected</a></p>
                <script>window.location.href = "{test_checkout['url']}";</script>
            </body>
            </html>
            '''
        else:
            # Track direct Stripe test failure
            analytics_service.track_user_event(
                user_id='platform_admin',
                event_name='Direct Stripe Test Failed',
                properties={'checkout_url_exists': False}
            )
            return "Failed to create checkout session", 500

    except Exception as e:
        logger.error(f"Direct Stripe test failed: {e}")
        # Track direct Stripe test failure
        analytics_service.track_user_event(
            user_id='platform_admin',
            event_name='Direct Stripe Test Failed',
            properties={'error': str(e)}
        )
        return f"Error: {str(e)}", 500

@app.route('/test-success')
def test_success():
    """Test success page"""
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Test Success</title></head>
    <body>
        <h1>✅ Stripe Test Successful!</h1>
        <p>The payment flow completed successfully.</p>
        <a href="/">Return to Home</a>
    </body>
    </html>
    '''

@app.route('/test-cancel')
def test_cancel():
    """Test cancel page"""
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Test Cancelled</title></head>
    <body>
        <h1>❌ Test Cancelled</h1>
        <p>You cancelled the test payment.</p>
        <a href="/">Return to Home</a>
    </body>
    </html>
    '''

@app.route('/debug-env')
@super_admin_required
def debug_env():
    """Debug environment variables - admin only"""
    import os

    env_status = {
        'STRIPE_SECRET_KEY_TEST': 'Set' if os.environ.get("STRIPE_SECRET_KEY_TEST") else 'Not Set',
        'STRIPE_PUBLISHABLE_KEY_TEST': 'Set' if os.environ.get("STRIPE_PUBLISHABLE_KEY_TEST") else 'Not Set',
        'STRIPE_WEBHOOK_SECRET': 'Set' if os.environ.get("STRIPE_WEBHOOK_SECRET") else 'Not Set',
        'SENDGRID_API_KEY': 'Set' if os.environ.get("SENDGRID_API_KEY") else 'Not Set',
        'GEMINI_API_KEY': 'Set' if os.environ.get("GEMINI_API_KEY") else 'Not Set'
    }
    # Track viewing debug env
    analytics_service.track_user_event(
        user_id='platform_admin',
        event_name='Viewed Debug Environment Variables'
    )
    return jsonify(env_status)

@app.route('/submit-feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback with optional file attachments"""
    try:
        # Get form data
        feedback_type = request.form.get('feedback_type', '').strip()
        message = request.form.get('message', '').strip()
        email = request.form.get('email', '').strip()
        name = request.form.get('name', '').strip()
        system_info = request.form.get('system_info', '').strip()

        if not all([feedback_type, message]):
            return jsonify({'error': 'Feedback type and message are required'}), 400

        # Prepare feedback data
        feedback_data = {
            'feedback_type': feedback_type,
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        }

        # Add user information if logged in
        user = get_current_user()
        user_id_for_tracking = 'anonymous_user'
        if user:
            feedback_data['user_info'] = {
                'user_id': user.user_id,
                'name': f"{user.first_name} {user.last_name}",
                'email': user.email
            }
            user_id_for_tracking = str(user.user_id)
        else:
            # For anonymous users, use provided contact info
            if email:
                feedback_data['email'] = email
            if name:
                feedback_data['name'] = name

        # Add system information if provided
        if system_info:
            feedback_data['system_info'] = system_info

        # Process file attachments
        attachments = []
        files = request.files.getlist('attachments')

        total_size = 0
        max_size = 10 * 1024 * 1024  # 10MB limit

        for file in files:
            if file.filename:
                # Check file size
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Reset to beginning

                total_size += file_size
                if total_size > max_size:
                    return jsonify({'error': 'Total file size exceeds 10MB limit'}), 400

                # Read file content
                file_content = file.read()

                attachments.append({
                    'filename': file.filename,
                    'content': file_content,
                    'content_type': file.content_type,
                    'size': file_size
                })

        # Send feedback email
        if email_service.send_feedback_email(feedback_data, attachments):
            # Track feedback submission
            analytics_service.track_user_event(
                user_id=user_id_for_tracking,
                event_name='Feedback Submitted',
                properties={
                    'feedback_type': feedback_type,
                    'has_attachments': len(attachments) > 0,
                    'message_length': len(message)
                }
            )
            logger.info(f"Feedback submitted: {feedback_type}")
            return jsonify({'success': True, 'message': 'Feedback sent successfully'})
        else:
            logger.error("Failed to send feedback email")
            return jsonify({'error': 'Failed to send feedback email'}), 500

    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        return jsonify({'error': 'An error occurred while processing your feedback'}), 500

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 Internal Server Error: {error}")
    # Track 500 errors
    user_id = get_current_user().user_id if get_current_user() else 'anonymous_user'
    analytics_service.track_user_event(
        user_id=str(user_id),
        event_name='Internal Server Error (500)',
        properties={
            'path': request.path,
            'error_message': str(error)
        }
    )
    return render_template('500.html'), 500