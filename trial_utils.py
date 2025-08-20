
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def get_trial_period_for_user(user_email: str, invite_code: str = None) -> int:
    """
    Get the appropriate trial period for a user (7 days for all users, 90 days for beta users).
    
    Args:
        user_email: User's email address
        invite_code: Optional invitation code used during registration
        
    Returns:
        Number of trial days (7 for normal users, 90 for beta users)
    """
    try:
        from beta_trial_manager import beta_trial_manager
        
        if beta_trial_manager.is_beta_user(user_email, invite_code):
            logger.info(f"Beta user detected: {user_email} - extending trial to 90 days")
            return 90
        else:
            logger.info(f"All users get premium trial: {user_email} - 7-day premium trial")
            return 7
            
    except Exception as e:
        logger.error(f"Error determining trial period for {user_email}: {e}")
        # Default to 7 days if there's an error
        return 7

def is_user_in_trial_period(user_email: str) -> bool:
    """
    Check if a user is currently in their trial period (either beta or regular).
    
    Args:
        user_email: User's email address
        
    Returns:
        True if user is in trial period, False otherwise
    """
    try:
        from beta_trial_manager import beta_trial_manager
        
        # Check if user has an active beta trial
        if beta_trial_manager.is_beta_trial_active(user_email):
            return True
        
        # For regular users, you would check against your existing trial logic
        # This function is designed to work alongside your existing 7-day trial system
        # without modifying it
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking trial period for {user_email}: {e}")
        return False

def get_trial_expiration_date(user_email: str) -> Optional[datetime]:
    """
    Get the trial expiration date for a user.
    
    Args:
        user_email: User's email address
        
    Returns:
        Trial expiration datetime if found, None otherwise
    """
    try:
        from beta_trial_manager import beta_trial_manager
        
        # Check for beta trial first
        beta_expiration = beta_trial_manager.get_trial_expiration(user_email)
        if beta_expiration:
            return beta_expiration
        
        # For regular users, you would integrate with your existing trial system here
        return None
        
    except Exception as e:
        logger.error(f"Error getting trial expiration for {user_email}: {e}")
        return None

def get_trial_days_remaining(user_email: str) -> Optional[int]:
    """
    Get the number of days remaining in a user's trial.
    
    Args:
        user_email: User's email address
        
    Returns:
        Days remaining if in trial, None otherwise
    """
    try:
        from beta_trial_manager import beta_trial_manager
        
        # Check for beta trial first
        beta_days = beta_trial_manager.get_days_remaining(user_email)
        if beta_days is not None:
            return beta_days
        
        # For regular users, you would integrate with your existing trial system here
        return None
        
    except Exception as e:
        logger.error(f"Error getting trial days remaining for {user_email}: {e}")
        return None

def create_premium_trial_for_free_user(user_id: str, user_email: str) -> bool:
    """
    Create a 7-day premium trial for free users.
    
    Args:
        user_id: User's ID
        user_email: User's email address
        
    Returns:
        True if trial was created successfully, False otherwise
    """
    try:
        from beta_trial_manager import beta_trial_manager
        
        # Create a 7-day premium trial using the beta trial system
        # This reuses the existing infrastructure but with shorter duration
        trial_created = beta_trial_manager.create_premium_trial(
            user_id=user_id,
            user_email=user_email,
            trial_days=7,
            trial_type='premium_free_trial'
        )
        
        if trial_created:
            logger.info(f"Created 7-day premium trial for free user {user_email}")
            return True
        else:
            logger.warning(f"Failed to create premium trial for {user_email}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating premium trial for {user_email}: {e}")
        return False
