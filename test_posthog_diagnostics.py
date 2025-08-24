
#!/usr/bin/env python3

import os
import sys
import logging
from datetime import datetime
import traceback

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_environment_variables():
    """Test PostHog environment variables"""
    print("🔍 TESTING ENVIRONMENT VARIABLES")
    print("=" * 50)
    
    posthog_api_key = os.environ.get("POSTHOG_API_KEY")
    posthog_host = os.environ.get("POSTHOG_HOST", "https://app.posthog.com")
    
    print(f"POSTHOG_API_KEY: {'✅ Set' if posthog_api_key else '❌ Not Set'}")
    if posthog_api_key:
        print(f"API Key (first 8 chars): {posthog_api_key[:8]}...")
    print(f"POSTHOG_HOST: {posthog_host}")
    
    return bool(posthog_api_key)

def test_posthog_import():
    """Test PostHog library import"""
    print("\n🔍 TESTING POSTHOG LIBRARY IMPORT")
    print("=" * 50)
    
    try:
        import posthog
        print("✅ PostHog library imported successfully")
        print(f"PostHog version: {getattr(posthog, '__version__', 'Unknown')}")
        return True
    except ImportError as e:
        print(f"❌ PostHog library import failed: {e}")
        print("💡 Run: pip install posthog")
        return False
    except Exception as e:
        print(f"❌ Unexpected error importing PostHog: {e}")
        return False

def test_analytics_service():
    """Test the analytics service initialization"""
    print("\n🔍 TESTING ANALYTICS SERVICE")
    print("=" * 50)
    
    try:
        from analytics_service import analytics_service
        
        print(f"PostHog Key Available: {'✅ Yes' if analytics_service.posthog_key else '❌ No'}")
        print(f"PostHog Client: {'✅ Initialized' if analytics_service.posthog_client else '❌ Not Initialized'}")
        print(f"PostHog Host: {analytics_service.posthog_host}")
        
        return analytics_service.posthog_client is not None
    except Exception as e:
        print(f"❌ Analytics service test failed: {e}")
        traceback.print_exc()
        return False

def test_event_tracking():
    """Test actual event tracking"""
    print("\n🔍 TESTING EVENT TRACKING")
    print("=" * 50)
    
    try:
        from analytics_service import analytics_service
        
        # Test event
        test_user_id = f"test_user_{datetime.now().timestamp()}"
        test_event = "Diagnostics Test Event"
        test_properties = {
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "source": "diagnostics_script"
        }
        
        print(f"Attempting to track event: {test_event}")
        print(f"User ID: {test_user_id}")
        print(f"Properties: {test_properties}")
        
        result = analytics_service.track_user_event(
            user_id=test_user_id,
            event_name=test_event,
            properties=test_properties
        )
        
        print(f"Event tracking result: {'✅ Success' if result else '❌ Failed'}")
        
        # Test user identification
        print("\nTesting user identification...")
        user_props = {
            "email": "test@example.com",
            "plan": "diagnostics_test"
        }
        
        identify_result = analytics_service.identify_user(
            user_id=test_user_id,
            user_properties=user_props
        )
        
        print(f"User identification result: {'✅ Success' if identify_result else '❌ Failed'}")
        
        # Flush events
        analytics_service.flush()
        print("✅ Events flushed")
        
        return result and identify_result
        
    except Exception as e:
        print(f"❌ Event tracking test failed: {e}")
        traceback.print_exc()
        return False

def test_posthog_direct():
    """Test PostHog directly without our service wrapper"""
    print("\n🔍 TESTING POSTHOG DIRECTLY")
    print("=" * 50)
    
    try:
        import posthog
        
        api_key = os.environ.get("POSTHOG_API_KEY")
        if not api_key:
            print("❌ No API key available for direct test")
            return False
        
        # Configure PostHog directly
        posthog.api_key = api_key
        posthog.host = os.environ.get("POSTHOG_HOST", "https://app.posthog.com")
        
        # Test direct capture
        test_user_id = f"direct_test_{datetime.now().timestamp()}"
        
        posthog.capture(
            distinct_id=test_user_id,
            event="Direct PostHog Test",
            properties={
                "test_type": "direct",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        print("✅ Direct PostHog capture sent")
        
        # Flush
        posthog.flush()
        print("✅ Direct PostHog events flushed")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct PostHog test failed: {e}")
        traceback.print_exc()
        return False

def test_web_endpoint():
    """Test the web endpoint for PostHog"""
    print("\n🔍 TESTING WEB ENDPOINT")
    print("=" * 50)
    
    try:
        import requests
        
        # Test the test-posthog endpoint
        response = requests.get("http://localhost:5000/test-posthog")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Web endpoint accessible")
            print(f"Response: {data}")
            return True
        else:
            print(f"❌ Web endpoint returned {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Web endpoint test failed: {e}")
        return False

def main():
    """Run all PostHog diagnostics"""
    print("🚀 POSTHOG ANALYTICS DIAGNOSTICS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    results = {
        "environment": test_environment_variables(),
        "import": test_posthog_import(),
        "service": test_analytics_service(),
        "tracking": test_event_tracking(),
        "direct": test_posthog_direct(),
        "web": test_web_endpoint()
    }
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.upper():15} {status}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    print(f"\nOVERALL: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("🎉 All PostHog tests passed!")
    else:
        print("⚠️  Some PostHog tests failed. Check the output above for details.")
        
    print("\n💡 NEXT STEPS:")
    if not results["environment"]:
        print("- Add POSTHOG_API_KEY to your environment variables")
    if not results["import"]:
        print("- Install PostHog: pip install posthog")
    if not results["service"]:
        print("- Check analytics_service.py configuration")
    if not results["tracking"]:
        print("- Debug event tracking implementation")

if __name__ == "__main__":
    main()
