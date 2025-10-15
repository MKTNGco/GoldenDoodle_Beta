
import os
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class CrispService:
    def __init__(self):
        self.api_key = os.environ.get('CRISP_API_KEY')
        self.website_id = os.environ.get('CRISP_WEBSITE_ID')
        self.base_url = "https://api.crisp.chat/v1"
        
        if not self.api_key or not self.website_id:
            logger.warning("Crisp API credentials not configured")
            
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Make authenticated request to Crisp API"""
        if not self.api_key:
            logger.error("Crisp API key not configured")
            return None
            
        headers = {
            'Authorization': f'Basic {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Crisp API request failed: {e}")
            return None
    
    def create_or_update_profile(self, user_email: str, user_data: Dict) -> bool:
        """Create or update user profile in Crisp"""
        endpoint = f"/website/{self.website_id}/people/profile/{user_email}"
        
        profile_data = {
            "email": user_email,
            "person": {
                "nickname": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
                "avatar": user_data.get('avatar_url'),
            },
            "data": {
                "user_id": user_data.get('user_id'),
                "subscription_level": user_data.get('subscription_level'),
                "tenant_id": user_data.get('tenant_id'),
                "organization_name": user_data.get('organization_name'),  # Add organization name
                "organization_type": user_data.get('organization_type'),  # Add organization type
                "last_login": user_data.get('last_login'),
                "email_verified": user_data.get('email_verified', False),
                "is_admin": user_data.get('is_admin', False)
            }
        }
        
        result = self._make_request('PUT', endpoint, profile_data)
        return result is not None
    
    def track_event(self, user_email: str, event_name: str, event_data: Dict = None) -> bool:
        """Track custom event for user"""
        endpoint = f"/website/{self.website_id}/people/events/{user_email}"
        
        event_payload = {
            "text": event_name,
            "data": event_data or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        result = self._make_request('POST', endpoint, event_payload)
        return result is not None
    
    def send_message_to_user(self, user_email: str, message: str, from_operator: bool = True) -> bool:
        """Send a message to a user"""
        # First, get or create a conversation for the user
        conversation_id = self._get_or_create_conversation(user_email)
        if not conversation_id:
            return False
            
        endpoint = f"/website/{self.website_id}/conversation/{conversation_id}/message"
        
        message_data = {
            "type": "text",
            "from": "operator" if from_operator else "user",
            "origin": "chat",
            "content": message
        }
        
        result = self._make_request('POST', endpoint, message_data)
        return result is not None
    
    def _get_or_create_conversation(self, user_email: str) -> Optional[str]:
        """Get existing conversation or create new one for user"""
        # Search for existing conversations
        search_endpoint = f"/website/{self.website_id}/conversations"
        
        conversations = self._make_request('GET', search_endpoint)
        
        if conversations and conversations.get('data'):
            # Look for conversation with this user
            for conv in conversations['data']:
                if conv.get('people', {}).get('email') == user_email:
                    return conv.get('session_id')
        
        # Create new conversation if none found
        create_endpoint = f"/website/{self.website_id}/conversation"
        new_conv = self._make_request('POST', create_endpoint, {
            "people": {"email": user_email}
        })
        
        if new_conv and new_conv.get('data'):
            return new_conv['data'].get('session_id')
            
        return None
    
    def get_user_conversations(self, user_email: str) -> List[Dict]:
        """Get all conversations for a user"""
        endpoint = f"/website/{self.website_id}/people/conversations/{user_email}"
        
        result = self._make_request('GET', endpoint)
        if result and result.get('data'):
            return result['data']
        return []

# Global instance
crisp_service = CrispService()
