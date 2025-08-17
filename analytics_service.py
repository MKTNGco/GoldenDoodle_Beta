
import os
import requests
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        # You can use services like Mixpanel, Segment, or PostHog
        self.mixpanel_token = os.environ.get("MIXPANEL_TOKEN")
        self.posthog_key = os.environ.get("POSTHOG_API_KEY")
        
    def track_user_event(self, user_id: str, event_name: str, properties: Dict[str, Any] = None):
        """Track user events for analytics"""
        if not properties:
            properties = {}
            
        properties.update({
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'environment': 'replit'
        })
        
        # Send to PostHog (free tier available)
        if self.posthog_key:
            self._send_to_posthog(user_id, event_name, properties)
            
        # Send to Mixpanel (free tier available)
        if self.mixpanel_token:
            self._send_to_mixpanel(user_id, event_name, properties)
    
    def _send_to_posthog(self, user_id: str, event: str, properties: Dict):
        """Send event to PostHog"""
        try:
            payload = {
                'api_key': self.posthog_key,
                'event': event,
                'properties': {
                    'distinct_id': user_id,
                    **properties
                }
            }
            
            response = requests.post(
                'https://app.posthog.com/capture/',
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"Event '{event}' sent to PostHog for user {user_id}")
            else:
                logger.warning(f"Failed to send event to PostHog: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending to PostHog: {e}")
    
    def _send_to_mixpanel(self, user_id: str, event: str, properties: Dict):
        """Send event to Mixpanel"""
        try:
            import base64
            import json
            
            data = {
                'event': event,
                'properties': {
                    'distinct_id': user_id,
                    'token': self.mixpanel_token,
                    **properties
                }
            }
            
            encoded_data = base64.b64encode(json.dumps(data).encode()).decode()
            
            response = requests.post(
                'https://api.mixpanel.com/track/',
                data={'data': encoded_data},
                timeout=5
            )
            
            if response.status_code == 200:
                logger.info(f"Event '{event}' sent to Mixpanel for user {user_id}")
            else:
                logger.warning(f"Failed to send event to Mixpanel: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending to Mixpanel: {e}")

# Global analytics service instance
analytics_service = AnalyticsService()
