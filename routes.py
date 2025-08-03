from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app
from auth import login_required, admin_required, get_current_user, login_user, logout_user
from database import db_manager
from gemini_service import gemini_service
from rag_service import rag_service
from models import TenantType, SubscriptionLevel, CONTENT_MODE_CONFIG
import json
import logging
import uuid

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
                return render_template('register.html')
            
            if user_type == 'company' and not organization_name:
                flash('Organization name is required for company accounts.', 'error')
                return render_template('register.html')
            
            # Check if user already exists
            existing_user = db_manager.get_user_by_email(email)
            if existing_user:
                flash('An account with this email already exists.', 'error')
                return render_template('register.html')
            
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
            
            # Log in user
            login_user(user)
            flash('Account created successfully! Welcome to GoldenDoodleLM.', 'success')
            return redirect(url_for('chat'))
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            flash('An error occurred during registration. Please try again.', 'error')
    
    return render_template('register.html')

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
        
        # Get brand voices
        company_brand_voices = []
        if tenant.tenant_type == TenantType.COMPANY:
            company_brand_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
        
        user_brand_voices = db_manager.get_user_brand_voices(tenant.tenant_id, user.user_id)
        
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
            # Get brand voice from database
            company_brand_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
            user_brand_voices = db_manager.get_user_brand_voices(tenant.tenant_id, user.user_id)
            
            all_brand_voices = company_brand_voices + user_brand_voices
            selected_brand_voice = next((bv for bv in all_brand_voices if bv.brand_voice_id == brand_voice_id), None)
            
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
        
        return jsonify({'response': response})
        
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return jsonify({'error': 'An error occurred while generating content. Please try again.'}), 500

@app.route('/how-to')
def how_to():
    """How to use GoldenDoodleLM guide page"""
    return render_template('how_to.html')

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
    
    # Get brand voices
    company_brand_voices = []
    if tenant.tenant_type == TenantType.COMPANY:
        company_brand_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
    
    user_brand_voices = db_manager.get_user_brand_voices(tenant.tenant_id, user.user_id)
    
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
    
    company_brand_voices = []
    if tenant.tenant_type == TenantType.COMPANY:
        company_brand_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
    
    user_brand_voices = db_manager.get_user_brand_voices(tenant.tenant_id, user.user_id)
    
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
    voice_type = request.args.get('type', 'user')
    edit_id = request.args.get('edit')
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
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
        
        # Required fields
        company_name = data.get('company_name', '').strip()
        company_url = data.get('company_url', '').strip()
        voice_short_name = data.get('voice_short_name', '').strip()
        voice_type = data.get('voice_type', 'user')
        brand_voice_id = data.get('brand_voice_id')  # For editing existing voices
        
        if not all([company_name, company_url, voice_short_name]):
            return jsonify({'error': 'Company name, URL, and voice name are required'}), 400
        
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if not tenant:
            return jsonify({'error': 'Invalid tenant'}), 400
        
        # Determine if this is an edit or create operation
        is_editing = bool(brand_voice_id)
        
        # Check permissions and limits
        if voice_type == 'company':
            if not user.is_admin:
                return jsonify({'error': 'Admin access required'}), 403
            
            if not is_editing:
                existing_company_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
                if len(existing_company_voices) >= tenant.max_brand_voices:
                    return jsonify({'error': f'Maximum of {tenant.max_brand_voices} company brand voices allowed'}), 400
            
            user_id = None
        else:
            if not is_editing:
                existing_user_voices = db_manager.get_user_brand_voices(tenant.tenant_id, user.user_id)
                
                if user.subscription_level == SubscriptionLevel.PRO:
                    max_voices = 10
                elif user.subscription_level == SubscriptionLevel.SOLO:
                    max_voices = 1
                elif user.subscription_level in [SubscriptionLevel.TEAM, SubscriptionLevel.ENTERPRISE]:
                    max_voices = 10
                else:
                    max_voices = 1
                
                if len(existing_user_voices) >= max_voices:
                    return jsonify({'error': f'Maximum of {max_voices} personal brand voices allowed for your subscription level'}), 400
            
            user_id = user.user_id
        
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
                return jsonify({'error': 'Brand voice not found or permission denied'}), 404
            
            brand_voice = db_manager.update_brand_voice(
                tenant_id=tenant.tenant_id,
                brand_voice_id=brand_voice_id,
                wizard_data=wizard_data,
                markdown_content=markdown_content,
                user_id=user_id
            )
            
            return jsonify({
                'success': True,
                'brand_voice_id': brand_voice.brand_voice_id,
                'message': f'Brand voice "{voice_short_name}" updated successfully!'
            })
        else:
            brand_voice = db_manager.create_comprehensive_brand_voice(
                tenant_id=tenant.tenant_id,
                wizard_data=wizard_data,
                markdown_content=markdown_content,
                user_id=user_id
            )
            
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
            return jsonify({'error': 'Brand voice not found'}), 404
        
        # Check permissions
        if selected_brand_voice.user_id and selected_brand_voice.user_id != user.user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        if not selected_brand_voice.user_id and not user.is_admin:
            return jsonify({'error': 'Permission denied'}), 403
        
        return jsonify(selected_brand_voice.configuration)
        
    except Exception as e:
        logger.error(f"Error getting brand voice: {e}")
        return jsonify({'error': 'An error occurred while loading the brand voice'}), 500

@app.route('/auto-save-brand-voice', methods=['POST'])
@login_required
def auto_save_brand_voice():
    """Auto-save brand voice progress"""
    try:
        data = request.get_json()
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Check if required fields are present for auto-save
        company_name = data.get('company_name', '').strip()
        company_url = data.get('company_url', '').strip()
        voice_short_name = data.get('voice_short_name', '').strip()
        
        if not all([company_name, company_url, voice_short_name]):
            return jsonify({'error': 'Required fields missing'}), 400
        
        # Auto-save logic would go here
        # For now, just return success with a mock profile_id
        profile_id = data.get('profile_id') or str(uuid.uuid4())
        
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
    markdown = f"""# {data['voice_short_name']} Brand Voice Guide

## Company Overview
**Company:** {data['company_name']}
**Website:** {data['company_url']}

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
- **Communication Style:** {data['personality_formal_casual']}/5 (1=Formal, 5=Casual)
- **Tone:** {data['personality_serious_playful']}/5 (1=Serious, 5=Playful)
- **Approach:** {data['personality_traditional_modern']}/5 (1=Traditional, 5=Modern)
- **Authority:** {data['personality_authoritative_collaborative']}/5 (1=Authoritative, 5=Collaborative)
- **Accessibility:** {data['personality_accessible_exclusive']}/5 (1=Accessible, 5=Aspirational)

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

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500
