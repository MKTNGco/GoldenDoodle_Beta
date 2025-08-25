
import os
import json
import sqlite3
import logging
import hmac
import hashlib
from datetime import datetime
from typing import Dict, Optional
from flask import request, jsonify, render_template
import requests

logger = logging.getLogger(__name__)

class CrispMarketplace:
    def __init__(self):
        self.marketplace_id = os.environ.get('CRISP_MARKETPLACE_ID')
        self.marketplace_key = os.environ.get('CRISP_MARKETPLACE_KEY')
        self.webhook_secret = os.environ.get('CRISP_WEBHOOK_SIGNING_SECRET')
        self.base_url = "https://api.crisp.chat/v1"
        
        # Initialize SQLite database for storing plugin installations
        self.init_database()
        
        if not self.marketplace_id or not self.marketplace_key:
            logger.warning("Crisp Marketplace credentials not configured")
        if not self.webhook_secret:
            logger.warning("Crisp webhook signing secret not configured")
    
    def init_database(self):
        """Initialize SQLite database for plugin installations"""
        try:
            conn = sqlite3.connect('crisp_installations.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS installations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    website_id TEXT UNIQUE NOT NULL,
                    token TEXT NOT NULL,
                    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Crisp installations database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    
    def save_installation(self, website_id: str, token: str) -> bool:
        """Save plugin installation data"""
        try:
            conn = sqlite3.connect('crisp_installations.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO installations (website_id, token, updated_at)
                VALUES (?, ?, ?)
            ''', (website_id, token, datetime.now()))
            
            conn.commit()
            conn.close()
            logger.info(f"Saved installation for website_id: {website_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save installation: {e}")
            return False
    
    def get_installation(self, website_id: str) -> Optional[Dict]:
        """Get plugin installation data"""
        try:
            conn = sqlite3.connect('crisp_installations.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT website_id, token, installed_at, updated_at
                FROM installations
                WHERE website_id = ?
            ''', (website_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'website_id': result[0],
                    'token': result[1],
                    'installed_at': result[2],
                    'updated_at': result[3]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get installation: {e}")
            return None
    
    def make_authenticated_request(self, website_id: str, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """Make authenticated request to Crisp API using stored token"""
        installation = self.get_installation(website_id)
        if not installation:
            logger.error(f"No installation found for website_id: {website_id}")
            return None
        
        headers = {
            'Authorization': f'Bearer {installation["token"]}',
            'Content-Type': 'application/json',
            'X-Crisp-Tier': 'plugin'
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
    
    def enrich_lead_data(self, user_id: str, website_id: str) -> Dict:
        """
        Placeholder function for lead enrichment.
        This would typically integrate with external data sources.
        """
        logger.info(f"Enriching lead data for user_id: {user_id}")
        
        # Simulate lead enrichment process
        enriched_data = {
            'user_id': user_id,
            'website_id': website_id,
            'enriched_at': datetime.now().isoformat(),
            'data_sources': ['internal_database', 'social_lookup', 'company_data'],
            'enrichment_score': 0.85,
            'lead_quality': 'high',
            'estimated_company_size': '50-100 employees',
            'industry': 'Technology',
            'location': 'San Francisco, CA'
        }
        
        # In a real implementation, you would:
        # 1. Look up the user in your database
        # 2. Call external APIs for data enrichment
        # 3. Score the lead based on various factors
        # 4. Update the user profile in Crisp with enriched data
        
        return enriched_data
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature from Crisp"""
        if not self.webhook_secret:
            logger.warning("No webhook secret configured - skipping signature verification")
            return True
            
        if not signature:
            logger.error("No signature provided in webhook request")
            return False
            
        # Crisp uses HMAC-SHA256
        expected_signature = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures safely
        return hmac.compare_digest(f"sha256={expected_signature}", signature)

# Global instance
crisp_marketplace = CrispMarketplace()
