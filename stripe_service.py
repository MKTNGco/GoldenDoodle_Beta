
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
            'solo': 'price_1RvL44Hynku0jyEH12IrEJuI',  # Replace with your actual Practitioner price ID
            'team': 'price_1RvL4sHynku0jyEH4go1pRLM',   # Replace with your actual Organization price ID  
            'professional': 'price_1RvL79Hynku0jyEHm7b89IPr'  # Replace with your actual Powerhouse price ID
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
            # Log the parameters being used
            logger.info(f"Creating checkout session with:")
            logger.info(f"  Price ID: {price_id}")
            logger.info(f"  Customer Email: {customer_email}")
            logger.info(f"  Customer ID: {customer_id}")
            logger.info(f"  Success URL: {success_url}")
            logger.info(f"  Cancel URL: {cancel_url}")
            logger.info(f"  API Key configured: {bool(stripe.api_key)}")
            logger.info(f"  Test mode: {self.test_mode}")
            
            # Verify Stripe keys are configured
            if not stripe.api_key:
                logger.error("Stripe API key is not configured")
                raise Exception("Stripe API key missing")
            
            if not self.publishable_key:
                logger.error("Stripe publishable key is not configured")
                raise Exception("Stripe publishable key missing")
            
            # Validate price ID exists
            if price_id not in self.plan_price_mapping.values():
                logger.error(f"Invalid price ID: {price_id}")
                logger.error(f"Available price IDs: {list(self.plan_price_mapping.values())}")
                raise Exception(f"Invalid pricing plan: {price_id}")
                
            session_params = {
                'payment_method_types': ['card'],
                'mode': 'subscription',
                'line_items': [{
                    'price': price_id,
                    'quantity': 1,
                }],
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': metadata or {},
                'billing_address_collection': 'auto',
                'allow_promotion_codes': True,
                'automatic_tax': {'enabled': False},
                'subscription_data': {
                    'trial_period_days': 0  # Explicitly no trial
                }
            }
            
            if customer_id:
                session_params['customer'] = customer_id
            else:
                session_params['customer_email'] = customer_email
            
            logger.info(f"Making Stripe API call to create checkout session...")
            logger.info(f"Session params: {session_params}")
            
            session = stripe.checkout.Session.create(**session_params)
            
            if session and session.url:
                logger.info(f"✓ Successfully created checkout session: {session.id}")
                logger.info(f"✓ Checkout URL: {session.url}")
                
                return {
                    'id': session.id,
                    'url': session.url
                }
            else:
                logger.error(f"❌ Session created but missing URL: {session}")
                return None
        except stripe.error.InvalidRequestError as e:
            logger.error(f"Invalid Stripe request: {e}")
            raise Exception(f"Payment configuration error: {str(e)}")
        except stripe.error.AuthenticationError as e:
            logger.error(f"Stripe authentication error: {e}")
            raise Exception("Payment service authentication failed")
        except stripe.error.RateLimitError as e:
            logger.error(f"Stripe rate limit error: {e}")
            raise Exception("Payment service is temporarily unavailable")
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API Error creating checkout session: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error code: {getattr(e, 'code', 'N/A')}")
            raise Exception(f"Payment processing error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating checkout session: {e}")
            raise
    
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
