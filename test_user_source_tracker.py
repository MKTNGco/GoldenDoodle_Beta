
#!/usr/bin/env python3
"""
Test script for the UserSourceTracker class.
Run this to see how the user source tracking works.
"""

from user_source_tracker import user_source_tracker

def test_user_source_tracking():
    print("=== Testing User Source Tracker ===\n")

    # Test 1: Track organic signup
    print("1. Tracking organic signup...")
    success = user_source_tracker.track_user_signup("user1@example.com", "organic")
    print(f"Organic signup tracked: {success}\n")

    # Test 2: Track invitation signup
    print("2. Tracking invitation signup...")
    success = user_source_tracker.track_user_signup("user2@example.com", "invitation_beta", "BETAZTRD")
    print(f"Invitation signup tracked: {success}\n")

    # Test 3: Track referral signup
    print("3. Tracking referral signup...")
    success = user_source_tracker.track_user_signup("user3@example.com", "referral", "REF123")
    print(f"Referral signup tracked: {success}\n")

    # Test 4: Track paid signup
    print("4. Tracking paid signup...")
    success = user_source_tracker.track_user_signup("user4@example.com", "paid_solo")
    print(f"Paid signup tracked: {success}\n")

    # Test 5: Get user source
    print("5. Looking up user source...")
    source = user_source_tracker.get_user_source("user2@example.com")
    print(f"User source: {source}\n")

    # Test 6: Get signup statistics
    print("6. Getting signup statistics...")
    stats = user_source_tracker.get_signup_stats()
    print(f"Signup stats: {stats}\n")

    # Test 7: Get invite code usage
    print("7. Getting invite code usage...")
    invite_usage = user_source_tracker.get_invite_code_usage("BETAZTRD")
    print(f"BETAZTRD usage: {invite_usage}\n")

    # Test 8: Get all sources
    print("8. Getting all tracked sources...")
    all_sources = user_source_tracker.get_all_sources()
    print(f"Total tracked signups: {len(all_sources)}")
    for source in all_sources:
        print(f"  - {source['user_email']}: {source['signup_source']} ({source['signup_date'][:10]})")

if __name__ == "__main__":
    test_user_source_tracking()
