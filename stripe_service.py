
import os
import stripe
import logging
from typing import Dict, Any, Optional, List
from models import SubscriptionLevel

logger = logging.getLogger(__name__)

class StripeService:
    def __init__(self):
        # Set Stripe API key based on environment
        self.test_mode = True  # Start in test mode
        if self.test_mode:
            stripe.api_key = os.environ.get("STRIPE_SECRET_KEY_TEST")
            self.publishable_key = os.environ.get("STRIPE_PUBLISHABLE_KEY_TEST")
        else:
            stripe.api_key = os.environ.get("STRIPE_SECRET_KEY_LIVE")
            self.publishable_key = os.environ.get("STRIPE_PUBLISHABLE_KEY_LIVE")
        
        self.webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        
        if not stripe.api_key:
            logger.error("Stripe API key not found in environment variables")
            
        # Plan mapping - maps your internal plan IDs to Stripe price IDs
        self.plan_price_mapping = {
            'solo': 'price_1234567890abcdef',  # Replace with your actual Practitioner price ID
            'team': 'price_1234567890ghijkl',   # Replace with your actual Organization price ID  
            'professional': 'price_1234567890mnopqr'  # Replace with your actual Powerhouse price ID
        }
    
    def get_publishable_key(self) -> str:
        """Get the publishable key for frontend"""
        return self.publishable_key or ""
    
    def create_customer(self, email: str, name: str, metadata: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """Create a new Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {}
            )
            logger.info(f"Created Stripe customer: {customer.id} for {email}")
            return {
                'id': customer.id,
                'email': customer.email,
                'name': customer.name
            }
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Stripe customer: {e}")
            return None
    
    def create_checkout_session(self, 
                              customer_email: str,
                              price_id: str,
                              success_url: str,
                              cancel_url: str,
                              customer_id: str = None,
                              metadata: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
        """Create a Stripe checkout session for subscription"""
        try:
            session_params = {
                'payment_method_types': ['card'],
                'mode': 'subscription',
                'line_items': [{
                    'price': price_id,
                    'quantity': 1,
                }],
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': metadata or {}
            }
            
            if customer_id:
                session_params['customer'] = customer_id
            else:
                session_params['customer_email'] = customer_email
            
            session = stripe.checkout.Session.create(**session_params)
            
            logger.info(f"Created checkout session: {session.id}")
            return {
                'id': session.id,
                'url': session.url
            }
        except stripe.error.StripeError as e:
            logger.error(f"Error creating checkout session: {e}")
            return None
    
    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription details"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                'id': subscription.id,
                'status': subscription.status,
                'customer': subscription.customer,
                'current_period_start': subscription.current_period_start,
                'current_period_end': subscription.current_period_end,
                'cancel_at_period_end': subscription.cancel_at_period_end
            }
        except stripe.error.StripeError as e:
            logger.error(f"Error getting subscription: {e}")
            return None
    
    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> bool:
        """Cancel a subscription"""
        try:
            if at_period_end:
                stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            else:
                stripe.Subscription.delete(subscription_id)
            
            logger.info(f"Cancelled subscription: {subscription_id}")
            return True
        except stripe.error.StripeError as e:
            logger.error(f"Error cancelling subscription: {e}")
            return False
    
    def create_billing_portal_session(self, customer_id: str, return_url: str) -> Optional[str]:
        """Create a billing portal session for customer self-service"""
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return session.url
        except stripe.error.StripeError as e:
            logger.error(f"Error creating billing portal session: {e}")
            return None
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> Optional[Dict[str, Any]]:
        """Verify webhook signature and return event"""
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return event
        except ValueError as e:
            logger.error(f"Invalid payload: {e}")
            return None
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {e}")
            return None

# Global Stripe service instance
stripe_service = StripeService()
