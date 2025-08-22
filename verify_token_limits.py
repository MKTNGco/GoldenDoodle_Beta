
#!/usr/bin/env python3
"""
Script to verify token limits by account type
"""

from database import db_manager
from models import SubscriptionLevel

def verify_token_limits():
    """Verify token limits for each subscription level"""
    print("=== Token Limits Verification ===\n")
    
    # Get all pricing plans
    plans = db_manager.get_all_pricing_plans()
    
    if not plans:
        print("No pricing plans found. Populating defaults...")
        db_manager.populate_pricing_plans()
        plans = db_manager.get_all_pricing_plans()
    
    print("Current Token Limits by Plan:")
    print("-" * 50)
    
    for plan in plans:
        plan_name = plan['name']
        token_limit = plan['token_limit']
        
        if token_limit == -1:
            limit_display = "Unlimited"
        else:
            limit_display = f"{token_limit:,} tokens/month"
        
        print(f"{plan_name:12} | {limit_display}")
    
    print("\n=== Testing Token Limit Enforcement ===\n")
    
    # Test with a mock user ID (you can replace with a real user ID)
    test_user_id = "test-user-123"
    
    # Test scenarios
    test_scenarios = [
        (1000, "Small request"),
        (50000, "Medium request"), 
        (200000, "Large request"),
        (1500000, "Excessive request")
    ]
    
    for estimated_tokens, description in test_scenarios:
        print(f"Testing {description} ({estimated_tokens:,} tokens):")
        
        # This would normally check against actual user limits
        # For testing, we'll just show what would happen for each plan
        for plan in plans:
            plan_name = plan['name']
            token_limit = plan['token_limit']
            
            if token_limit == -1:
                status = "✓ Allowed (unlimited)"
            elif estimated_tokens <= token_limit:
                status = "✓ Allowed"
            else:
                status = "✗ Blocked (exceeds limit)"
            
            print(f"  {plan_name:12} | {status}")
        print()

def check_specific_user_limits(user_id: str):
    """Check limits for a specific user"""
    print(f"\n=== Checking limits for user: {user_id} ===")
    
    # Get user's current plan
    plan = db_manager.get_user_plan(user_id)
    if not plan:
        print("User plan not found")
        return
    
    # Get user's current usage
    usage = db_manager.get_user_token_usage(user_id)
    if not usage:
        print("User usage data not found")
        return
    
    plan_name = plan.get('plan_name', 'Unknown')
    token_limit = plan.get('token_limit', 0)
    current_usage = usage.get('tokens_used_month', 0)
    total_usage = usage.get('tokens_used_total', 0)
    
    print(f"Plan: {plan_name}")
    
    if token_limit == -1:
        print(f"Monthly Limit: Unlimited")
        print(f"Current Usage: {current_usage:,} tokens")
        print(f"Total Usage: {total_usage:,} tokens")
        print("Status: ✓ No limits")
    else:
        remaining = max(0, token_limit - current_usage)
        percentage_used = (current_usage / token_limit * 100) if token_limit > 0 else 0
        
        print(f"Monthly Limit: {token_limit:,} tokens")
        print(f"Current Usage: {current_usage:,} tokens ({percentage_used:.1f}%)")
        print(f"Remaining: {remaining:,} tokens")
        print(f"Total Usage: {total_usage:,} tokens")
        
        if current_usage >= token_limit:
            print("Status: ✗ Monthly limit exceeded")
        elif current_usage >= token_limit * 0.9:
            print("Status: ⚠ Approaching limit (90%+)")
        else:
            print("Status: ✓ Within limits")

if __name__ == "__main__":
    verify_token_limits()
    
    # Example: Check specific user (uncomment and provide real user ID)
    # check_specific_user_limits("your-user-id-here")
