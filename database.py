import os
import psycopg2
import psycopg2.extras
import uuid
import json
import logging
from typing import Optional, List, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash
from models import Tenant, User, BrandVoice, TenantType, SubscriptionLevel

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.main_db_url = os.environ.get("DATABASE_URL")
        if not self.main_db_url:
            raise ValueError("DATABASE_URL environment variable is required")

    def get_connection(self, database_url: Optional[str] = None):
        """Get a database connection"""
        url = database_url or self.main_db_url
        return psycopg2.connect(url)

    def init_main_database(self):
        """Initialize the main control plane database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Create enums
            cursor.execute("""
                DO $$ BEGIN
                    CREATE TYPE tenant_type AS ENUM ('company', 'independent_user');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)

            cursor.execute("""
                DO $$ BEGIN
                    CREATE TYPE subscription_level AS ENUM ('solo', 'pro', 'team', 'enterprise');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)

            # Create tenants table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    tenant_id UUID PRIMARY KEY,
                    tenant_type tenant_type NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    database_name VARCHAR(255) NOT NULL UNIQUE,
                    max_brand_voices INTEGER NOT NULL DEFAULT 3,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id UUID PRIMARY KEY,
                    tenant_id UUID NOT NULL,
                    first_name VARCHAR(255) NOT NULL,
                    last_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    subscription_level subscription_level NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    email_verified BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Add email_verified column if it doesn't exist (for existing databases)
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'email_verified'
                    ) THEN
                        ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT FALSE;
                    END IF;
                END $$;
            """)

            # Add last_login column if it doesn't exist
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'last_login'
                    ) THEN
                        ALTER TABLE users ADD COLUMN last_login TIMESTAMP NULL;
                    END IF;
                END $$;
            """)

            # Create email verification tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_verification_tokens (
                    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    token_hash VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
            """)

            # Create password reset tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL,
                    token_hash VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
            """)

            # Organization invite tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS organization_invite_tokens (
                    invite_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL,
                    invited_by_user_id UUID NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    token_hash VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    used BOOLEAN DEFAULT FALSE
                );
            """)

            # Create indexes separately
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_organization_invite_token_hash 
                ON organization_invite_tokens(token_hash);
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_organization_invite_email 
                ON organization_invite_tokens(email);
            """)

            # Migration: Fix organization_invite_tokens table structure
            cursor.execute("""
                DO $$ 
                BEGIN
                    -- Check if used_at column exists and used column doesn't
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'organization_invite_tokens' AND column_name = 'used_at'
                    ) AND NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'organization_invite_tokens' AND column_name = 'used'
                    ) THEN
                        -- Add used column
                        ALTER TABLE organization_invite_tokens ADD COLUMN used BOOLEAN DEFAULT FALSE;
                        -- Migrate data: set used = TRUE where used_at IS NOT NULL
                        UPDATE organization_invite_tokens SET used = TRUE WHERE used_at IS NOT NULL;
                        -- Drop the old column
                        ALTER TABLE organization_invite_tokens DROP COLUMN used_at;
                    END IF;
                END $$;
            """)

            # Create message_type enum for PostgreSQL
            cursor.execute("""
                DO $$ BEGIN
                    CREATE TYPE message_type AS ENUM ('user', 'assistant');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)

            # Create pricing plans table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pricing_plans (
                    plan_id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price_monthly DECIMAL(10,2) NOT NULL,
                    price_annual DECIMAL(10,2) NULL,
                    target_user TEXT,
                    core_value TEXT,
                    analysis_brainstorm BOOLEAN NOT NULL DEFAULT FALSE,
                    templates VARCHAR(50) NOT NULL DEFAULT 'basic',
                    token_limit INTEGER NOT NULL DEFAULT 20000,
                    brand_voices INTEGER NOT NULL DEFAULT 0,
                    admin_controls BOOLEAN NOT NULL DEFAULT FALSE,
                    chat_history_limit INTEGER NOT NULL DEFAULT 10,
                    user_seats INTEGER NOT NULL DEFAULT 1,
                    support_level VARCHAR(50) NOT NULL DEFAULT 'none',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create user token usage tracking table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_token_usage (
                    user_id UUID PRIMARY KEY,
                    tokens_used_month INTEGER NOT NULL DEFAULT 0,
                    tokens_used_total INTEGER NOT NULL DEFAULT 0,
                    current_month INTEGER NOT NULL DEFAULT EXTRACT(MONTH FROM NOW()),
                    current_year INTEGER NOT NULL DEFAULT EXTRACT(YEAR FROM NOW()),
                    last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
            """)

            # Add plan_id column to users table if it doesn't exist
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'plan_id'
                    ) THEN
                        ALTER TABLE users ADD COLUMN plan_id VARCHAR(50) DEFAULT 'free';
                    END IF;
                END $$;
            """)

            # Chat sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id VARCHAR(36) PRIMARY KEY,
                    user_id UUID NOT NULL,
                    title VARCHAR(255) NOT NULL DEFAULT 'New Chat',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_chat_sessions_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
            """)

            # Create index for chat sessions
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_updated 
                ON chat_sessions(user_id, updated_at);
            """)

            # Chat messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id VARCHAR(36) PRIMARY KEY,
                    session_id VARCHAR(36) NOT NULL,
                    message_type message_type NOT NULL,
                    content TEXT NOT NULL,
                    content_mode VARCHAR(50) NULL,
                    brand_voice_id VARCHAR(36) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_chat_messages_session FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
                );
            """)

            # Create index for chat messages
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created 
                ON chat_messages(session_id, created_at);
            """)

            # Add foreign key constraints separately to avoid issues with table creation order
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'organization_invite_tokens_tenant_id_fkey'
                    ) THEN
                        ALTER TABLE organization_invite_tokens 
                        ADD CONSTRAINT organization_invite_tokens_tenant_id_fkey 
                        FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE;
                    END IF;
                END $$;
            """)

            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.table_constraints 
                        WHERE constraint_name = 'organization_invite_tokens_invited_by_user_id_fkey'
                    ) THEN
                        ALTER TABLE organization_invite_tokens 
                        ADD CONSTRAINT organization_invite_tokens_invited_by_user_id_fkey 
                        FOREIGN KEY (invited_by_user_id) REFERENCES users(user_id) ON DELETE CASCADE;
                    END IF;
                END $$;
            """)

            conn.commit()
            cursor.close()
            conn.close()
            
            # Populate default pricing plans
            self.populate_pricing_plans()
            
            logger.info("Main database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing main database: {e}")
            raise

    def ensure_chat_tables_exist(self):
        """Ensure chat tables exist - can be called independently"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Create message_type enum for PostgreSQL
            cursor.execute("""
                DO $$ BEGIN
                    CREATE TYPE message_type AS ENUM ('user', 'assistant');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)

            # Chat sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id VARCHAR(36) PRIMARY KEY,
                    user_id UUID NOT NULL,
                    title VARCHAR(255) NOT NULL DEFAULT 'New Chat',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_chat_sessions_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );
            """)

            # Create index for chat sessions
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_updated 
                ON chat_sessions(user_id, updated_at);
            """)

            # Chat messages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id VARCHAR(36) PRIMARY KEY,
                    session_id VARCHAR(36) NOT NULL,
                    message_type message_type NOT NULL,
                    content TEXT NOT NULL,
                    content_mode VARCHAR(50) NULL,
                    brand_voice_id VARCHAR(36) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_chat_messages_session FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
                );
            """)

            # Create index for chat messages
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created 
                ON chat_messages(session_id, created_at);
            """)

            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Chat tables ensured to exist")

        except Exception as e:
            logger.error(f"Error ensuring chat tables exist: {e}")
            raise

    def create_tenant_database(self, tenant: Tenant):
        """Create a tenant-specific database"""
        try:
            # Note: In a real Neon setup, you would create a separate database
            # For this implementation, we'll create tenant-specific tables in the main database
            # with tenant_id prefixes to simulate separate databases

            conn = self.get_connection()
            cursor = conn.cursor()

            table_suffix = tenant.tenant_id.replace('-', '_')

            # Create company brand voices table for all tenants (since we treat all voices as company voices now)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS company_brand_voices_{table_suffix} (
                    brand_voice_id UUID PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    configuration JSON NOT NULL,
                    markdown_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create user brand voices table (keeping for backward compatibility)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS user_brand_voices_{table_suffix} (
                    brand_voice_id UUID PRIMARY KEY,
                    user_id UUID NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    configuration JSON NOT NULL,
                    markdown_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Tenant database tables created successfully for {tenant.tenant_id}")

        except Exception as e:
            logger.error(f"Error creating tenant database: {e}")
            raise

    def create_tenant(self, name: str, tenant_type: TenantType, max_brand_voices: int = 3) -> Tenant:
        """Create a new tenant"""
        try:
            tenant_id = str(uuid.uuid4())
            database_name = f"tenant_{tenant_id.replace('-', '_')}"

            tenant = Tenant(
                tenant_id=tenant_id,
                tenant_type=tenant_type,
                name=name,
                database_name=database_name,
                max_brand_voices=max_brand_voices
            )

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO tenants (tenant_id, tenant_type, name, database_name, max_brand_voices)
                VALUES (%s, %s, %s, %s, %s)
            """, (tenant.tenant_id, tenant.tenant_type.value, tenant.name, tenant.database_name, tenant.max_brand_voices))

            conn.commit()
            cursor.close()
            conn.close()

            # Create tenant-specific tables
            self.create_tenant_database(tenant)

            return tenant

        except Exception as e:
            logger.error(f"Error creating tenant: {e}")
            raise

    def create_user(self, tenant_id: str, first_name: str, last_name: str, email: str, password: str, 
                   subscription_level: SubscriptionLevel, is_admin: bool = False) -> User:
        """Create a new user"""
        try:
            user_id = str(uuid.uuid4())
            password_hash = generate_password_hash(password)

            user = User(
                user_id=user_id,
                tenant_id=tenant_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password_hash=password_hash,
                subscription_level=subscription_level,
                is_admin=is_admin
            )

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users (user_id, tenant_id, first_name, last_name, email, password_hash, subscription_level, is_admin, email_verified)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user.user_id, user.tenant_id, user.first_name, user.last_name, user.email, user.password_hash, 
                  user.subscription_level.value, user.is_admin, False)) # Set email_verified to False initially

            conn.commit()
            cursor.close()
            conn.close()

            return user

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT * FROM users WHERE email = %s
            """, (email,))

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                user = User(
                    user_id=str(row['user_id']),
                    tenant_id=str(row['tenant_id']),
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    email=row['email'],
                    password_hash=row['password_hash'],
                    subscription_level=SubscriptionLevel(row['subscription_level']),
                    is_admin=row['is_admin']
                )
                user.email_verified = row['email_verified']  # Add email_verified
                user.created_at = row['created_at']
                user.last_login = row['last_login']
                return user
            return None

        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def get_tenant_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT * FROM tenants WHERE tenant_id = %s
            """, (tenant_id,))

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                return Tenant(
                    tenant_id=str(row['tenant_id']),
                    tenant_type=TenantType(row['tenant_type']),
                    name=row['name'],
                    database_name=row['database_name'],
                    max_brand_voices=row['max_brand_voices']
                )
            return None

        except Exception as e:
            logger.error(f"Error getting tenant by ID: {e}")
            return None

    def verify_password(self, user: User, password: str) -> bool:
        """Verify a user's password"""
        try:
            return check_password_hash(user.password_hash, password)
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    def create_verification_token(self, user_id: str, token_hash: str) -> bool:
        """Create email verification token"""
        try:
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(hours=24)

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO email_verification_tokens (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s)
            """, (user_id, token_hash, expires_at))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error creating verification token: {e}")
            return False

    def verify_email_token(self, token_hash: str) -> Optional[str]:
        """Verify email token and return user_id if valid"""
        try:
            from datetime import datetime

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id FROM email_verification_tokens 
                WHERE token_hash = %s AND expires_at > %s AND used = FALSE
            """, (token_hash, datetime.utcnow()))

            row = cursor.fetchone()

            if row:
                user_id = str(row[0])

                # Mark token as used
                cursor.execute("""
                    UPDATE email_verification_tokens 
                    SET used = TRUE 
                    WHERE token_hash = %s
                """, (token_hash,))

                # Mark user email as verified
                cursor.execute("""
                    UPDATE users 
                    SET email_verified = TRUE 
                    WHERE user_id = %s
                """, (user_id,))

                conn.commit()
                cursor.close()
                conn.close()
                return user_id

            cursor.close()
            conn.close()
            return None

        except Exception as e:
            logger.error(f"Error verifying email token: {e}")
            return None

    def create_password_reset_token(self, user_id: str, token_hash: str) -> bool:
        """Create password reset token"""
        try:
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(hours=1)

            conn = self.get_connection()
            cursor = conn.cursor()

            # Delete any existing tokens for this user
            cursor.execute("""
                DELETE FROM password_reset_tokens 
                WHERE user_id = %s
            """, (user_id,))

            cursor.execute("""
                INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s)
            """, (user_id, token_hash, expires_at))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error creating password reset token: {e}")
            return False

    def verify_password_reset_token(self, token_hash: str) -> Optional[str]:
        """Verify password reset token and return user_id if valid"""
        try:
            from datetime import datetime

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT user_id FROM password_reset_tokens 
                WHERE token_hash = %s AND expires_at > %s AND used = FALSE
            """, (token_hash, datetime.utcnow()))

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                return str(row[0])
            return None

        except Exception as e:
            logger.error(f"Error verifying password reset token: {e}")
            return None

    def use_password_reset_token(self, token_hash: str) -> bool:
        """Mark password reset token as used"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE password_reset_tokens 
                SET used = TRUE 
                WHERE token_hash = %s
            """, (token_hash,))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error marking password reset token as used: {e}")
            return False

    def resend_verification_email(self, user_id: str) -> bool:
        """Delete existing verification tokens for user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM email_verification_tokens 
                WHERE user_id = %s
            """, (user_id,))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error deleting verification tokens: {e}")
            return False

    def get_company_brand_voices(self, tenant_id: str) -> List[BrandVoice]:
        """Get company brand voices for a tenant"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            table_name = f"company_brand_voices_{tenant_id.replace('-', '_')}"

            logger.info(f"Getting company brand voices from table: {table_name}")

            # First, ensure the table exists
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    brand_voice_id UUID PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    configuration JSON NOT NULL,
                    markdown_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Commit the table creation before querying
            conn.commit()

            cursor.execute(f"""
                SELECT * FROM {table_name} ORDER BY created_at DESC
            """)

            rows = cursor.fetchall()
            logger.info(f"Found {len(rows)} brand voices in {table_name}")

            cursor.close()
            conn.close()

            brand_voices = []
            for row in rows:
                logger.info(f"Processing brand voice: {row['name']} (ID: {row['brand_voice_id']})")
                brand_voices.append(BrandVoice(
                    brand_voice_id=str(row['brand_voice_id']),
                    name=row['name'],
                    configuration=row['configuration'],
                    markdown_content=row['markdown_content']
                ))

            logger.info(f"Returning {len(brand_voices)} brand voices")
            return brand_voices

        except Exception as e:
            logger.error(f"Error getting company brand voices for tenant {tenant_id}: {e}")
            return []

    def get_user_brand_voices(self, tenant_id: str, user_id: str) -> List[BrandVoice]:
        """Get user brand voices"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            table_name = f"user_brand_voices_{tenant_id.replace('-', '_')}"
            cursor.execute(f"""
                SELECT * FROM {table_name} WHERE user_id = %s ORDER BY name
            """, (user_id,))

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            brand_voices = []
            for row in rows:
                brand_voices.append(BrandVoice(
                    brand_voice_id=str(row['brand_voice_id']),
                    name=row['name'],
                    configuration=row['configuration'],
                    markdown_content=row['markdown_content'],
                    user_id=str(row['user_id'])
                ))

            return brand_voices

        except Exception as e:
            logger.error(f"Error getting user brand voices: {e}")
            return []

    def create_brand_voice(self, tenant_id: str, name: str, configuration: Dict[str, Any], 
                          markdown_content: str, user_id: Optional[str] = None) -> BrandVoice:
        """Create a new brand voice"""
        try:
            brand_voice_id = str(uuid.uuid4())

            conn = self.get_connection()
            cursor = conn.cursor()

            if user_id:
                # User brand voice
                table_name = f"user_brand_voices_{tenant_id.replace('-', '_')}"
                # Ensure table exists
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        brand_voice_id UUID PRIMARY KEY,
                        user_id UUID NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        configuration JSON NOT NULL,
                        markdown_content TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute(f"""
                    INSERT INTO {table_name} (brand_voice_id, user_id, name, configuration, markdown_content)
                    VALUES (%s, %s, %s, %s, %s)
                """, (brand_voice_id, user_id, name, json.dumps(configuration), markdown_content))
            else:
                # Company brand voice
                table_name = f"company_brand_voices_{tenant_id.replace('-', '_')}"
                # Ensure table exists
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        brand_voice_id UUID PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        configuration JSON NOT NULL,
                        markdown_content TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute(f"""
                    INSERT INTO {table_name} (brand_voice_id, name, configuration, markdown_content)
                    VALUES (%s, %s, %s, %s)
                """, (brand_voice_id, name, json.dumps(configuration), markdown_content))

            conn.commit()
            cursor.close()
            conn.close()

            return BrandVoice(
                brand_voice_id=brand_voice_id,
                name=name,
                configuration=configuration,
                markdown_content=markdown_content,
                user_id=user_id
            )

        except Exception as e:
            logger.error(f"Error creating brand voice: {e}")
            raise

    def update_brand_voice(self, tenant_id: str, brand_voice_id: str, wizard_data: Dict[str, Any], 
                          markdown_content: str, user_id: Optional[str] = None) -> BrandVoice:
        """Update an existing brand voice with new wizard data"""
        try:
            name = wizard_data['voice_short_name']
            configuration = wizard_data.copy()

            conn = self.get_connection()
            cursor = conn.cursor()

            if user_id:
                # User brand voice
                table_name = f"user_brand_voices_{tenant_id.replace('-', '_')}"
                cursor.execute(f"""
                    UPDATE {table_name} 
                    SET name = %s, configuration = %s, markdown_content = %s
                    WHERE brand_voice_id = %s AND user_id = %s
                """, (name, json.dumps(configuration), markdown_content, brand_voice_id, user_id))
            else:
                # Company brand voice
                table_name = f"company_brand_voices_{tenant_id.replace('-', '_')}"
                cursor.execute(f"""
                    UPDATE {table_name} 
                    SET name = %s, configuration = %s, markdown_content = %s
                    WHERE brand_voice_id = %s
                """, (name, json.dumps(configuration), markdown_content, brand_voice_id))

            if cursor.rowcount == 0:
                raise Exception("Brand voice not found or permission denied")

            conn.commit()
            cursor.close()
            conn.close()

            return BrandVoice(
                brand_voice_id=brand_voice_id,
                name=name,
                configuration=configuration,
                markdown_content=markdown_content,
                user_id=user_id
            )

        except Exception as e:
            logger.error(f"Error updating brand voice: {e}")
            raise

    def create_comprehensive_brand_voice(self, tenant_id: str, wizard_data: Dict[str, Any], 
                                       markdown_content: str, user_id: Optional[str] = None) -> BrandVoice:
        """Create a comprehensive brand voice with full wizard data - now always creates as company voice"""
        try:
            brand_voice_id = str(uuid.uuid4())
            name = wizard_data['voice_short_name']

            # Store the comprehensive wizard data as configuration
            configuration = wizard_data.copy()

            conn = self.get_connection()
            cursor = conn.cursor()

            # Always create as company brand voice now (ignoring user_id parameter)
            table_name = f"company_brand_voices_{tenant_id.replace('-', '_')}"

            # Ensure table exists
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    brand_voice_id UUID PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    configuration JSON NOT NULL,
                    markdown_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute(f"""
                INSERT INTO {table_name} (brand_voice_id, name, configuration, markdown_content)
                VALUES (%s, %s, %s, %s)
            """, (brand_voice_id, name, json.dumps(configuration), markdown_content))

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Successfully created brand voice '{name}' with ID {brand_voice_id} in tenant {tenant_id}")

            return BrandVoice(
                brand_voice_id=brand_voice_id,
                name=name,
                configuration=configuration,
                markdown_content=markdown_content,
                user_id=None  # Always None since we're treating as company voice
            )

        except Exception as e:
            logger.error(f"Error creating comprehensive brand voice: {e}")
            raise

    def get_all_tenants(self) -> List[Tenant]:
        """Get all tenants for admin management"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT tenant_id, tenant_type, name, database_name, max_brand_voices
                FROM tenants 
                ORDER BY name
            """)

            tenants = []
            for row in cursor.fetchall():
                tenants.append(Tenant(
                    tenant_id=str(row[0]),
                    tenant_type=TenantType(row[1]),
                    name=row[2],
                    database_name=row[3],
                    max_brand_voices=row[4]
                ))

            cursor.close()
            conn.close()
            return tenants
        except Exception as e:
            logger.error(f"Error getting all tenants: {e}")
            return []

    def get_organization_users(self, tenant_id: str) -> List[tuple]:
        """Get all users for a specific organization"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT u.user_id, u.tenant_id, u.first_name, u.last_name, u.email, 
                       u.subscription_level, u.is_admin, u.email_verified, u.created_at,
                       u.password_hash, u.last_login
                FROM users u
                WHERE u.tenant_id = %s
                ORDER BY u.is_admin DESC, u.created_at ASC
            """, (tenant_id,))

            users = []
            for row in cursor.fetchall():
                user = User(
                    user_id=str(row[0]),
                    tenant_id=str(row[1]),
                    first_name=row[2],
                    last_name=row[3],
                    email=row[4],
                    subscription_level=SubscriptionLevel(row[5]),
                    is_admin=row[6],
                    email_verified=row[7],
                    created_at=row[8],
                    password_hash=row[9],
                    last_login=row[10]
                )
                users.append(user)

            cursor.close()
            conn.close()
            return users
        except Exception as e:
            logger.error(f"Error getting organization users: {e}")
            return []

    def get_all_users(self) -> List[tuple]:
        """Get all users with tenant info for admin management"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT u.user_id, u.tenant_id, u.first_name, u.last_name, u.email, 
                       u.subscription_level, u.is_admin, u.email_verified, u.created_at,
                       t.name as tenant_name, t.tenant_type
                FROM users u
                JOIN tenants t ON u.tenant_id = t.tenant_id
                ORDER BY u.created_at DESC
            """)

            users = []
            for row in cursor.fetchall():
                user = User(
                    user_id=str(row[0]),
                    tenant_id=str(row[1]),
                    first_name=row[2],
                    last_name=row[3],
                    email=row[4],
                    password_hash="",  # Don't include password hash
                    subscription_level=SubscriptionLevel(row[5]),
                    is_admin=row[6],
                    email_verified=row[7],
                    created_at=str(row[8]) if row[8] else None
                )
                tenant_name = row[9]
                tenant_type = row[10]
                users.append((user, tenant_name, tenant_type))

            cursor.close()
            conn.close()
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            return []

    def delete_user(self, user_id: str) -> bool:
        """Delete a user account"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Get user's tenant_id first
            cursor.execute("SELECT tenant_id FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            if result:
                tenant_id = str(result[0])

                # Delete user's brand voices from tenant-specific table
                table_name = f"user_brand_voices_{tenant_id.replace('-', '_')}"
                try:
                    cursor.execute(f"DELETE FROM {table_name} WHERE user_id = %s", (user_id,))
                except Exception:
                    # Table might not exist, continue
                    pass

            # Delete verification tokens
            cursor.execute("DELETE FROM email_verification_tokens WHERE user_id = %s", (user_id,))

            # Delete password reset tokens
            cursor.execute("DELETE FROM password_reset_tokens WHERE user_id = %s", (user_id,))

            # Delete organization invite tokens sent by this user (if table exists)
            try:
                cursor.execute("DELETE FROM organization_invite_tokens WHERE invited_by_user_id = %s", (user_id,))
            except Exception as e:
                # Table might not exist, continue
                logger.warning(f"Could not delete organization invite tokens for user {user_id}: {e}")
                pass

            # Delete the user
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))

            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            return False

    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant and all associated data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Get all users in this tenant
            cursor.execute("SELECT user_id FROM users WHERE tenant_id = %s", (tenant_id,))
            user_ids = [row[0] for row in cursor.fetchall()]

            # Delete all user data
            for user_id in user_ids:
                cursor.execute("DELETE FROM email_verification_tokens WHERE user_id = %s", (user_id,))
                cursor.execute("DELETE FROM password_reset_tokens WHERE user_id = %s", (user_id,))

            # Delete tenant-specific brand voice tables
            table_prefix = tenant_id.replace('-', '_')
            try:
                cursor.execute(f"DROP TABLE IF EXISTS company_brand_voices_{table_prefix}")
                cursor.execute(f"DROP TABLE IF EXISTS user_brand_voices_{table_prefix}")
            except Exception:
                # Tables might not exist, continue
                pass

            # Delete organization invite tokens for this tenant
            try:
                cursor.execute("DELETE FROM organization_invite_tokens WHERE tenant_id = %s", (tenant_id,))
            except Exception:
                # Table might not exist, continue
                pass

            # Delete all users
            cursor.execute("DELETE FROM users WHERE tenant_id = %s", (tenant_id,))

            # Delete the tenant
            cursor.execute("DELETE FROM tenants WHERE tenant_id = %s", (tenant_id,))

            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting tenant: {e}")
            return False

    def update_user_subscription(self, user_id: str, subscription_level: str) -> bool:
        """Update user's subscription level"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users 
                SET subscription_level = %s
                WHERE user_id = %s
            """, (subscription_level, user_id))

            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating user subscription: {e}")
            return False

    def create_organization_invite(self, tenant_id: str, invited_by_user_id: str, email: str, token_hash: str) -> bool:
        """Create an organization invite token"""
        try:
            from datetime import datetime, timedelta
            expires_at = datetime.utcnow() + timedelta(days=7)  # 7 day expiry

            conn = self.get_connection()
            cursor = conn.cursor()

            # Check if there's already a pending invite for this email to this organization
            cursor.execute("""
                SELECT invite_id FROM organization_invite_tokens 
                WHERE tenant_id = %s AND email = %s AND used = FALSE AND expires_at > %s
            """, (tenant_id, email.lower(), datetime.utcnow()))

            existing_invite = cursor.fetchone()
            if existing_invite:
                # Delete the existing invite
                cursor.execute("""
                    DELETE FROM organization_invite_tokens 
                    WHERE invite_id = %s
                """, (existing_invite[0],))

            cursor.execute("""
                INSERT INTO organization_invite_tokens (tenant_id, invited_by_user_id, email, token_hash, expires_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (tenant_id, invited_by_user_id, email.lower(), token_hash, expires_at))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error creating organization invite: {e}")
            conn.rollback()
            cursor.close()
            conn.close()
            return False

    def verify_organization_invite_token(self, token_hash: str) -> Optional[tuple]:
        """Verify organization invite token and return (tenant_id, email) if valid"""
        try:
            from datetime import datetime

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT tenant_id, email FROM organization_invite_tokens 
                WHERE token_hash = %s AND expires_at > %s AND used = FALSE
            """, (token_hash, datetime.utcnow()))

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                return (str(row[0]), row[1])
            return None

        except Exception as e:
            logger.error(f"Error verifying organization invite token: {e}")
            return None

    def use_organization_invite_token(self, token_hash: str) -> bool:
        """Mark organization invite token as used"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE organization_invite_tokens 
                SET used = TRUE 
                WHERE token_hash = %s
            """, (token_hash,))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error marking organization invite token as used: {e}")
            return False

    def get_pending_invites(self, tenant_id):
        """Get pending organization invites"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT oi.email, 
                       (u.first_name || ' ' || u.last_name) as invited_by,
                       oi.created_at
                FROM organization_invite_tokens oi
                JOIN users u ON oi.invited_by_user_id = u.user_id
                WHERE oi.tenant_id = %s AND oi.used = FALSE
                ORDER BY oi.created_at DESC
            """, (tenant_id,))

            invites = cursor.fetchall()
            cursor.close()
            conn.close()

            # Convert to list of dicts for JSON serialization
            return [dict(invite) for invite in invites]
        except Exception as e:
            logger.error(f"Error getting pending invites for tenant {tenant_id}: {e}")
            return []

    def update_user_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        try:
            from datetime import datetime

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users 
                SET last_login = %s
                WHERE user_id = %s
            """, (datetime.utcnow(), user_id))

            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating user last login: {e}")
            return False

    def create_chat_session(self, user_id, title=None):
        """Create a new chat session"""
        try:
            # Ensure chat tables exist
            self.ensure_chat_tables_exist()

            conn = self.get_connection()
            cursor = conn.cursor()

            session_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO chat_sessions (session_id, user_id, title, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (session_id, user_id, title or "New Chat"))

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Created chat session {session_id} for user {user_id}")
            return session_id
        except Exception as e:
            logger.error(f"Error creating chat session for user {user_id}: {e}")
            return None

    def add_chat_message(self, session_id, message_type, content, content_mode=None, brand_voice_id=None):
        """Add a message to a chat session"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            message_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO chat_messages (message_id, session_id, message_type, content, content_mode, brand_voice_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (message_id, session_id, message_type, content, content_mode, brand_voice_id))

            conn.commit()
            cursor.close()
            conn.close()

            return message_id
        except Exception as e:
            logger.error(f"Error adding message to session {session_id}: {e}")
            return None

    def get_user_chat_sessions(self, user_id, limit=20):
        """Get user's recent chat sessions"""
        try:
            # Ensure chat tables exist
            self.ensure_chat_tables_exist()

            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT cs.session_id, cs.title, cs.created_at, cs.updated_at,
                       COUNT(cm.message_id) as message_count
                FROM chat_sessions cs
                LEFT JOIN chat_messages cm ON cs.session_id = cm.session_id
                WHERE cs.user_id = %s
                GROUP BY cs.session_id, cs.title, cs.created_at, cs.updated_at
                ORDER BY cs.updated_at DESC
                LIMIT %s
            """, (user_id, limit))

            sessions = cursor.fetchall()
            cursor.close()
            conn.close()

            return sessions
        except Exception as e:
            logger.error(f"Error getting chat sessions for user {user_id}: {e}")
            return []

    def get_chat_messages(self, session_id):
        """Get messages for a chat session"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT message_id, message_type, content, content_mode, brand_voice_id, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC
            """, (session_id,))

            messages = cursor.fetchall()
            cursor.close()
            conn.close()

            return messages
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            return []

    def update_chat_session_title(self, session_id, title):
        """Update chat session title and updated_at timestamp"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE chat_sessions 
                SET title = %s, updated_at = NOW()
                WHERE session_id = %s
            """, (title, session_id))

            conn.commit()
            cursor.close()
            conn.close()

            return True
        except Exception as e:
            logger.error(f"Error updating chat session title {session_id}: {e}")
            return False

    def delete_chat_session(self, session_id, user_id):
        """Delete a chat session and its messages"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # First verify the session belongs to the user
            cursor.execute("""
                SELECT user_id FROM chat_sessions WHERE session_id = %s
            """, (session_id,))

            result = cursor.fetchone()
            if not result or result[0] != user_id:
                cursor.close()
                conn.close()
                return False

            # Delete messages first (foreign key constraint)
            cursor.execute("DELETE FROM chat_messages WHERE session_id = %s", (session_id,))

            # Delete session
            cursor.execute("DELETE FROM chat_sessions WHERE session_id = %s", (session_id,))

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Deleted chat session {session_id} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting chat session {session_id}: {e}")
            return False

    def get_all_pricing_plans(self):
        """Get all pricing plans"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # First ensure pricing plans are populated
            self.populate_pricing_plans()

            cursor.execute("""
                SELECT * FROM pricing_plans ORDER BY 
                CASE plan_id 
                    WHEN 'free' THEN 1 
                    WHEN 'solo' THEN 2 
                    WHEN 'team' THEN 3 
                    WHEN 'professional' THEN 4 
                    ELSE 5 
                END
            """)

            plans = cursor.fetchall()
            cursor.close()
            conn.close()

            plans_list = [dict(plan) for plan in plans]
            logger.info(f"Retrieved {len(plans_list)} pricing plans from database")
            return plans_list
        except Exception as e:
            logger.error(f"Error getting pricing plans: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []

    def populate_pricing_plans(self):
        """Populate pricing plans table with default data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Ensure the pricing_plans table exists first
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pricing_plans (
                    plan_id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price_monthly DECIMAL(10,2) NOT NULL,
                    price_annual DECIMAL(10,2) NULL,
                    target_user TEXT,
                    core_value TEXT,
                    analysis_brainstorm BOOLEAN NOT NULL DEFAULT FALSE,
                    templates VARCHAR(50) NOT NULL DEFAULT 'basic',
                    token_limit INTEGER NOT NULL DEFAULT 20000,
                    brand_voices INTEGER NOT NULL DEFAULT 0,
                    admin_controls BOOLEAN NOT NULL DEFAULT FALSE,
                    chat_history_limit INTEGER NOT NULL DEFAULT 10,
                    user_seats INTEGER NOT NULL DEFAULT 1,
                    support_level VARCHAR(50) NOT NULL DEFAULT 'none',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Check if plans already exist
            cursor.execute("SELECT COUNT(*) FROM pricing_plans")
            count = cursor.fetchone()[0]
            logger.info(f"Found {count} existing pricing plans")

            if count == 0:
                # Insert default pricing plans
                plans = [
                    {
                        'plan_id': 'free',
                        'name': 'The Companion',
                        'price_monthly': 0.00,
                        'price_annual': None,
                        'target_user': 'Individuals exploring the tool.',
                        'core_value': 'Basic access to the core model.',
                        'analysis_brainstorm': False,
                        'templates': 'basic',
                        'token_limit': 20000,
                        'brand_voices': 0,
                        'admin_controls': False,
                        'chat_history_limit': 10,
                        'user_seats': 1,
                        'support_level': 'none'
                    },
                    {
                        'plan_id': 'solo',
                        'name': 'The Practitioner',
                        'price_monthly': 29.00,
                        'price_annual': 290.00,
                        'target_user': 'Solo practitioners working independently.',
                        'core_value': 'Full power for one person.',
                        'analysis_brainstorm': True,
                        'templates': 'full',
                        'token_limit': 200000,
                        'brand_voices': 1,
                        'admin_controls': False,
                        'chat_history_limit': -1,
                        'user_seats': 1,
                        'support_level': 'email'
                    },
                    {
                        'plan_id': 'team',
                        'name': 'The Organization',
                        'price_monthly': 39.00,
                        'price_annual': 32.00,
                        'target_user': 'Communication departments and teams.',
                        'core_value': 'Organizational consistency with team collaboration.',
                        'analysis_brainstorm': True,
                        'templates': 'full',
                        'token_limit': 250000,
                        'brand_voices': 10,
                        'admin_controls': True,
                        'chat_history_limit': -1,
                        'user_seats': 50,
                        'support_level': 'priority'
                    },
                    {
                        'plan_id': 'professional',
                        'name': 'The Powerhouse',
                        'price_monthly': 82.00,
                        'price_annual': 820.00,
                        'target_user': 'Professional grant writers and heavy users.',
                        'core_value': 'Massive individual output with premium features.',
                        'analysis_brainstorm': True,
                        'templates': 'full',
                        'token_limit': 1000000,
                        'brand_voices': 10,
                        'admin_controls': False,
                        'chat_history_limit': -1,
                        'user_seats': 1,
                        'support_level': 'top_priority'
                    }
                ]

                for plan in plans:
                    cursor.execute("""
                        INSERT INTO pricing_plans (
                            plan_id, name, price_monthly, price_annual, target_user, core_value,
                            analysis_brainstorm, templates, token_limit, brand_voices, admin_controls,
                            chat_history_limit, user_seats, support_level
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        plan['plan_id'], plan['name'], plan['price_monthly'], plan['price_annual'],
                        plan['target_user'], plan['core_value'], plan['analysis_brainstorm'],
                        plan['templates'], plan['token_limit'], plan['brand_voices'],
                        plan['admin_controls'], plan['chat_history_limit'], plan['user_seats'],
                        plan['support_level']
                    ))

                conn.commit()
                logger.info("Pricing plans populated successfully")

            cursor.close()
            conn.close()

        except Exception as e:
            logger.error(f"Error populating pricing plans: {e}")
            raise

    def get_user_plan(self, user_id):
        """Get user's current plan details"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT u.plan_id, pp.* 
                FROM users u
                LEFT JOIN pricing_plans pp ON u.plan_id = pp.plan_id
                WHERE u.user_id = %s
            """, (user_id,))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error getting user plan: {e}")
            return None

    def get_user_token_usage(self, user_id):
        """Get user's token usage for the current month"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Ensure usage record exists
            self.ensure_user_token_usage_record(user_id)

            cursor.execute("""
                SELECT tokens_used_month, tokens_used_total, current_month, current_year
                FROM user_token_usage 
                WHERE user_id = %s
            """, (user_id,))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            return dict(result) if result else {'tokens_used_month': 0, 'tokens_used_total': 0}
        except Exception as e:
            logger.error(f"Error getting user token usage: {e}")
            return {'tokens_used_month': 0, 'tokens_used_total': 0}

    def ensure_user_token_usage_record(self, user_id):
        """Ensure user has a token usage record"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO user_token_usage (user_id, tokens_used_month, tokens_used_total)
                VALUES (%s, 0, 0)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id,))

            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            logger.error(f"Error ensuring user token usage record: {e}")

    def update_user_token_usage(self, user_id, tokens_used):
        """Update user's token usage"""
        try:
            from datetime import datetime
            current_month = datetime.now().month
            current_year = datetime.now().year

            conn = self.get_connection()
            cursor = conn.cursor()

            # Check if we need to reset monthly usage
            cursor.execute("""
                SELECT current_month, current_year FROM user_token_usage 
                WHERE user_id = %s
            """, (user_id,))

            result = cursor.fetchone()
            if result:
                stored_month, stored_year = result
                if stored_month != current_month or stored_year != current_year:
                    # Reset monthly usage
                    cursor.execute("""
                        UPDATE user_token_usage 
                        SET tokens_used_month = %s, tokens_used_total = tokens_used_total + %s,
                            current_month = %s, current_year = %s, last_reset = NOW()
                        WHERE user_id = %s
                    """, (tokens_used, tokens_used, current_month, current_year, user_id))
                else:
                    # Add to existing usage
                    cursor.execute("""
                        UPDATE user_token_usage 
                        SET tokens_used_month = tokens_used_month + %s, 
                            tokens_used_total = tokens_used_total + %s
                        WHERE user_id = %s
                    """, (tokens_used, tokens_used, user_id))
            else:
                # Create new record
                cursor.execute("""
                    INSERT INTO user_token_usage 
                    (user_id, tokens_used_month, tokens_used_total, current_month, current_year)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, tokens_used, tokens_used, current_month, current_year))

            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating user token usage: {e}")
            return False

    def check_user_limits(self, user_id, content_mode, estimated_tokens):
        """Check if user can perform the requested action based on their plan limits"""
        try:
            # Get user's plan
            user_plan = self.get_user_plan(user_id)
            if not user_plan:
                return {'allowed': False, 'error': 'User plan not found'}

            # Check if content mode is allowed for free users
            if user_plan['plan_id'] == 'free':
                restricted_modes = ['summarize', 'brainstorm', 'analyze']
                if content_mode in restricted_modes:
                    return {'allowed': False, 'error': f'{content_mode.title()} feature requires a paid plan'}

            # Check token limits
            usage = self.get_user_token_usage(user_id)
            current_usage = usage.get('tokens_used_month', 0)
            token_limit = user_plan.get('token_limit', 20000)

            if current_usage + estimated_tokens > token_limit:
                return {'allowed': False, 'error': f'Monthly token limit exceeded. Upgrade your plan for more tokens.'}

            return {'allowed': True}

        except Exception as e:
            logger.error(f"Error checking user limits: {e}")
            return {'allowed': False, 'error': 'Error checking user limits'}

# Global database manager instance
db_manager = DatabaseManager()

def init_databases():
    """Initialize all databases"""
    db_manager.init_main_database()

# Initialize databases on import
try:
    init_databases()
except Exception as e:
    logger.error(f"Failed to initialize databases on import: {e}")
    # Don't raise here to avoid breaking the app, but log the error