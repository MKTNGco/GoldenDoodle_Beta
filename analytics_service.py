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

    def track_user_session_start(self, user, tenant=None):
        """
        Track user session start for DAU/WAU and tenant activity metrics
        Maps to: posthog.capture('user_session_start', {
            organization_id: user.organization_id,
            user_id: user.id
        })
        """
        if not user:
            return False

        try:
            # Build session start properties as per client requirements
            properties = {
                'user_id': str(user.user_id),
                'organization_id': user.tenant_id  # tenant_id is organization_id
            }

            # Add additional session context
            properties.update({
                'email': user.email,
                'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                'is_admin': user.is_admin,
                'session_timestamp': datetime.utcnow().isoformat()
            })

            # Add organization name if tenant is provided
            if tenant:
                properties['organization_name'] = tenant.name

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    logger.info(f"📤 Tracking user session start for user {user.user_id}")
                    
                    # Use PostHog capture with user_session_start event
                    posthog.capture(
                        distinct_id=str(user.user_id),
                        event='user_session_start',
                        properties=properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ User session start tracked for user {user.user_id}")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error tracking user session start: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would track session start for user {user.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in track_user_session_start: {e}")
            return False

    def track_token_usage(self, user, tokens_consumed, content_mode=None, user_monthly_total=None, org_monthly_total=None, tenant=None):
        """
        Track token usage for analytics and billing
        Maps to: posthog.capture('token_usage', {
            user_id: user.id,
            organization_id: user.organization_id,
            tokens_consumed: response.usage_metadata.total_token_count,
            content_mode: 'email', // or blog, social, etc.
            user_monthly_total: user.tokens_used_this_month,
            org_monthly_total: org.tokens_used_this_month
        })
        """
        if not user:
            return False

        try:
            # Build token usage properties as per client requirements
            properties = {
                'user_id': str(user.user_id),
                'organization_id': user.tenant_id,  # tenant_id is organization_id
                'tokens_consumed': tokens_consumed,
                'content_mode': content_mode,
                'user_monthly_total': user_monthly_total or 0,
                'org_monthly_total': org_monthly_total or 0
            }

            # Add additional context
            properties.update({
                'email': user.email,
                'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                'is_admin': user.is_admin,
                'usage_timestamp': datetime.utcnow().isoformat()
            })

            # Add organization name if tenant is provided
            if tenant:
                properties['organization_name'] = tenant.name

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    logger.info(f"📤 Tracking token usage for user {user.user_id}: {tokens_consumed} tokens")
                    
                    # Use PostHog capture with token_usage event
                    posthog.capture(
                        distinct_id=str(user.user_id),
                        event='token_usage',
                        properties=properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ Token usage tracked for user {user.user_id}")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error tracking token usage: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would track token usage for user {user.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in track_token_usage: {e}")
            return False

    def track_user_signup(self, user, tenant=None, signup_method='direct'):
        """
        Track user signup for conversion analytics
        Maps to: posthog.capture('user_signed_up', {
            organization_id: user.organization_id,
            signup_method: 'direct' // or 'invitation'
        })
        """
        if not user:
            return False

        try:
            # Build signup properties as per client requirements
            properties = {
                'user_id': str(user.user_id),
                'organization_id': user.tenant_id,  # tenant_id is organization_id
                'signup_method': signup_method
            }

            # Add additional signup context
            properties.update({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                'is_admin': user.is_admin,
                'signup_timestamp': datetime.utcnow().isoformat()
            })

            # Add organization name if tenant is provided
            if tenant:
                properties['organization_name'] = tenant.name

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    logger.info(f"📤 Tracking user signup for user {user.user_id} via {signup_method}")
                    
                    # Use PostHog capture with user_signed_up event
                    posthog.capture(
                        distinct_id=str(user.user_id),
                        event='user_signed_up',
                        properties=properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ User signup tracked for user {user.user_id}")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error tracking user signup: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would track signup for user {user.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in track_user_signup: {e}")
            return False

    def track_brand_voice_created(self, user, brand_voice_id, tenant=None):
        """
        Track brand voice creation as critical activation event
        Maps to: posthog.capture('brand_voice_created', {
            user_id: user.id,
            organization_id: user.organization_id,
            days_since_signup: days_elapsed,
            brand_voice_id: brand_voice.id
        })
        """
        if not user:
            return False

        try:
            # Calculate days since signup
            days_since_signup = 0
            if user.created_at:
                try:
                    from datetime import datetime
                    signup_date = datetime.fromisoformat(user.created_at.replace('Z', '+00:00'))
                    days_since_signup = (datetime.utcnow() - signup_date).days
                except Exception as e:
                    logger.warning(f"Could not calculate days since signup: {e}")
                    days_since_signup = 0

            # Build brand voice creation properties as per client requirements
            properties = {
                'user_id': str(user.user_id),
                'organization_id': user.tenant_id,  # tenant_id is organization_id
                'days_since_signup': days_since_signup,
                'brand_voice_id': str(brand_voice_id)
            }

            # Add additional context
            properties.update({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                'is_admin': user.is_admin,
                'creation_timestamp': datetime.utcnow().isoformat()
            })

            # Add organization name if tenant is provided
            if tenant:
                properties['organization_name'] = tenant.name

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    logger.info(f"📤 Tracking brand voice creation for user {user.user_id}: {days_since_signup} days since signup")
                    
                    # Use PostHog capture with brand_voice_created event
                    posthog.capture(
                        distinct_id=str(user.user_id),
                        event='brand_voice_created',
                        properties=properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ Brand voice creation tracked for user {user.user_id}")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error tracking brand voice creation: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would track brand voice creation for user {user.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in track_brand_voice_created: {e}")
            return False

    def track_first_content_generated(self, user, content_mode, tenant=None):
        """
        Track first content generation as critical activation event
        Maps to: posthog.capture('first_content_generated', {
            user_id: user.id,
            organization_id: user.organization_id,
            content_mode: mode,
            days_since_signup: days_elapsed,
            time_to_first_value_hours: hours_elapsed
        })
        """
        if not user:
            return False

        try:
            # Calculate days since signup
            days_since_signup = 0
            hours_since_signup = 0
            if user.created_at:
                try:
                    from datetime import datetime
                    signup_date = datetime.fromisoformat(user.created_at.replace('Z', '+00:00'))
                    time_diff = datetime.utcnow() - signup_date
                    days_since_signup = time_diff.days
                    hours_since_signup = time_diff.total_seconds() / 3600  # Convert to hours
                except Exception as e:
                    logger.warning(f"Could not calculate time since signup: {e}")
                    days_since_signup = 0
                    hours_since_signup = 0

            # Build first content generation properties as per client requirements
            properties = {
                'user_id': str(user.user_id),
                'organization_id': user.tenant_id,  # tenant_id is organization_id
                'content_mode': content_mode,
                'days_since_signup': days_since_signup,
                'time_to_first_value_hours': hours_since_signup
            }

            # Add additional context
            properties.update({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                'is_admin': user.is_admin,
                'generation_timestamp': datetime.utcnow().isoformat()
            })

            # Add organization name if tenant is provided
            if tenant:
                properties['organization_name'] = tenant.name

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    logger.info(f"📤 Tracking first content generation for user {user.user_id}: {days_since_signup} days, {hours_since_signup:.1f} hours since signup")
                    
                    # Use PostHog capture with first_content_generated event
                    posthog.capture(
                        distinct_id=str(user.user_id),
                        event='first_content_generated',
                        properties=properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ First content generation tracked for user {user.user_id}")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error tracking first content generation: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would track first content generation for user {user.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in track_first_content_generated: {e}")
            return False

    def track_content_generated(self, user, content_mode, tokens_used, generation_successful=True, retry_attempt=0, tenant=None):
        """
        Track content generation activity for analytics
        Maps to: posthog.capture('content_generated', {
            user_id: user.id,
            organization_id: user.organization_id,
            content_mode: mode,
            tokens_used: token_count,
            generation_successful: true/false,
            retry_attempt: attempt_number
        })
        """
        if not user:
            return False

        try:
            # Build content generation properties as per client requirements
            properties = {
                'user_id': str(user.user_id),
                'organization_id': user.tenant_id,  # tenant_id is organization_id
                'content_mode': content_mode,
                'tokens_used': tokens_used,
                'generation_successful': generation_successful,
                'retry_attempt': retry_attempt
            }

            # Add additional context
            properties.update({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                'is_admin': user.is_admin,
                'generation_timestamp': datetime.utcnow().isoformat()
            })

            # Add organization name if tenant is provided
            if tenant:
                properties['organization_name'] = tenant.name

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    status_text = "successful" if generation_successful else "failed"
                    retry_text = f" (attempt {retry_attempt})" if retry_attempt > 0 else ""
                    logger.info(f"📤 Tracking content generation for user {user.user_id}: {status_text}{retry_text}, {tokens_used} tokens")
                    
                    # Use PostHog capture with content_generated event
                    posthog.capture(
                        distinct_id=str(user.user_id),
                        event='content_generated',
                        properties=properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ Content generation tracked for user {user.user_id}")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error tracking content generation: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would track content generation for user {user.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in track_content_generated: {e}")
            return False

    def track_api_error(self, error_type, error_code=None, user=None, content_mode=None, tenant=None, additional_properties=None):
        """
        Track API errors for monitoring external service failures
        Maps to: posthog.capture('api_error', {
            error_type: 'gemini_api_failure',
            error_code: response.status_code,
            user_id: user.id,
            organization_id: user.organization_id,
            content_mode: attempted_mode
        })
        """
        try:
            # Build API error properties as per client requirements
            properties = {
                'error_type': error_type,
                'error_code': error_code
            }

            # Add user context if available
            if user:
                properties.update({
                    'user_id': str(user.user_id),
                    'organization_id': user.tenant_id,  # tenant_id is organization_id
                    'email': user.email,
                    'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                    'is_admin': user.is_admin
                })

            # Add content mode if provided
            if content_mode:
                properties['content_mode'] = content_mode

            # Add organization name if tenant is provided
            if tenant:
                properties['organization_name'] = tenant.name

            # Add additional properties if provided
            if additional_properties:
                properties.update(additional_properties)

            # Add timestamp
            properties['error_timestamp'] = datetime.utcnow().isoformat()

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    distinct_id = str(user.user_id) if user else 'anonymous'
                    logger.info(f"📤 Tracking API error: {error_type} (code: {error_code}) for user {distinct_id}")
                    
                    # Use PostHog capture with api_error event
                    posthog.capture(
                        distinct_id=distinct_id,
                        event='api_error',
                        properties=properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ API error tracked: {error_type}")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error tracking API error: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would track API error: {error_type}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in track_api_error: {e}")
            return False

    def track_application_error(self, error_type, error_message, user=None, additional_properties=None):
        """
        Track application errors for monitoring internal system failures
        Maps to: posthog.capture('application_error', {
            error_type: 'database_connection',
            error_message: error.message,
            user_id: user.id if available else None
        })
        """
        try:
            # Build application error properties as per client requirements
            properties = {
                'error_type': error_type,
                'error_message': error_message
            }

            # Add user context if available
            if user:
                properties.update({
                    'user_id': str(user.user_id),
                    'organization_id': user.tenant_id,  # tenant_id is organization_id
                    'email': user.email,
                    'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                    'is_admin': user.is_admin
                })

            # Add additional properties if provided
            if additional_properties:
                properties.update(additional_properties)

            # Add timestamp
            properties['error_timestamp'] = datetime.utcnow().isoformat()

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    distinct_id = str(user.user_id) if user else 'anonymous'
                    logger.info(f"📤 Tracking application error: {error_type} for user {distinct_id}")
                    
                    # Use PostHog capture with application_error event
                    posthog.capture(
                        distinct_id=distinct_id,
                        event='application_error',
                        properties=properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ Application error tracked: {error_type}")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error tracking application error: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would track application error: {error_type}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in track_application_error: {e}")
            return False

    def track_page_load(self, page_name, load_time_ms, user=None, tenant=None):
        """
        Track page load times for performance monitoring
        Maps to: posthog.capture('page_load', {
            page_name: 'dashboard',
            load_time_ms: performance.now(),
            user_id: user.id,
            organization_id: user.organization_id
        })
        """
        try:
            # Build page load properties as per client requirements
            properties = {
                'page_name': page_name,
                'load_time_ms': load_time_ms
            }

            # Add user context if available
            if user:
                properties.update({
                    'user_id': str(user.user_id),
                    'organization_id': user.tenant_id,  # tenant_id is organization_id
                    'email': user.email,
                    'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                    'is_admin': user.is_admin
                })

            # Add organization name if tenant is provided
            if tenant:
                properties['organization_name'] = tenant.name

            # Add timestamp
            properties['load_timestamp'] = datetime.utcnow().isoformat()

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    distinct_id = str(user.user_id) if user else 'anonymous'
                    logger.info(f"📤 Tracking page load: {page_name} ({load_time_ms}ms) for user {distinct_id}")
                    
                    # Use PostHog capture with page_load event
                    posthog.capture(
                        distinct_id=distinct_id,
                        event='page_load',
                        properties=properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ Page load tracked: {page_name}")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error tracking page load: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would track page load: {page_name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in track_page_load: {e}")
            return False

    def track_content_generation_performance(self, user, content_mode, response_time_ms, tokens_generated, tenant=None):
        """
        Track content generation response times for performance monitoring
        Maps to: posthog.capture('content_generation_performance', {
            user_id: user.id,
            organization_id: user.organization_id,
            content_mode: mode,
            response_time_ms: generation_time,
            tokens_generated: token_count
        })
        """
        if not user:
            return False

        try:
            # Build content generation performance properties as per client requirements
            properties = {
                'user_id': str(user.user_id),
                'organization_id': user.tenant_id,  # tenant_id is organization_id
                'content_mode': content_mode,
                'response_time_ms': response_time_ms,
                'tokens_generated': tokens_generated
            }

            # Add additional context
            properties.update({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                'is_admin': user.is_admin,
                'performance_timestamp': datetime.utcnow().isoformat()
            })

            # Add organization name if tenant is provided
            if tenant:
                properties['organization_name'] = tenant.name

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    logger.info(f"📤 Tracking content generation performance for user {user.user_id}: {response_time_ms}ms, {tokens_generated} tokens")
                    
                    # Use PostHog capture with content_generation_performance event
                    posthog.capture(
                        distinct_id=str(user.user_id),
                        event='content_generation_performance',
                        properties=properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ Content generation performance tracked for user {user.user_id}")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error tracking content generation performance: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would track content generation performance for user {user.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in track_content_generation_performance: {e}")
            return False

    def track_user_return(self, user, days_since_last_visit, session_number, tenant=None):
        """
        Track user return visits for retention analysis
        Maps to: posthog.capture('user_return', {
            user_id: user.id,
            organization_id: user.organization_id,
            days_since_last_visit: days_elapsed,
            session_number: user.session_count
        })
        """
        if not user:
            return False

        try:
            # Build user return properties as per client requirements
            properties = {
                'user_id': str(user.user_id),
                'organization_id': user.tenant_id,  # tenant_id is organization_id
                'days_since_last_visit': days_since_last_visit,
                'session_number': session_number
            }

            # Add additional context
            properties.update({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                'is_admin': user.is_admin,
                'return_timestamp': datetime.utcnow().isoformat()
            })

            # Add organization name if tenant is provided
            if tenant:
                properties['organization_name'] = tenant.name

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    logger.info(f"📤 Tracking user return for user {user.user_id}: {days_since_last_visit} days since last visit, session #{session_number}")
                    
                    # Use PostHog capture with user_return event
                    posthog.capture(
                        distinct_id=str(user.user_id),
                        event='user_return',
                        properties=properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ User return tracked for user {user.user_id}")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error tracking user return: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would track user return for user {user.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in track_user_return: {e}")
            return False

    def track_content_mode_used(self, user, content_mode, is_first_time_using_mode, total_modes_used_by_user, tenant=None):
        """
        Track content mode usage for feature adoption analytics
        Maps to: posthog.capture('content_mode_used', {
            user_id: user.id,
            organization_id: user.organization_id,
            content_mode: mode,
            is_first_time_using_mode: boolean,
            total_modes_used_by_user: count
        })
        """
        if not user:
            return False

        try:
            # Build content mode usage properties as per client requirements
            properties = {
                'user_id': str(user.user_id),
                'organization_id': user.tenant_id,  # tenant_id is organization_id
                'content_mode': content_mode,
                'is_first_time_using_mode': is_first_time_using_mode,
                'total_modes_used_by_user': total_modes_used_by_user
            }

            # Add additional context
            properties.update({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                'is_admin': user.is_admin,
                'usage_timestamp': datetime.utcnow().isoformat()
            })

            # Add organization name if tenant is provided
            if tenant:
                properties['organization_name'] = tenant.name

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    first_time_text = "first time" if is_first_time_using_mode else "repeat"
                    logger.info(f"📤 Tracking content mode usage for user {user.user_id}: {content_mode} ({first_time_text}), total modes: {total_modes_used_by_user}")
                    
                    # Use PostHog capture with content_mode_used event
                    posthog.capture(
                        distinct_id=str(user.user_id),
                        event='content_mode_used',
                        properties=properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ Content mode usage tracked for user {user.user_id}")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error tracking content mode usage: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would track content mode usage for user {user.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in track_content_mode_used: {e}")
            return False

    def identify_user_with_org(self, user, tenant=None):
        """
        Identify users with organization details as per client requirements
        Uses PostHog capture with $identify event for compatibility
        Maps to: posthog.capture(user.id, '$identify', {
            'email': user.email,
            'organization_id': user.organization_id,
            'organization_name': user.organization.name,
            'signup_date': user.created_at,
            'user_role_in_app': user.role
        })
        """
        if not user:
            return False

        try:
            # Build user properties with organization context
            user_properties = {
                'email': user.email,
                'organization_id': user.tenant_id,  # tenant_id is organization_id
                'signup_date': user.created_at,
                'user_role_in_app': 'admin' if user.is_admin else 'member'
            }

            # Add organization name if tenant is provided
            if tenant:
                user_properties['organization_name'] = tenant.name
            
            # Add additional user context
            user_properties.update({
                'first_name': user.first_name,
                'last_name': user.last_name,
                'subscription_level': user.subscription_level.value if hasattr(user.subscription_level, 'value') else str(user.subscription_level),
                'email_verified': user.email_verified,
                'last_login': user.last_login
            })

            if self.posthog_client and self.posthog_key:
                try:
                    import posthog
                    
                    logger.info(f"📤 Identifying user {user.user_id} with organization details")
                    
                    posthog.capture(
                        distinct_id=str(user.user_id),
                        event='$identify',
                        properties=user_properties
                    )
                    
                    posthog.flush()
                    time.sleep(0.1)
                    
                    logger.info(f"✅ User {user.user_id} identified with organization context")
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Error identifying user in PostHog: {e}")
                    return False
            else:
                logger.warning(f"⚠️ PostHog not configured - would identify user {user.user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in identify_user_with_org: {e}")
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
def track_all_requests(app):
    """Add this to your Flask app to automatically track all requests"""

    @app.before_request
    def before_request():
        # Skip tracking for static files and API endpoints
        if not request.path.startswith(
                '/static') and not request.path.startswith('/api'):
            # Track page view for every request
            analytics_service.track_page_view()

    return before_request
