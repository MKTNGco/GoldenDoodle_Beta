
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from database import DatabaseManager
import psycopg2.extras

logger = logging.getLogger(__name__)

class BetaTrialManager:
    def __init__(self):
        """Initialize the beta trial manager with database connection."""
        self.db = DatabaseManager()

    def is_beta_user(self, user_email: str, invite_code: str = None) -> bool:
        """
        Check if a user is a beta user based on email and/or invite code.
        
        Args:
            user_email: User's email address
            invite_code: Optional invitation code used during registration
            
        Returns:
            True if user is a beta user, False otherwise
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Check user_sources table for beta signup source
            cursor.execute("""
                SELECT signup_source FROM user_sources 
                WHERE user_email = %s
            """, (user_email.lower().strip(),))
            
            user_source = cursor.fetchone()
            if user_source and user_source['signup_source'] == 'invitation_beta':
                cursor.close()
                conn.close()
                return True
            
            # Check invitations table for beta invitation
            if invite_code:
                cursor.execute("""
                    SELECT invitation_type FROM invitations 
                    WHERE invite_code = %s
                """, (invite_code,))
                
                invitation = cursor.fetchone()
                if invitation and invitation['invitation_type'] == 'beta':
                    cursor.close()
                    conn.close()
                    return True
            
            cursor.close()
            conn.close()
            return False
            
        except Exception as e:
            logger.error(f"Error checking if user is beta: {e}")
            return False

    def create_beta_trial(self, user_id: str, user_email: str, invite_code: str = None) -> bool:
        """
        Create a 90-day beta trial for a user.
        
        Args:
            user_id: User's ID
            user_email: User's email address
            invite_code: Invitation code used during registration
            
        Returns:
            True if beta trial was created successfully, False otherwise
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            email_lower = user_email.lower().strip()
            
            # Check if user already has a beta trial
            cursor.execute("""
                SELECT id FROM beta_trials 
                WHERE user_email = %s
            """, (email_lower,))
            
            existing_trial = cursor.fetchone()
            if existing_trial:
                logger.info(f"Beta trial already exists for {user_email}")
                cursor.close()
                conn.close()
                return True
            
            # Create 90-day trial
            trial_start = datetime.now()
            trial_end = trial_start + timedelta(days=90)
            
            cursor.execute("""
                INSERT INTO beta_trials 
                (user_id, user_email, invite_code, trial_start, trial_end, 
                 trial_days, trial_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                email_lower,
                invite_code,
                trial_start,
                trial_end,
                90,
                'beta',
                'active'
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Created 90-day beta trial for {user_email} (User ID: {user_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error creating beta trial for {user_email}: {e}")
            return False

    def create_premium_trial(self, user_id: str, user_email: str, trial_days: int = 7, trial_type: str = 'premium_free_trial') -> bool:
        """
        Create a premium trial for any user (used for free users getting premium features).
        
        Args:
            user_id: User's ID
            user_email: User's email address
            trial_days: Number of trial days (default 7)
            trial_type: Type of trial (default 'premium_free_trial')
            
        Returns:
            True if trial was created successfully, False otherwise
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            email_lower = user_email.lower().strip()
            
            # Check if user already has any trial
            cursor.execute("""
                SELECT id FROM beta_trials 
                WHERE user_email = %s
            """, (email_lower,))
            
            existing_trial = cursor.fetchone()
            if existing_trial:
                logger.info(f"Trial already exists for {user_email}")
                cursor.close()
                conn.close()
                return True
            
            # Create trial
            trial_start = datetime.now()
            trial_end = trial_start + timedelta(days=trial_days)
            
            cursor.execute("""
                INSERT INTO beta_trials 
                (user_id, user_email, trial_start, trial_end, 
                 trial_days, trial_type, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                email_lower,
                trial_start,
                trial_end,
                trial_days,
                trial_type,
                'active'
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Created {trial_days}-day {trial_type} for {user_email} (User ID: {user_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error creating premium trial for {user_email}: {e}")
            return False

    def get_beta_trial(self, user_email: str) -> Optional[Dict]:
        """
        Get beta trial information for a user.
        
        Args:
            user_email: User's email address
            
        Returns:
            Beta trial data if found, None otherwise
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            email_lower = user_email.lower().strip()
            
            cursor.execute("""
                SELECT * FROM beta_trials 
                WHERE user_email = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (email_lower,))
            
            trial = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if trial:
                # Convert to dictionary with ISO format dates
                trial_dict = dict(trial)
                trial_dict['trial_start'] = trial_dict['trial_start'].isoformat()
                trial_dict['trial_end'] = trial_dict['trial_end'].isoformat()
                trial_dict['created_at'] = trial_dict['created_at'].isoformat()
                if trial_dict['expired_at']:
                    trial_dict['expired_at'] = trial_dict['expired_at'].isoformat()
                return trial_dict
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting beta trial for {user_email}: {e}")
            return None

    def is_beta_trial_active(self, user_email: str) -> bool:
        """
        Check if a user's beta trial is still active.
        
        Args:
            user_email: User's email address
            
        Returns:
            True if beta trial is active, False otherwise
        """
        try:
            trial = self.get_beta_trial(user_email)
            if not trial:
                return False
            
            if trial['status'] != 'active':
                return False
            
            trial_end = datetime.fromisoformat(trial['trial_end'])
            return datetime.now() < trial_end
            
        except Exception as e:
            logger.error(f"Error checking beta trial status for {user_email}: {e}")
            return False

    def get_trial_expiration(self, user_email: str) -> Optional[datetime]:
        """
        Get the trial expiration date for a beta user.
        
        Args:
            user_email: User's email address
            
        Returns:
            Trial expiration datetime if found, None otherwise
        """
        try:
            trial = self.get_beta_trial(user_email)
            if trial:
                return datetime.fromisoformat(trial['trial_end'])
            return None
            
        except Exception as e:
            logger.error(f"Error getting trial expiration for {user_email}: {e}")
            return None

    def get_days_remaining(self, user_email: str) -> Optional[int]:
        """
        Get the number of days remaining in a beta trial.
        
        Args:
            user_email: User's email address
            
        Returns:
            Days remaining if trial is active, None otherwise
        """
        try:
            trial_end = self.get_trial_expiration(user_email)
            if trial_end:
                days_remaining = (trial_end - datetime.now()).days
                return max(0, days_remaining)
            return None
            
        except Exception as e:
            logger.error(f"Error calculating days remaining for {user_email}: {e}")
            return None

    def expire_beta_trial(self, user_email: str) -> bool:
        """
        Mark a beta trial as expired.
        
        Args:
            user_email: User's email address
            
        Returns:
            True if trial was expired successfully, False otherwise
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            email_lower = user_email.lower().strip()
            
            cursor.execute("""
                UPDATE beta_trials 
                SET status = 'expired', expired_at = %s
                WHERE user_email = %s
            """, (datetime.now(), email_lower))
            
            success = cursor.rowcount > 0
            conn.commit()
            cursor.close()
            conn.close()
            
            if success:
                logger.info(f"Expired beta trial for {user_email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error expiring beta trial for {user_email}: {e}")
            return False

    def get_all_beta_trials(self) -> List[Dict]:
        """
        Get all beta trial data.
        
        Returns:
            List of all beta trials
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT * FROM beta_trials 
                ORDER BY created_at DESC
            """)
            
            trials = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Convert to list of dictionaries with ISO format dates
            trials_list = []
            for trial in trials:
                trial_dict = dict(trial)
                trial_dict['trial_start'] = trial_dict['trial_start'].isoformat()
                trial_dict['trial_end'] = trial_dict['trial_end'].isoformat()
                trial_dict['created_at'] = trial_dict['created_at'].isoformat()
                if trial_dict['expired_at']:
                    trial_dict['expired_at'] = trial_dict['expired_at'].isoformat()
                trials_list.append(trial_dict)
            
            return trials_list
            
        except Exception as e:
            logger.error(f"Error getting all beta trials: {e}")
            return []

    def get_beta_trial_stats(self) -> Dict:
        """
        Get beta trial statistics.
        
        Returns:
            Dictionary with beta trial statistics
        """
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get total count
            cursor.execute("SELECT COUNT(*) as total FROM beta_trials")
            total_result = cursor.fetchone()
            total_trials = total_result['total'] if total_result else 0
            
            if total_trials == 0:
                cursor.close()
                conn.close()
                return {
                    'total_beta_trials': 0,
                    'active_trials': 0,
                    'expired_trials': 0,
                    'trials_expiring_soon': 0
                }
            
            # Get active trials (status = 'active' and trial_end > now)
            cursor.execute("""
                SELECT COUNT(*) as active FROM beta_trials 
                WHERE status = 'active' AND trial_end > %s
            """, (datetime.now(),))
            active_result = cursor.fetchone()
            active_trials = active_result['active'] if active_result else 0
            
            # Get expired trials (status = 'expired' or trial_end <= now)
            cursor.execute("""
                SELECT COUNT(*) as expired FROM beta_trials 
                WHERE status = 'expired' OR trial_end <= %s
            """, (datetime.now(),))
            expired_result = cursor.fetchone()
            expired_trials = expired_result['expired'] if expired_result else 0
            
            # Get trials expiring soon (active and trial_end within 7 days)
            soon_threshold = datetime.now() + timedelta(days=7)
            cursor.execute("""
                SELECT COUNT(*) as expiring_soon FROM beta_trials 
                WHERE status = 'active' AND trial_end > %s AND trial_end <= %s
            """, (datetime.now(), soon_threshold))
            expiring_result = cursor.fetchone()
            expiring_soon = expiring_result['expiring_soon'] if expiring_result else 0
            
            cursor.close()
            conn.close()
            
            return {
                'total_beta_trials': total_trials,
                'active_trials': active_trials,
                'expired_trials': expired_trials,
                'trials_expiring_soon': expiring_soon
            }
            
        except Exception as e:
            logger.error(f"Error getting beta trial stats: {e}")
            return {'error': str(e)}

# Global instance for easy access
beta_trial_manager = BetaTrialManager()
