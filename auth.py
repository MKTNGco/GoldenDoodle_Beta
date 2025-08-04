import functools
from typing import Optional
from flask import session, redirect, url_for, request, flash
from database import db_manager
from models import User

def get_current_user() -> Optional[User]:
    """Get the current logged-in user"""
    if 'user_id' not in session:
        return None
    
    user_id = session['user_id']
    # Get user from database by ID
    try:
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM users WHERE user_id = %s
        """, (user_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            from models import SubscriptionLevel
            return User(
                user_id=str(row[0]),
                tenant_id=str(row[1]),
                first_name=row[2],
                last_name=row[3],
                email=row[4],
                password_hash=row[5],
                subscription_level=SubscriptionLevel(row[6]),
                is_admin=row[7],
                email_verified=row[8] if len(row) > 8 else False
            )
    except Exception as e:
        print(f"Error getting current user: {e}")
    
    return None

def login_required(f):
    """Decorator to require login for a route"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if get_current_user() is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin access for a route"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return redirect(url_for('login', next=request.url))
        if not user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('chat'))
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorator to require super admin access for a route"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return redirect(url_for('login', next=request.url))
        # Check if user is super admin (you can modify this logic)
        if not (user.email == 'sunny@goldendoodlelm.ai' or user.is_admin):
            flash('Super admin access required.', 'error')
            return redirect(url_for('chat'))
        return f(*args, **kwargs)
    return decorated_function

def login_user(user: User):
    """Log in a user by setting session data"""
    session['user_id'] = user.user_id
    session['user_name'] = user.name
    session['user_email'] = user.email
    session['tenant_id'] = user.tenant_id

def logout_user():
    """Log out the current user"""
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)
    session.pop('tenant_id', None)
