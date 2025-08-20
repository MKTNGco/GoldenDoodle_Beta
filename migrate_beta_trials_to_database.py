
#!/usr/bin/env python3

import json
import logging
from datetime import datetime
from database import DatabaseManager
import psycopg2.extras

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_beta_trials():
    """Migrate beta trials from JSON file to PostgreSQL database"""
    
    db = DatabaseManager()
    
    try:
        # Load existing beta trials from JSON
        with open('beta_trials.json', 'r') as f:
            trials_data = json.load(f)
        
        logger.info(f"Found {len(trials_data)} beta trials in JSON file")
        
        if not trials_data:
            logger.info("No beta trials to migrate")
            return True
        
        conn = db.get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # Check if any data already exists
        cursor.execute("SELECT COUNT(*) as count FROM beta_trials")
        existing_count = cursor.fetchone()['count']
        
        if existing_count > 0:
            logger.info(f"Database already contains {existing_count} beta trials")
            response = input("Do you want to continue and add JSON data? (y/N): ").lower()
            if response != 'y':
                logger.info("Migration cancelled")
                return False
        
        # Insert beta trials from JSON
        migrated_count = 0
        skipped_count = 0
        
        for trial in trials_data:
            try:
                # Check if trial already exists (by user_email and trial_start)
                cursor.execute("""
                    SELECT id FROM beta_trials 
                    WHERE user_email = %s AND trial_start = %s
                """, (trial['user_email'], trial['trial_start']))
                
                if cursor.fetchone():
                    logger.info(f"Trial for {trial['user_email']} already exists, skipping")
                    skipped_count += 1
                    continue
                
                # Insert the trial
                cursor.execute("""
                    INSERT INTO beta_trials 
                    (user_id, user_email, invite_code, trial_start, trial_end, 
                     trial_days, trial_type, status, created_at, expired_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    trial['user_id'],
                    trial['user_email'],
                    trial.get('invite_code'),
                    trial['trial_start'],
                    trial['trial_end'],
                    trial['trial_days'],
                    trial['trial_type'],
                    trial['status'],
                    trial['created_at'],
                    trial.get('expired_at')
                ))
                
                migrated_count += 1
                logger.info(f"Migrated trial for {trial['user_email']}")
                
            except Exception as e:
                logger.error(f"Error migrating trial for {trial.get('user_email', 'unknown')}: {e}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"✅ Migration completed: {migrated_count} trials migrated, {skipped_count} skipped")
        
        # Create backup of JSON file
        backup_filename = f"beta_trials.json.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        with open(backup_filename, 'w') as f:
            json.dump(trials_data, f, indent=2)
        logger.info(f"📁 Backup created: {backup_filename}")
        
        return True
        
    except FileNotFoundError:
        logger.info("No beta_trials.json file found - nothing to migrate")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_beta_trials()
    if success:
        print("\n🎉 Beta trials migration completed successfully!")
    else:
        print("\n❌ Beta trials migration failed!")
