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
            final_metadata = metadata or {}
            logger.info(f"STRIPE SERVICE DEBUG: create_customer called with:")
            logger.info(f"  email: {email}")
            logger.info(f"  name: {name}")
            logger.info(f"  metadata: {final_metadata}")

            # Log each metadata value and its type/length
            for key, value in final_metadata.items():
                logger.info(f"  metadata['{key}'] type: {type(value)}, length: {len(str(value))}, value: {repr(value)}")

                # Check if it's a User object being passed
                if hasattr(value, 'user_id'):
                    logger.error(f"  ❌ FOUND ISSUE: metadata['{key}'] is a User object! Use str(user.user_id) instead.")
                    raise Exception(f"Invalid metadata: {key} contains a User object instead of user_id string")

                if len(str(value)) > 500:
                    logger.error(f"  ❌ FOUND ISSUE: metadata['{key}'] exceeds 500 characters!")
                    logger.error(f"  ❌ Value preview: {str(value)[:100]}...")
                    raise Exception(f"Metadata value '{key}' exceeds 500 characters: {len(str(value))}")

            logger.info(f"STRIPE SERVICE DEBUG: About to call stripe.Customer.create...")
            print(f"DEBUG: About to call Stripe Customer.create with metadata: {final_metadata}")
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=final_metadata
            )
            logger.info(f"✓ Created Stripe customer: {customer.id} for {email}")
            return {
                'id': customer.id,
                'email': customer.email,
                'name': customer.name
            }
        except stripe.error.InvalidRequestError as e:
            logger.error(f"❌ STRIPE CUSTOMER CREATION - InvalidRequestError: {e}")
            logger.error(f"❌ Error occurred with metadata: {metadata}")
            raise Exception(f"Payment configuration error: {str(e)}")
        except stripe.error.StripeError as e:
            logger.error(f"❌ STRIPE CUSTOMER CREATION - StripeError: {e}")
            logger.error(f"❌ Error occurred with metadata: {metadata}")
            return None
        except Exception as e:
            logger.error(f"❌ STRIPE CUSTOMER CREATION - Unexpected error: {e}")
            logger.error(f"❌ Error occurred with metadata: {metadata}")
            raise

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

            final_metadata = metadata or {}
            logger.info(f"STRIPE SERVICE DEBUG: create_checkout_session called with:")
            logger.info(f"  customer_email: {customer_email}")
            logger.info(f"  price_id: {price_id}")
            logger.info(f"  customer_id: {customer_id}")
            logger.info(f"  metadata: {final_metadata}")

            # Log each metadata value and its type/length
            for key, value in final_metadata.items():
                logger.info(f"  metadata['{key}'] type: {type(value)}, length: {len(str(value))}, value: {repr(value)}")

                # Check if it's a User object being passed
                if hasattr(value, 'user_id'):
                    logger.error(f"  ❌ FOUND ISSUE: metadata['{key}'] is a User object! Use str(user.user_id) instead.")
                    raise Exception(f"Invalid metadata: {key} contains a User object instead of user_id string")

                if len(str(value)) > 500:
                    logger.error(f"  ❌ FOUND ISSUE: metadata['{key}'] exceeds 500 characters!")
                    logger.error(f"  ❌ Value preview: {str(value)[:100]}...")
                    raise Exception(f"Metadata value '{key}' exceeds 500 characters: {len(str(value))}")

            session_params = {
                'payment_method_types': ['card'],
                'mode': 'subscription',
                'line_items': [{
                    'price': price_id,
                    'quantity': 1,
                }],
                'success_url': success_url,
                'cancel_url': cancel_url,
                'metadata': final_metadata,
                'billing_address_collection': 'auto',
                'allow_promotion_codes': True,
                'automatic_tax': {'enabled': False}
            }

            # Add trial period if specified in metadata
            trial_days = (metadata or {}).get('trial_days')
            if trial_days and int(trial_days) > 0:
                session_params['subscription_data'] = {
                    'trial_period_days': int(trial_days)
                }
            # For 0 days trial or no trial specified, don't add subscription_data
            # This will use the default billing cycle without any trial period

            if customer_id:
                session_params['customer'] = customer_id
            else:
                session_params['customer_email'] = customer_email

            logger.info(f"Making Stripe API call to create checkout session...")
            logger.info(f"Session params: {session_params}")

            logger.info(f"STRIPE SERVICE DEBUG: About to call stripe.checkout.Session.create with params:")
            logger.info(f"  session_params keys: {list(session_params.keys())}")
            logger.info(f"  session_params metadata: {session_params.get('metadata', {})}")

            print(f"DEBUG: About to call Stripe checkout.Session.create with metadata: {session_params.get('metadata', {})}")
            try:
                session = stripe.checkout.Session.create(**session_params)
                logger.info(f"✓ Stripe API call completed. Session ID: {session.id}")
            except stripe.error.InvalidRequestError as e:
                logger.error(f"❌ STRIPE CHECKOUT SESSION - InvalidRequestError: {e}")
                logger.error(f"❌ Error occurred with session_params: {session_params}")
                logger.error(f"❌ Metadata that caused error: {session_params.get('metadata', {})}")
                raise Exception(f"Payment configuration error: {str(e)}")
            except Exception as stripe_err:
                logger.error(f"❌ STRIPE CHECKOUT SESSION - Unexpected error: {stripe_err}")
                logger.error(f"❌ Error occurred with session_params: {session_params}")
                logger.error(f"❌ Metadata that caused error: {session_params.get('metadata', {})}")
                raise

            if session and session.url:
                logger.info(f"✓ Successfully created checkout session: {session.id}")
                logger.info(f"✓ Checkout URL: {session.url}")
                logger.info(f"✓ Session status: {session.status}")
                logger.info(f"✓ Session mode: {session.mode}")
                logger.info(f"✓ Session payment_status: {session.payment_status}")

                # Validate the URL format
                if session.url.startswith('https://checkout.stripe.com/'):
                    logger.info("✓ Checkout URL format validated")
                else:
                    logger.warning(f"⚠️ Unexpected URL format: {session.url}")

                return {
                    'id': session.id,
                    'url': session.url,
                    'status': session.status
                }
            else:
                logger.error(f"❌ Session created but missing URL")
                logger.error(f"❌ Session object: {session}")
                logger.error(f"❌ Session dict: {session.to_dict() if hasattr(session, 'to_dict') else 'No to_dict method'}")
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