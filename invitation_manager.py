
import logging
from datetime import datetime
from typing import Dict, Optional, List
import random
import string
from database import DatabaseManager

logger = logging.getLogger(__name__)

class InvitationManager:
    def __init__(self):
        """Initialize the invitation manager with database connection."""
        self.db = DatabaseManager()

    def _generate_random_code(self, length: int = 8) -> str:
        """Generate a random alphanumeric code."""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

    def _generate_unique_code(self, prefix: str = "", length: int = 8) -> str:
        """Generate a unique invitation code with optional prefix."""
        max_attempts = 100
        for _ in range(max_attempts):
            if prefix:
                # If prefix is provided, subtract its length from total length
                remaining_length = max(1, length - len(prefix))
                code = prefix + self._generate_random_code(remaining_length)
            else:
                code = self._generate_random_code(length)

            # Check if code already exists
            existing = self.db.execute_query(
                "SELECT 1 FROM invitations WHERE invite_code = %s",
                (code,)
            )
            
            if not existing:
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
        try:
            # Generate unique code
            invite_code = self._generate_unique_code(prefix=prefix)

            # Insert invitation into database
            query = """
            INSERT INTO invitations (
                invite_code, invitee_email, organization_name, 
                invitation_type, status, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """

            params = (
                invite_code,
                email.lower().strip(),
                org_name.strip(),
                invitation_type,
                'pending',
                datetime.now().isoformat()
            )

            self.db.execute_query(query, params)

            logger.info(f"Created invitation {invite_code} for {email} to {org_name}")
            return invite_code

        except Exception as e:
            logger.error(f"Failed to create invitation: {e}")
            raise

    def get_invitation(self, code: str) -> Optional[Dict]:
        """
        Look up an invitation by code.

        Args:
            code: The invitation code to look up

        Returns:
            The invitation data if found, None otherwise
        """
        try:
            results = self.db.execute_query(
                "SELECT * FROM invitations WHERE invite_code = %s",
                (code.upper(),)
            )

            if results:
                return dict(results[0])

            return None

        except Exception as e:
            logger.error(f"Failed to get invitation {code}: {e}")
            return None

    def mark_accepted(self, code: str) -> bool:
        """
        Mark an invitation as accepted.

        Args:
            code: The invitation code to mark as accepted

        Returns:
            True if successfully marked, False if invitation not found
        """
        try:
            query = """
            UPDATE invitations 
            SET status = 'accepted', accepted_at = %s
            WHERE invite_code = %s
            """

            affected_rows = self.db.execute_query(
                query,
                (datetime.now().isoformat(), code.upper())
            )

            if affected_rows:
                logger.info(f"Marked invitation {code} as accepted")
                return True
            else:
                logger.warning(f"Invitation {code} not found for marking as accepted")
                return False

        except Exception as e:
            logger.error(f"Failed to mark invitation {code} as accepted: {e}")
            return False

    def mark_expired(self, code: str) -> bool:
        """
        Mark an invitation as expired.

        Args:
            code: The invitation code to mark as expired

        Returns:
            True if successfully marked, False if invitation not found
        """
        try:
            query = """
            UPDATE invitations 
            SET status = 'expired', expired_at = %s
            WHERE invite_code = %s
            """

            affected_rows = self.db.execute_query(
                query,
                (datetime.now().isoformat(), code.upper())
            )

            if affected_rows:
                logger.info(f"Marked invitation {code} as expired")
                return True
            else:
                logger.warning(f"Invitation {code} not found for marking as expired")
                return False

        except Exception as e:
            logger.error(f"Failed to mark invitation {code} as expired: {e}")
            return False

    def get_invitations_by_email(self, email: str) -> List[Dict]:
        """
        Get all invitations for a specific email address.

        Args:
            email: The email address to search for

        Returns:
            List of invitations for the email
        """
        try:
            results = self.db.execute_query(
                "SELECT * FROM invitations WHERE invitee_email = %s ORDER BY created_at DESC",
                (email.lower().strip(),)
            )

            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to get invitations for email {email}: {e}")
            return []

    def get_invitations_by_status(self, status: str) -> List[Dict]:
        """
        Get all invitations with a specific status.

        Args:
            status: The status to filter by (pending, accepted, expired)

        Returns:
            List of invitations with the specified status
        """
        try:
            results = self.db.execute_query(
                "SELECT * FROM invitations WHERE status = %s ORDER BY created_at DESC",
                (status,)
            )

            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to get invitations by status {status}: {e}")
            return []

    def get_invitations_by_type(self, invitation_type: str) -> List[Dict]:
        """
        Get all invitations of a specific type.

        Args:
            invitation_type: The invitation type to filter by

        Returns:
            List of invitations with the specified type
        """
        try:
            results = self.db.execute_query(
                "SELECT * FROM invitations WHERE invitation_type = %s ORDER BY created_at DESC",
                (invitation_type,)
            )

            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to get invitations by type {invitation_type}: {e}")
            return []

    def get_all_invitations(self) -> List[Dict]:
        """
        Get all invitations.

        Returns:
            List of all invitations
        """
        try:
            results = self.db.execute_query(
                "SELECT * FROM invitations ORDER BY created_at DESC"
            )

            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to get all invitations: {e}")
            return []

    def get_invitation_stats(self) -> Dict:
        """
        Get invitation statistics.

        Returns:
            Dictionary with invitation statistics
        """
        try:
            stats_query = """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted,
                COUNT(CASE WHEN status = 'expired' THEN 1 END) as expired
            FROM invitations
            """

            result = self.db.execute_query(stats_query)[0]

            return {
                'total_invitations': result['total'],
                'pending_invitations': result['pending'],
                'accepted_invitations': result['accepted'],
                'expired_invitations': result['expired'],
                'acceptance_rate': round((result['accepted'] / result['total'] * 100) if result['total'] > 0 else 0, 1)
            }

        except Exception as e:
            logger.error(f"Failed to get invitation stats: {e}")
            return {'error': str(e)}

# Global instance for easy access
invitation_manager = InvitationManager()
