import uuid
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum

class TenantType(Enum):
    COMPANY = 'company'
    INDEPENDENT_USER = 'independent_user'

class SubscriptionLevel(Enum):
    SOLO = 'solo'
    PRO = 'pro'
    TEAM = 'team'
    ENTERPRISE = 'enterprise'

@dataclass
class Tenant:
    tenant_id: str
    tenant_type: TenantType
    name: str
    database_name: str
    max_brand_voices: int = 3

@dataclass
class User:
    user_id: str
    tenant_id: str
    first_name: str
    last_name: str
    email: str
    password_hash: str
    subscription_level: SubscriptionLevel
    is_admin: bool = False
    email_verified: bool = False
    created_at: Optional[str] = None
    last_login: Optional[str] = None
    plan_id: str = 'free'  # Default to free plan
    
    @property
    def name(self) -> str:
        """Full name property for backward compatibility"""
        return f"{self.first_name} {self.last_name}".strip()</dataclass>

@dataclass
class BrandVoice:
    brand_voice_id: str
    name: str
    configuration: Dict[str, Any]
    markdown_content: Optional[str] = None
    user_id: Optional[str] = None  # For user brand voices

class ContentMode:
    EMAIL = 'email'
    ARTICLE = 'article'
    SOCIAL_MEDIA = 'social_media'
    REWRITE = 'rewrite'
    SUMMARIZE = 'summarize'
    BRAINSTORM = 'brainstorm'
    ANALYZE = 'analyze'

# Temperature settings for different content modes
CONTENT_MODE_TEMPERATURES = {
    ContentMode.SUMMARIZE: 0.3,
    ContentMode.REWRITE: 0.4,
    ContentMode.ANALYZE: 0.4,
    ContentMode.EMAIL: 0.5,
    ContentMode.ARTICLE: 0.7,
    ContentMode.SOCIAL_MEDIA: 0.8,
    ContentMode.BRAINSTORM: 0.9
}

# Content mode configurations
CONTENT_MODE_CONFIG = {
    ContentMode.EMAIL: {
        'name': 'Email',
        'placeholder': 'Compose a professional, empathetic email...',
        'temperature': 0.5,
        'description': 'Professional, empathetic email generation'
    },
    ContentMode.ARTICLE: {
        'name': 'Article',
        'placeholder': 'Write an informative article with trauma-informed principles...',
        'temperature': 0.7,
        'description': 'Informative content writing with trauma-informed principles'
    },
    ContentMode.SOCIAL_MEDIA: {
        'name': 'Social Media',
        'placeholder': 'Create engaging, accessible social media content...',
        'temperature': 0.8,
        'description': 'Engaging, accessible social content creation'
    },
    ContentMode.REWRITE: {
        'name': 'Rewrite',
        'placeholder': 'Transform existing content with trauma-informed enhancements...',
        'temperature': 0.4,
        'description': 'Transform existing content with trauma-informed enhancements'
    },
    ContentMode.SUMMARIZE: {
        'name': 'Summarize',
        'placeholder': 'Summarize this document or content...',
        'temperature': 0.3,
        'description': 'Document and content summarization'
    },
    ContentMode.BRAINSTORM: {
        'name': 'Idea Brainstorm',
        'placeholder': 'Let\'s brainstorm creative ideas...',
        'temperature': 0.9,
        'description': 'Creative ideation and brainstorming'
    },
    ContentMode.ANALYZE: {
        'name': 'Analyze',
        'placeholder': 'Analyze this data or content...',
        'temperature': 0.4,
        'description': 'Data and content analysis'
    }
}
