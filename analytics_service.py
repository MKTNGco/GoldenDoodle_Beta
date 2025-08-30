import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import time
import atexit
from functools import wraps
from flask import request, session, g

logger = logging.getLogger(__name__)


class AnalyticsService:

    def __init__(self):
        self.posthog_key = os.environ.get("POSTHOG_API_KEY")
        self.posthog_host = os.environ.get("POSTHOG_HOST",
                                           "https://app.posthog.com")
        self.posthog_client = None
        self.debug_mode = os.environ.get("DEBUG", "False").lower() == "true"

        if self.debug_mode:
            logger.debug(
                f"🔍 PostHog API Key present: {bool(self.posthog_key)}")
            logger.debug(f"🔍 PostHog Host: {self.posthog_host}")

        # Initialize PostHog client if API key is available
        if self.posthog_key:
            try:
                import posthog

                # Set module-level configuration
                posthog.api_key = self.posthog_key
                posthog.host = self.posthog_host
                posthog.debug = self.debug_mode

                # Important: Set sync mode for immediate sending
                posthog.sync_mode = True

                # Set timeouts and retries
                posthog.timeout = 30
                posthog.max_retries = 3

                self.posthog_client = posthog
                logger.info("✅ PostHog analytics initialized successfully")

                # Register cleanup function
                atexit.register(self.flush)

            except ImportError:
                logger.warning(
                    "❌ PostHog library not installed. Install with: pip install posthog"
                )
                self.posthog_client = None
            except Exception as e:
                logger.error(f"❌ Failed to initialize PostHog: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.posthog_client = None
        else:
            logger.warning(
                "❌ POSTHOG_API_KEY not found in environment variables")

    def get_user_id(self):
        """Get consistent user ID for tracking"""
        # Try to get user ID from session, fall back to IP address
        user_id = None

        # If you have user authentication, use that
        if 'user_id' in session:
            user_id = session['user_id']
        elif 'username' in session:
            user_id = session['username']
        elif hasattr(g, 'user') and g.user:
            user_id = str(g.user.id) if hasattr(g.user, 'id') else str(g.user)
        else:
            # Fall back to IP + session ID for anonymous users
            ip = request.remote_addr or 'unknown'
            session_id = session.get('_id', 'no_session')
            user_id = f"anonymous_{ip}_{session_id}"

        return user_id

    def track_user_event(self,
                         user_id: str,
                         event_name: str,
                         properties: Dict[str, Any] = None):
        """Track user events for analytics"""
        if not properties:
            properties = {}

        # Add default properties for B2B SaaS metrics
        properties.update({
            'timestamp':
            datetime.utcnow().isoformat(),
            'environment':
            'replit',
            'source':
            'goldendoodlelm',
            'user_agent':
            request.headers.get('User-Agent', '') if request else '',
            'ip_address':
            request.remote_addr if request else '',
            'url':
            request.url if request else '',
            'path':
            request.path if request else ''
        })

        # Send to PostHog if available
        if self.posthog_client and self.posthog_key:
            try:
                import posthog

                logger.info(f"📤 Tracking: {event_name} for user {user_id}")

                posthog.capture(distinct_id=user_id,
                                event=event_name,
                                properties=properties)

                # Force immediate flush
                posthog.flush()
                time.sleep(0.1)

                logger.info(
                    f"✅ Event '{event_name}' sent to PostHog for user {user_id}"
                )
                return True

            except Exception as e:
                logger.error(f"❌ Error sending event to PostHog: {e}")
                return False
        else:
            logger.warning(
                f"⚠️ PostHog not configured - would track: {event_name} for user {user_id}"
            )
            return False

    def track_page_view(self, page_name: str = None):
        """Track page view - this creates your DAU/WAU data"""
        user_id = self.get_user_id()
        page = page_name or request.path if request else 'unknown'

        return self.track_user_event(
            user_id=user_id,
            event_name='$pageview',  # PostHog standard event name
            properties={
                'page_name': page,
                'page_title': page_name or page,
                'referrer': request.referrer if request else None
            })

    def track_session_start(self, user_properties: Dict[str, Any] = None):
        """Track when user starts a session - key for DAU/WAU"""
        user_id = self.get_user_id()

        # Identify user first
        if user_properties:
            self.identify_user(user_id, user_properties)

        return self.track_user_event(user_id=user_id,
                                     event_name='Session Started',
                                     properties={
                                         'session_start': True,
                                         'beta_tester': True,
                                         'app_version': 'beta'
                                     })

    def track_session_end(self, session_duration_minutes: float = None):
        """Track when user ends session - for session length metrics"""
        user_id = self.get_user_id()

        properties = {'session_end': True}
        if session_duration_minutes:
            properties['session_duration_minutes'] = session_duration_minutes

        return self.track_user_event(user_id=user_id,
                                     event_name='Session Ended',
                                     properties=properties)

    def track_feature_usage(self,
                            feature_name: str,
                            additional_properties: Dict[str, Any] = None):
        """Track specific feature usage"""
        user_id = self.get_user_id()

        properties = {'feature_name': feature_name, 'feature_used': True}

        if additional_properties:
            properties.update(additional_properties)

        return self.track_user_event(user_id=user_id,
                                     event_name='Feature Used',
                                     properties=properties)

    def auto_track_route(self, route_name: str = None):
        """Decorator to automatically track route visits"""

        def decorator(func):

            @wraps(func)
            def wrapper(*args, **kwargs):
                # Track page view automatically
                page_name = route_name or func.__name__ or request.endpoint
                self.track_page_view(page_name)

                # Execute original function
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def identify_user(self,
                      user_id: str,
                      user_properties: Dict[str, Any] = None):
        """Identify a user with their properties"""
        if not user_properties:
            user_properties = {}

        # Add beta tester flag
        user_properties.update({
            'beta_tester': True,
            'app_version': 'beta',
            'signup_date': datetime.utcnow().isoformat()
        })

        if self.posthog_client and self.posthog_key:
            try:
                import posthog

                logger.info(f"📤 Identifying user {user_id}")

                posthog.identify(distinct_id=user_id,
                                 properties=user_properties)

                posthog.flush()
                time.sleep(0.1)

                logger.info(f"✅ User {user_id} identified in PostHog")
                return True

            except Exception as e:
                logger.error(f"❌ Error identifying user in PostHog: {e}")
                return False
        else:
            logger.warning(
                f"⚠️ PostHog not configured - would identify user {user_id}")
            return False

    def flush(self):
        """Flush any pending events"""
        if self.posthog_client:
            try:
                import posthog
                posthog.flush()
                logger.debug("✅ PostHog events flushed")
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"❌ Error flushing PostHog events: {e}")


# Global analytics service instance
analytics_service = AnalyticsService()


# Middleware to automatically track all page views
def track_all_requests():
    """Add this to your Flask app to automatically track all requests"""

    @app.before_request
    def before_request():
        # Skip tracking for static files and API endpoints
        if not request.path.startswith(
                '/static') and not request.path.startswith('/api'):
            # Track page view for every request
            analytics_service.track_page_view()

    return before_request
