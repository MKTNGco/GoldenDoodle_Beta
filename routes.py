from flask import render_template, request, redirect, url_for, flash, session, jsonify
from app import app
from auth import login_required, admin_required, get_current_user, login_user, logout_user
from database import db_manager
from gemini_service import gemini_service
from rag_service import rag_service
from models import TenantType, SubscriptionLevel, CONTENT_MODE_CONFIG
import json
import logging

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
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            organization_name = request.form.get('organization_name', '').strip()
            user_type = request.form.get('user_type', 'independent')
            subscription_level = request.form.get('subscription_level', 'entry')
            
            # Validation
            if not all([name, email, password]):
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
            
            # Create tenant
            if user_type == 'company':
                tenant = db_manager.create_tenant(
                    name=organization_name,
                    tenant_type=TenantType.COMPANY,
                    max_brand_voices=3
                )
                is_admin = True  # First user in company is admin
            else:
                tenant = db_manager.create_tenant(
                    name=f"{name}'s Account",
                    tenant_type=TenantType.INDEPENDENT_USER,
                    max_brand_voices=1
                )
                is_admin = False
            
            # Create user
            user = db_manager.create_user(
                tenant_id=tenant.tenant_id,
                name=name,
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
@login_required
def chat():
    """Main chat interface"""
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
    
    return render_template('chat.html', 
                         user=user, 
                         tenant=tenant,
                         company_brand_voices=company_brand_voices,
                         user_brand_voices=user_brand_voices,
                         content_modes=CONTENT_MODE_CONFIG)

@app.route('/generate', methods=['POST'])
@login_required
def generate():
    """Generate AI content"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', '').strip()
        content_mode = data.get('content_mode')
        brand_voice_id = data.get('brand_voice_id')
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
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
    
    # Check limits
    max_user_voices = 10 if user.subscription_level == SubscriptionLevel.PRO else 1
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
    """Brand voice creation wizard"""
    voice_type = request.args.get('type', 'user')
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    if voice_type == 'company' and not user.is_admin:
        flash('Admin access required to create company brand voices.', 'error')
        return redirect(url_for('brand_voices'))
    
    return render_template('brand_voice_wizard.html', voice_type=voice_type, user=user)

@app.route('/create-brand-voice', methods=['POST'])
@login_required
def create_brand_voice():
    """Create a new brand voice"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        voice_type = data.get('voice_type', 'user')
        
        # Brand voice configuration from wizard
        tone = data.get('tone', 'professional')
        style = data.get('style', 'informative')
        audience = data.get('audience', 'general')
        values = data.get('values', [])
        key_messages = data.get('key_messages', [])
        terminology = data.get('terminology', {})
        
        if not name:
            return jsonify({'error': 'Brand voice name is required'}), 400
        
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        tenant = db_manager.get_tenant_by_id(user.tenant_id)
        if not tenant:
            return jsonify({'error': 'Invalid tenant'}), 400
        
        # Check permissions and limits
        if voice_type == 'company':
            if not user.is_admin:
                return jsonify({'error': 'Admin access required'}), 403
            
            existing_company_voices = db_manager.get_company_brand_voices(tenant.tenant_id)
            if len(existing_company_voices) >= tenant.max_brand_voices:
                return jsonify({'error': f'Maximum of {tenant.max_brand_voices} company brand voices allowed'}), 400
            
            user_id = None
        else:
            existing_user_voices = db_manager.get_user_brand_voices(tenant.tenant_id, user.user_id)
            max_voices = 10 if user.subscription_level == SubscriptionLevel.PRO else 1
            
            if len(existing_user_voices) >= max_voices:
                return jsonify({'error': f'Maximum of {max_voices} personal brand voices allowed for your subscription level'}), 400
            
            user_id = user.user_id
        
        # Create configuration
        configuration = {
            'tone': tone,
            'style': style,
            'audience': audience,
            'values': values,
            'key_messages': key_messages,
            'terminology': terminology
        }
        
        # Create markdown content for RAG
        markdown_content = f"""# {name} Brand Voice Guide

## Tone
{tone.title()} - Use a {tone} tone in all communications.

## Style
{style.title()} - Maintain a {style} writing style.

## Target Audience
{audience.title()} - Content is designed for {audience} audiences.

## Core Values
{chr(10).join(f"- {value}" for value in values)}

## Key Messages
{chr(10).join(f"- {message}" for message in key_messages)}

## Preferred Terminology
{chr(10).join(f"- Use '{preferred}' instead of '{avoid}'" for avoid, preferred in terminology.items())}

## Guidelines
- Always maintain trauma-informed communication principles
- Use person-first, strengths-based language
- Prioritize safety, trust, and empowerment
- Be culturally responsive and inclusive
"""
        
        # Create brand voice
        brand_voice = db_manager.create_brand_voice(
            tenant_id=tenant.tenant_id,
            name=name,
            configuration=configuration,
            markdown_content=markdown_content,
            user_id=user_id
        )
        
        return jsonify({
            'success': True,
            'brand_voice_id': brand_voice.brand_voice_id,
            'message': f'Brand voice "{name}" created successfully!'
        })
        
    except Exception as e:
        logger.error(f"Error creating brand voice: {e}")
        return jsonify({'error': 'An error occurred while creating the brand voice. Please try again.'}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500
