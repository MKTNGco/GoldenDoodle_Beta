
#!/usr/bin/env python3
"""
Script to list all registered users and their email addresses
"""
from database import db_manager
from tabulate import tabulate

def list_all_users():
    """Fetch and display all registered users"""
    try:
        # Get all users from database
        users_data = db_manager.get_all_users()
        
        if not users_data:
            print("No users found in the database.")
            return
        
        # Prepare data for display
        user_list = []
        for user, tenant_name, tenant_type in users_data:
            user_list.append({
                'Name': f"{user.first_name} {user.last_name}",
                'Email': user.email,
                'Organization': tenant_name,
                'Type': tenant_type,
                'Subscription': user.subscription_level.value,
                'Admin': 'Yes' if user.is_admin else 'No',
                'Verified': 'Yes' if user.email_verified else 'No',
                'Created': user.created_at[:10] if user.created_at else 'N/A'
            })
        
        # Display as table
        print(f"\nTotal Users: {len(user_list)}\n")
        print(tabulate(user_list, headers='keys', tablefmt='grid'))
        
        # Also print just emails for easy copying
        print("\n\nEmail List (copy-friendly):")
        print("-" * 50)
        for user_data in user_list:
            print(user_data['Email'])
        
        return user_list
        
    except Exception as e:
        print(f"Error fetching users: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    list_all_users()
