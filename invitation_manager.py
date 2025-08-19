
import json
import os
import random
import string
from datetime import datetime
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class InvitationManager:
    def __init__(self, json_file_path: str = "invitations.json"):
        """Initialize the invitation manager with a JSON file path."""
        self.json_file_path = json_file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Create the JSON file if it doesn't exist."""
        if not os.path.exists(self.json_file_path):
            with open(self.json_file_path, 'w') as f:
                json.dump([], f)
    
    def _load_invitations(self) -> List[Dict]:
        """Load all invitations from the JSON file."""
        try:
            with open(self.json_file_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading invitations: {e}")
            return []
    
    def _save_invitations(self, invitations: List[Dict]):
        """Save all invitations to the JSON file."""
        try:
            with open(self.json_file_path, 'w') as f:
                json.dump(invitations, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving invitations: {e}")
            raise
    
    def _generate_random_code(self, length: int = 8) -> str:
        """Generate a random alphanumeric code."""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    def _generate_unique_code(self, prefix: str = "", length: int = 8) -> str:
        """Generate a unique invitation code with optional prefix."""
        invitations = self._load_invitations()
        existing_codes = {inv['invite_code'] for inv in invitations}
        
        max_attempts = 100
        for _ in range(max_attempts):
            if prefix:
                # If prefix is provided, subtract its length from total length
                remaining_length = max(1, length - len(prefix))
                code = prefix + self._generate_random_code(remaining_length)
            else:
                code = self._generate_random_code(length)
            
            if code not in existing_codes:
                return code
        
        raise Exception("Failed to generate unique invitation code after maximum attempts")
    
    def create_invitation(self, email: str, org_name: str, invitation_type: str, prefix: str = "") -> str:
        """
        Create a new invitation and return the invitation code.
        
        Args:
            email: Invitee's email address
            org_name: Organization name
            invitation_type: Type of invitation (beta, team_member, referral)
            prefix: Optional prefix for the invitation code
        
        Returns:
            The generated invitation code
        """
        invitations = self._load_invitations()
        
        # Generate unique code
        invite_code = self._generate_unique_code(prefix=prefix)
        
        # Create invitation data
        invitation = {
            "invite_code": invite_code,
            "invitee_email": email.lower().strip(),
            "organization_name": org_name.strip(),
            "invitation_type": invitation_type,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        # Add to list and save
        invitations.append(invitation)
        self._save_invitations(invitations)
        
        logger.info(f"Created invitation {invite_code} for {email} to {org_name}")
        return invite_code
    
    def get_invitation(self, code: str) -> Optional[Dict]:
        """
        Look up an invitation by code.
        
        Args:
            code: The invitation code to look up
        
        Returns:
            The invitation data if found, None otherwise
        """
        invitations = self._load_invitations()
        
        for invitation in invitations:
            if invitation['invite_code'] == code.upper():
                return invitation
        
        return None
    
    def mark_accepted(self, code: str) -> bool:
        """
        Mark an invitation as accepted.
        
        Args:
            code: The invitation code to mark as accepted
        
        Returns:
            True if successfully marked, False if invitation not found
        """
        invitations = self._load_invitations()
        
        for invitation in invitations:
            if invitation['invite_code'] == code.upper():
                invitation['status'] = 'accepted'
                invitation['accepted_at'] = datetime.now().isoformat()
                self._save_invitations(invitations)
                logger.info(f"Marked invitation {code} as accepted")
                return True
        
        logger.warning(f"Invitation {code} not found for marking as accepted")
        return False
    
    def mark_expired(self, code: str) -> bool:
        """
        Mark an invitation as expired.
        
        Args:
            code: The invitation code to mark as expired
        
        Returns:
            True if successfully marked, False if invitation not found
        """
        invitations = self._load_invitations()
        
        for invitation in invitations:
            if invitation['invite_code'] == code.upper():
                invitation['status'] = 'expired'
                invitation['expired_at'] = datetime.now().isoformat()
                self._save_invitations(invitations)
                logger.info(f"Marked invitation {code} as expired")
                return True
        
        logger.warning(f"Invitation {code} not found for marking as expired")
        return False
    
    def get_invitations_by_email(self, email: str) -> List[Dict]:
        """
        Get all invitations for a specific email address.
        
        Args:
            email: The email address to search for
        
        Returns:
            List of invitations for the email
        """
        invitations = self._load_invitations()
        return [inv for inv in invitations if inv['invitee_email'] == email.lower().strip()]
    
    def get_invitations_by_status(self, status: str) -> List[Dict]:
        """
        Get all invitations with a specific status.
        
        Args:
            status: The status to filter by (pending, accepted, expired)
        
        Returns:
            List of invitations with the specified status
        """
        invitations = self._load_invitations()
        return [inv for inv in invitations if inv['status'] == status]
    
    def get_all_invitations(self) -> List[Dict]:
        """
        Get all invitations.
        
        Returns:
            List of all invitations
        """
        return self._load_invitations()

# Global instance for easy access
invitation_manager = InvitationManager()
