
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class BetaTrialManager:
    def __init__(self, json_file_path: str = "beta_trials.json"):
        """Initialize the beta trial manager with a JSON file path."""
        self.json_file_path = json_file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create the JSON file if it doesn't exist."""
        if not os.path.exists(self.json_file_path):
            with open(self.json_file_path, 'w') as f:
                json.dump([], f)

    def _load_beta_trials(self) -> List[Dict]:
        """Load all beta trial data from the JSON file."""
        try:
            with open(self.json_file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading beta trials: {e}")
            return []

    def _save_beta_trials(self, trials: List[Dict]):
        """Save all beta trial data to the JSON file."""
        try:
            with open(self.json_file_path, 'w') as f:
                json.dump(trials, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving beta trials: {e}")

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
            # Check user_sources.json for beta signup source
            from user_source_tracker import user_source_tracker
            user_source = user_source_tracker.get_user_source(user_email)
            
            if user_source and user_source.get('signup_source') == 'invitation_beta':
                return True
            
            # Check invitations.json for beta invitation
            if invite_code:
                from invitation_manager import invitation_manager
                invitation = invitation_manager.get_invitation(invite_code)
                if invitation and invitation.get('invitation_type') == 'beta':
                    return True
            
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
            trials = self._load_beta_trials()
            
            # Check if user already has a beta trial
            existing_trial = next((t for t in trials if t['user_email'] == user_email.lower().strip()), None)
            if existing_trial:
                logger.info(f"Beta trial already exists for {user_email}")
                return True
            
            # Create 90-day trial
            trial_start = datetime.now()
            trial_end = trial_start + timedelta(days=90)
            
            beta_trial = {
                "user_id": user_id,
                "user_email": user_email.lower().strip(),
                "invite_code": invite_code,
                "trial_start": trial_start.isoformat(),
                "trial_end": trial_end.isoformat(),
                "trial_days": 90,
                "trial_type": "beta",
                "status": "active",
                "created_at": trial_start.isoformat()
            }
            
            trials.append(beta_trial)
            self._save_beta_trials(trials)
            
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
            trials = self._load_beta_trials()
            
            # Check if user already has any trial
            existing_trial = next((t for t in trials if t['user_email'] == user_email.lower().strip()), None)
            if existing_trial:
                logger.info(f"Trial already exists for {user_email}")
                return True
            
            # Create trial
            trial_start = datetime.now()
            trial_end = trial_start + timedelta(days=trial_days)
            
            premium_trial = {
                "user_id": user_id,
                "user_email": user_email.lower().strip(),
                "trial_start": trial_start.isoformat(),
                "trial_end": trial_end.isoformat(),
                "trial_days": trial_days,
                "trial_type": trial_type,
                "status": "active",
                "created_at": trial_start.isoformat()
            }
            
            trials.append(premium_trial)
            self._save_beta_trials(trials)
            
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
            trials = self._load_beta_trials()
            email_lower = user_email.lower().strip()
            
            for trial in trials:
                if trial['user_email'] == email_lower:
                    return trial
            
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
            trials = self._load_beta_trials()
            email_lower = user_email.lower().strip()
            
            for trial in trials:
                if trial['user_email'] == email_lower:
                    trial['status'] = 'expired'
                    trial['expired_at'] = datetime.now().isoformat()
                    self._save_beta_trials(trials)
                    logger.info(f"Expired beta trial for {user_email}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error expiring beta trial for {user_email}: {e}")
            return False

    def get_all_beta_trials(self) -> List[Dict]:
        """
        Get all beta trial data.
        
        Returns:
            List of all beta trials
        """
        return self._load_beta_trials()

    def get_beta_trial_stats(self) -> Dict:
        """
        Get beta trial statistics.
        
        Returns:
            Dictionary with beta trial statistics
        """
        try:
            trials = self._load_beta_trials()
            
            if not trials:
                return {
                    'total_beta_trials': 0,
                    'active_trials': 0,
                    'expired_trials': 0,
                    'trials_expiring_soon': 0
                }
            
            active_trials = 0
            expired_trials = 0
            expiring_soon = 0
            
            now = datetime.now()
            soon_threshold = now + timedelta(days=7)  # Expiring within 7 days
            
            for trial in trials:
                if trial['status'] == 'active':
                    trial_end = datetime.fromisoformat(trial['trial_end'])
                    if now < trial_end:
                        active_trials += 1
                        if trial_end < soon_threshold:
                            expiring_soon += 1
                    else:
                        expired_trials += 1
                else:
                    expired_trials += 1
            
            return {
                'total_beta_trials': len(trials),
                'active_trials': active_trials,
                'expired_trials': expired_trials,
                'trials_expiring_soon': expiring_soon
            }
            
        except Exception as e:
            logger.error(f"Error getting beta trial stats: {e}")
            return {'error': str(e)}

# Global instance for easy access
beta_trial_manager = BetaTrialManager()
