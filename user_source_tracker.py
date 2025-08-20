
import json
import os
from datetime import datetime
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class UserSourceTracker:
    def __init__(self, json_file_path: str = "user_sources.json"):
        """Initialize the user source tracker with a JSON file path."""
        self.json_file_path = json_file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create the JSON file if it doesn't exist."""
        if not os.path.exists(self.json_file_path):
            with open(self.json_file_path, 'w') as f:
                json.dump([], f)
    
    def _load_sources(self) -> List[Dict]:
        """Load all source tracking data from the JSON file."""
        try:
            with open(self.json_file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading user sources: {e}")
            return []
    
    def _save_sources(self, sources: List[Dict]):
        """Save all source tracking data to the JSON file."""
        try:
            with open(self.json_file_path, 'w') as f:
                json.dump(sources, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving user sources: {e}")
            # Don't raise exception - we don't want tracking failures to break registration
    
    def track_user_signup(self, user_email: str, signup_source: str, invite_code: Optional[str] = None) -> bool:
        """
        Track user signup source information.
        
        Args:
            user_email: User's email address
            signup_source: Source of signup (organic, invitation, referral, etc.)
            invite_code: Invitation code if applicable
        
        Returns:
            True if successfully tracked, False otherwise
        """
        try:
            sources = self._load_sources()
            
            # Create tracking entry
            tracking_entry = {
                "user_email": user_email.lower().strip(),
                "signup_source": signup_source,
                "invite_code": invite_code,
                "signup_date": datetime.now().isoformat(),
                "tracked_at": datetime.now().isoformat()
            }
            
            # Add to list and save
            sources.append(tracking_entry)
            self._save_sources(sources)
            
            logger.info(f"Tracked signup source for {user_email}: {signup_source}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to track signup source for {user_email}: {e}")
            return False
    
    def get_user_source(self, user_email: str) -> Optional[Dict]:
        """
        Get signup source information for a user.
        
        Args:
            user_email: User's email address
        
        Returns:
            Source tracking data if found, None otherwise
        """
        try:
            sources = self._load_sources()
            email_lower = user_email.lower().strip()
            
            for source in sources:
                if source['user_email'] == email_lower:
                    return source
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user source for {user_email}: {e}")
            return None
    
    def get_sources_by_type(self, signup_source: str) -> List[Dict]:
        """
        Get all users who signed up from a specific source.
        
        Args:
            signup_source: The signup source to filter by
        
        Returns:
            List of source tracking entries
        """
        try:
            sources = self._load_sources()
            return [source for source in sources if source['signup_source'] == signup_source]
            
        except Exception as e:
            logger.error(f"Error getting sources by type {signup_source}: {e}")
            return []
    
    def get_invite_code_usage(self, invite_code: str) -> List[Dict]:
        """
        Get all users who signed up with a specific invite code.
        
        Args:
            invite_code: The invite code to search for
        
        Returns:
            List of source tracking entries
        """
        try:
            sources = self._load_sources()
            return [source for source in sources if source.get('invite_code') == invite_code]
            
        except Exception as e:
            logger.error(f"Error getting invite code usage for {invite_code}: {e}")
            return []
    
    def get_signup_stats(self) -> Dict:
        """
        Get basic signup statistics.
        
        Returns:
            Dictionary with signup statistics
        """
        try:
            sources = self._load_sources()
            
            if not sources:
                return {
                    'total_signups': 0,
                    'sources': {},
                    'invite_signups': 0,
                    'organic_signups': 0
                }
            
            # Count by source
            source_counts = {}
            invite_signups = 0
            
            for source in sources:
                signup_source = source['signup_source']
                source_counts[signup_source] = source_counts.get(signup_source, 0) + 1
                
                if source.get('invite_code'):
                    invite_signups += 1
            
            organic_signups = len(sources) - invite_signups
            
            return {
                'total_signups': len(sources),
                'sources': source_counts,
                'invite_signups': invite_signups,
                'organic_signups': organic_signups
            }
            
        except Exception as e:
            logger.error(f"Error getting signup stats: {e}")
            return {'error': str(e)}
    
    def get_all_sources(self) -> List[Dict]:
        """
        Get all source tracking data.
        
        Returns:
            List of all source tracking entries
        """
        return self._load_sources()

# Global instance for easy access
user_source_tracker = UserSourceTracker()
