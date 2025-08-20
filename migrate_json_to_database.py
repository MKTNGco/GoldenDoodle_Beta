
#!/usr/bin/env python3
"""
Migration script to move invitation and user source data from JSON files to database tables.
Run this script to migrate your data safely with rollback capability.
"""

import json
import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from database import DatabaseManager
import psycopg2.extras

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MigrationManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.backup_created = False
        
    def create_backup_tables(self):
        """Create backup tables before migration"""
        try:
            logger.info("Creating backup tables...")
            
            # Create backup tables with timestamp suffix
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            backup_queries = [
                f"""
                CREATE TABLE IF NOT EXISTS invitations_backup_{timestamp} AS 
                SELECT * FROM invitations WHERE 1=0;
                """,
                f"""
                CREATE TABLE IF NOT EXISTS user_sources_backup_{timestamp} AS 
                SELECT * FROM user_sources WHERE 1=0;
                """
            ]
            
            for query in backup_queries:
                self.db.execute_query(query)
            
            self.backup_timestamp = timestamp
            self.backup_created = True
            logger.info(f"Backup tables created with timestamp: {timestamp}")
            
        except Exception as e:
            logger.error(f"Failed to create backup tables: {e}")
            raise
    
    def backup_existing_data(self):
        """Backup any existing data in the tables"""
        if not self.backup_created:
            self.create_backup_tables()
            
        try:
            logger.info("Backing up existing data...")
            
            # Backup existing invitations
            backup_invitations_query = f"""
            INSERT INTO invitations_backup_{self.backup_timestamp}
            SELECT * FROM invitations;
            """
            
            # Backup existing user sources
            backup_sources_query = f"""
            INSERT INTO user_sources_backup_{self.backup_timestamp}
            SELECT * FROM user_sources;
            """
            
            self.db.execute_query(backup_invitations_query)
            self.db.execute_query(backup_sources_query)
            
            logger.info("Existing data backed up successfully")
            
        except Exception as e:
            logger.error(f"Failed to backup existing data: {e}")
            # Don't raise here as tables might be empty
    
    def load_json_data(self, file_path: str) -> List[Dict]:
        """Load data from JSON file"""
        if not os.path.exists(file_path):
            logger.warning(f"JSON file not found: {file_path}")
            return []
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data)} records from {file_path}")
                return data
        except Exception as e:
            logger.error(f"Failed to load JSON file {file_path}: {e}")
            return []
    
    def migrate_invitations(self):
        """Migrate invitations from JSON to database"""
        logger.info("Starting invitations migration...")
        
        invitations_data = self.load_json_data('invitations.json')
        if not invitations_data:
            logger.info("No invitations data to migrate")
            return
        
        try:
            # Clear existing data
            self.db.execute_query("DELETE FROM invitations")
            
            # Insert JSON data
            for invitation in invitations_data:
                query = """
                INSERT INTO invitations (
                    invite_code, invitee_email, organization_name, 
                    invitation_type, status, created_at, accepted_at, expired_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                params = (
                    invitation['invite_code'],
                    invitation['invitee_email'],
                    invitation['organization_name'],
                    invitation['invitation_type'],
                    invitation['status'],
                    invitation['created_at'],
                    invitation.get('accepted_at'),
                    invitation.get('expired_at')
                )
                
                self.db.execute_query(query, params)
            
            logger.info(f"Successfully migrated {len(invitations_data)} invitations")
            
        except Exception as e:
            logger.error(f"Failed to migrate invitations: {e}")
            raise
    
    def migrate_user_sources(self):
        """Migrate user sources from JSON to database"""
        logger.info("Starting user sources migration...")
        
        sources_data = self.load_json_data('user_sources.json')
        if not sources_data:
            logger.info("No user sources data to migrate")
            return
        
        try:
            # Clear existing data
            self.db.execute_query("DELETE FROM user_sources")
            
            # Insert JSON data
            for source in sources_data:
                query = """
                INSERT INTO user_sources (
                    user_email, signup_source, invite_code, 
                    signup_date, tracked_at
                ) VALUES (%s, %s, %s, %s, %s)
                """
                
                params = (
                    source['user_email'],
                    source['signup_source'],
                    source.get('invite_code'),
                    source['signup_date'],
                    source['tracked_at']
                )
                
                self.db.execute_query(query, params)
            
            logger.info(f"Successfully migrated {len(sources_data)} user sources")
            
        except Exception as e:
            logger.error(f"Failed to migrate user sources: {e}")
            raise
    
    def create_json_backups(self):
        """Create timestamped backups of JSON files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        json_files = ['invitations.json', 'user_sources.json']
        
        for json_file in json_files:
            if os.path.exists(json_file):
                backup_name = f"{json_file}.backup_{timestamp}"
                os.rename(json_file, backup_name)
                logger.info(f"Created JSON backup: {backup_name}")
    
    def verify_migration(self):
        """Verify that migration was successful"""
        logger.info("Verifying migration...")
        
        try:
            # Count records in database
            conn = self.db.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("SELECT COUNT(*) as count FROM invitations")
            inv_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM user_sources")
            src_count = cursor.fetchone()['count']
            
            cursor.close()
            conn.close()
            
            logger.info(f"Database contains {inv_count} invitations and {src_count} user sources")
            
            # Verify some sample data
            sample_invitation = self.db.execute_query("SELECT * FROM invitations LIMIT 1")
            sample_source = self.db.execute_query("SELECT * FROM user_sources LIMIT 1")
            
            if sample_invitation:
                logger.info(f"Sample invitation: {sample_invitation[0]['invite_code']}")
            if sample_source:
                logger.info(f"Sample user source: {sample_source[0]['user_email']}")
            
            logger.info("Migration verification completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration verification failed: {e}")
            return False
    
    def rollback(self):
        """Rollback migration by restoring from backup tables"""
        if not self.backup_created:
            logger.error("No backup tables found for rollback")
            return False
        
        try:
            logger.info(f"Rolling back migration using backup_{self.backup_timestamp}...")
            
            # Clear current data
            self.db.execute_query("DELETE FROM user_sources")
            self.db.execute_query("DELETE FROM invitations")
            
            # Restore from backup
            restore_queries = [
                f"""
                INSERT INTO invitations 
                SELECT * FROM invitations_backup_{self.backup_timestamp}
                """,
                f"""
                INSERT INTO user_sources 
                SELECT * FROM user_sources_backup_{self.backup_timestamp}
                """
            ]
            
            for query in restore_queries:
                self.db.execute_query(query)
            
            logger.info("Rollback completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

def run_migration():
    """Run the complete migration process"""
    migration = MigrationManager()
    
    try:
        logger.info("=== Starting Migration Process ===")
        
        # Step 1: Create and run table creation script
        logger.info("Step 1: Creating database tables...")
        with open('create_invitation_tables.sql', 'r') as f:
            sql_script = f.read()
        
        # Execute the SQL script
        migration.db.execute_script(sql_script)
        logger.info("Database tables created successfully")
        
        # Step 2: Create backups
        logger.info("Step 2: Creating backups...")
        migration.create_backup_tables()
        migration.backup_existing_data()
        migration.create_json_backups()
        
        # Step 3: Migrate data
        logger.info("Step 3: Migrating data...")
        migration.migrate_invitations()
        migration.migrate_user_sources()
        
        # Step 4: Verify migration
        logger.info("Step 4: Verifying migration...")
        if migration.verify_migration():
            logger.info("=== Migration completed successfully! ===")
            logger.info(f"Backup tables created: invitations_backup_{migration.backup_timestamp}, user_sources_backup_{migration.backup_timestamp}")
            logger.info("JSON files have been backed up with timestamp suffix")
            return True
        else:
            logger.error("Migration verification failed")
            return False
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        logger.info("Attempting rollback...")
        migration.rollback()
        return False

def rollback_migration():
    """Rollback the migration"""
    migration = MigrationManager()
    
    # Find the most recent backup
    try:
        backups = migration.db.execute_query("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_name LIKE 'invitations_backup_%' 
        ORDER BY table_name DESC LIMIT 1
        """)
        
        if not backups:
            logger.error("No backup tables found for rollback")
            return False
        
        # Extract timestamp from backup table name
        backup_table = backups[0]['table_name']
        timestamp = backup_table.split('_')[-2] + '_' + backup_table.split('_')[-1]
        migration.backup_timestamp = timestamp
        migration.backup_created = True
        
        return migration.rollback()
        
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
        print("Rolling back migration...")
        success = rollback_migration()
        sys.exit(0 if success else 1)
    else:
        print("Starting migration...")
        success = run_migration()
        if success:
            print("\nMigration completed! You can now update your code to use the database.")
            print("To rollback if needed, run: python migrate_json_to_database.py rollback")
        sys.exit(0 if success else 1)
