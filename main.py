from app import app

if __name__ == '__main__':
    # Ensure all database tables exist on startup
    from database import db_manager
    try:
        db_manager.ensure_chat_tables_exist()
        print("✓ Chat tables verified/created")
    except Exception as e:
        print(f"⚠️  Warning: Could not ensure chat tables exist: {e}")
    
    # Bind to 0.0.0.0 to make accessible on Replit
    app.run(host='0.0.0.0', port=5000, debug=True)
