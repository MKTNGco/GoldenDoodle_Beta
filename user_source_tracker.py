
import logging
from datetime import datetime
from typing import Dict, Optional, List
from database import DatabaseManager

logger = logging.getLogger(__name__)

class UserSourceTracker:
    def __init__(self):
        """Initialize the user source tracker with database connection."""
        self.db = DatabaseManager()

    def track_user_signup(self, user_email: str, signup_source: str, invite_code: str = None) -> bool:
        """
        Track a user signup with source information

        Args:
            user_email: User's email address
            signup_source: Source of signup (organic, invitation_beta, referral, paid_solo, user_referral, etc.)
            invite_code: Optional invitation code if applicable

        Returns:
            True if tracking was successful, False otherwise
        """
        try:
            query = """
            INSERT INTO user_sources (
                user_email, signup_source, invite_code, 
                signup_date, tracked_at
            ) VALUES (%s, %s, %s, %s, %s)
            """

            params = (
                user_email.lower().strip(),
                signup_source,
                invite_code,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            )

            self.db.execute_query(query, params)

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
            results = self.db.execute_query(
                "SELECT * FROM user_sources WHERE user_email = %s ORDER BY tracked_at DESC LIMIT 1",
                (user_email.lower().strip(),)
            )

            if results:
                return dict(results[0])

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
            results = self.db.execute_query(
                "SELECT * FROM user_sources WHERE signup_source = %s ORDER BY signup_date DESC",
                (signup_source,)
            )

            return [dict(row) for row in results]

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
            results = self.db.execute_query(
                "SELECT * FROM user_sources WHERE invite_code = %s ORDER BY signup_date DESC",
                (invite_code,)
            )

            return [dict(row) for row in results]

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
            # Get total count
            total_result = self.db.execute_query("SELECT COUNT(*) as count FROM user_sources")
            total_signups = total_result[0]['count'] if total_result else 0

            if total_signups == 0:
                return {
                    'total_signups': 0,
                    'sources': {},
                    'invite_signups': 0,
                    'organic_signups': 0
                }

            # Get counts by source
            source_results = self.db.execute_query("""
            SELECT signup_source, COUNT(*) as count 
            FROM user_sources 
            GROUP BY signup_source
            """)

            source_counts = {row['signup_source']: row['count'] for row in source_results}

            # Get invite signups count
            invite_result = self.db.execute_query("""
            SELECT COUNT(*) as count 
            FROM user_sources 
            WHERE invite_code IS NOT NULL
            """)
            invite_signups = invite_result[0]['count'] if invite_result else 0

            organic_signups = total_signups - invite_signups

            return {
                'total_signups': total_signups,
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
        try:
            results = self.db.execute_query(
                "SELECT * FROM user_sources ORDER BY signup_date DESC"
            )

            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Error getting all sources: {e}")
            return []

    def get_source_trends(self, days: int = 30) -> Dict:
        """
        Get signup source trends for the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with trend data
        """
        try:
            query = """
            SELECT 
                signup_source,
                DATE(signup_date) as signup_day,
                COUNT(*) as daily_count
            FROM user_sources 
            WHERE signup_date >= NOW() - INTERVAL '%s days'
            GROUP BY signup_source, DATE(signup_date)
            ORDER BY signup_day DESC, signup_source
            """

            results = self.db.execute_query(query, (days,))

            trends = {}
            for row in results:
                source = row['signup_source']
                day = row['signup_day'].isoformat() if hasattr(row['signup_day'], 'isoformat') else str(row['signup_day'])
                count = row['daily_count']

                if source not in trends:
                    trends[source] = {}
                trends[source][day] = count

            return {
                'period_days': days,
                'trends': trends
            }

        except Exception as e:
            logger.error(f"Error getting source trends: {e}")
            return {'error': str(e)}

# Global instance for easy access
user_source_tracker = UserSourceTracker()
