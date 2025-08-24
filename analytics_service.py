
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        self.posthog_key = os.environ.get("POSTHOG_API_KEY")
        self.posthog_host = os.environ.get("POSTHOG_HOST", "https://app.posthog.com")
        self.posthog_client = None
        self.debug_mode = os.environ.get("DEBUG", "False").lower() == "true"
        
        if self.debug_mode:
            logger.debug(f"🔍 PostHog API Key present: {bool(self.posthog_key)}")
            logger.debug(f"🔍 PostHog Host: {self.posthog_host}")
        
        # Initialize PostHog client if API key is available
        if self.posthog_key:
            try:
                import posthog
                posthog.api_key = self.posthog_key
                posthog.host = self.posthog_host
                posthog.debug = self.debug_mode
                self.posthog_client = posthog
                logger.info("✅ PostHog analytics initialized successfully")
                
                # Test connection
                if self.debug_mode:
                    self._test_connection()
                    
            except ImportError:
                logger.warning("❌ PostHog library not installed. Install with: pip install posthog")
                self.posthog_client = None
            except Exception as e:
                logger.error(f"❌ Failed to initialize PostHog: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.posthog_client = None
        else:
            logger.warning("❌ POSTHOG_API_KEY not found in environment variables")
            
    def _test_connection(self):
        """Test PostHog connection in debug mode"""
        try:
            self.track_user_event("debug_test", "PostHog Connection Test", {"debug": True})
            logger.debug("🔍 PostHog connection test sent")
        except Exception as e:
            logger.error(f"❌ PostHog connection test failed: {e}")
            
    def track_user_event(self, user_id: str, event_name: str, properties: Dict[str, Any] = None):
        """Track user events for analytics"""
        if not properties:
            properties = {}
            
        # Add default properties
        properties.update({
            'timestamp': datetime.utcnow().isoformat(),
            'environment': 'replit',
            'source': 'goldendoodlelm'
        })
        
        # Send to PostHog if available
        if self.posthog_client and self.posthog_key:
            try:
                self.posthog_client.capture(
                    distinct_id=user_id,
                    event=event_name,
                    properties=properties
                )
                logger.info(f"✅ Event '{event_name}' sent to PostHog for user {user_id}")
                logger.debug(f"PostHog event payload: {{'distinct_id': '{user_id}', 'event': '{event_name}', 'properties': {properties}}}")
                return True
            except Exception as e:
                logger.error(f"❌ Error sending event to PostHog: {e}")
                return False
        else:
            logger.warning(f"⚠️ PostHog not configured - would track: {event_name} for user {user_id}")
            return False
    
    def identify_user(self, user_id: str, user_properties: Dict[str, Any] = None):
        """Identify a user with their properties"""
        if not user_properties:
            user_properties = {}
            
        if self.posthog_client and self.posthog_key:
            try:
                # PostHog uses identify as a module-level function, not a method
                import posthog
                posthog.identify(
                    distinct_id=user_id,
                    properties=user_properties
                )
                logger.info(f"✅ User {user_id} identified in PostHog")
                return True
            except Exception as e:
                logger.error(f"❌ Error identifying user in PostHog: {e}")
                return False
        else:
            logger.warning(f"⚠️ PostHog not configured - would identify user {user_id}")
            return False
    
    def flush(self):
        """Flush any pending events"""
        if self.posthog_client:
            try:
                self.posthog_client.flush()
                logger.debug("✅ PostHog events flushed")
            except Exception as e:
                logger.error(f"❌ Error flushing PostHog events: {e}")

# Global analytics service instance
analytics_service = AnalyticsService()
