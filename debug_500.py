
#!/usr/bin/env python3

import sys
import traceback

def test_imports():
    """Test if all modules can be imported"""
    try:
        from app import app
        from database import db_manager
        from auth import get_current_user
        from routes import *
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        traceback.print_exc()
        return False

def test_database():
    """Test database connection"""
    try:
        from database import db_manager
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_env_vars():
    """Check critical environment variables"""
    import os
    
    required_vars = [
        'DATABASE_URL',
        'GEMINI_API_KEY',
        'SESSION_SECRET'
    ]
    
    missing = []
    for var in required_vars:
        if not os.environ.get(var):
            missing.append(var)
    
    if missing:
        print(f"❌ Missing environment variables: {missing}")
        return False
    else:
        print("✓ Required environment variables present")
        return True

def main():
    print("🔍 GoldenDoodleLM 500 Error Diagnosis")
    print("=" * 50)
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("Environment", test_env_vars()))
    results.append(("Database", test_database()))
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    for test_name, success in results:
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"{test_name:15} {status}")
    
    if all(result[1] for result in results):
        print("\n✓ Basic tests passed. Check console logs for route-specific errors.")
    else:
        print("\n❌ Found issues. Fix the failed tests above.")

if __name__ == "__main__":
    main()
