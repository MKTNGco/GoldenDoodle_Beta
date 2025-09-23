import os
import psycopg2
import psycopg2.extras
from psycopg2 import sql
import uuid
import json
import logging
from typing import Optional, List, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash
from models import Tenant, User, BrandVoice, TenantType, SubscriptionLevel
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Define RealDictCursor for use in methods  
from psycopg2.extras import RealDictCursor

class DatabaseManager:
    def __init__(self):
        self.main_db_url = os.environ.get("DATABASE_URL")
        if not self.main_db_url:
            raise ValueError("DATABASE_URL environment variable is required")

    def get_connection(self, database_url: Optional[str] = None):
        """Get a database connection"""
        url = database_url or self.main_db_url
        return psycopg2.connect(url)

    def _is_safe_identifier(self, identifier: str) -> bool:
        """Validate that an identifier is safe for use in SQL (alphanumeric, hyphens, underscores only)"""
        import re
        # Allow only alphanumeric characters, hyphens, and underscores
        # Typical UUID format: 8-4-4-4-12 characters
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', identifier)) and len(identifier) <= 50

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
                    CREATE TYPE subscription_level AS ENUM ('free', 'solo', 'pro', 'team', 'enterprise');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)

            # Migration: Add 'free' to existing subscription_level enum if not present
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_enum 
                        WHERE enumlabel = 'free' 
                        AND enumtypid = (
                            SELECT oid FROM pg_type WHERE typname = 'subscription_level'
                        )
                    ) THEN
                        ALTER TYPE subscription_level ADD VALUE 'free' BEFORE 'solo';
                    END IF;
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    stripe_customer_id VARCHAR(255) UNIQUE,
                    stripe_subscription_id VARCHAR(255) UNIQUE,
                    subscription_status VARCHAR(50) DEFAULT 'inactive',
                    current_period_end TIMESTAMP
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
                    name VARCHAR(100) NOT NULL,
                    display_name VARCHAR(100),
                    core_value TEXT,
                    price_monthly DECIMAL(10,2),
                    price_annual DECIMAL(10,2),
                    token_limit INTEGER,
                    chat_history_limit INTEGER,
                    brand_voices INTEGER DEFAULT 0,
                    admin_controls BOOLEAN DEFAULT FALSE,
                    features JSONB,
                    user_seats INTEGER DEFAULT 1,
                    support_level VARCHAR(50) DEFAULT 'none',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
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

            # Add Stripe-related columns to users table
            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'stripe_customer_id'
                    ) THEN
                        ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(255) NULL;
                    END IF;
                END $$;
            """)

            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'stripe_subscription_id'
                    ) THEN
                        ALTER TABLE users ADD COLUMN stripe_subscription_id VARCHAR(255) NULL;
                    END IF;
                END $$;
            """)

            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'subscription_status'
                    ) THEN
                        ALTER TABLE users ADD COLUMN subscription_status VARCHAR(50) DEFAULT 'free';
                    END IF;
                END $$;
            """)

            cursor.execute("""
                DO $$ 
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'current_period_end'
                    ) THEN
                        ALTER TABLE users ADD COLUMN current_period_end TIMESTAMP NULL;
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
            try:
                self.populate_pricing_plans()
            except AttributeError:
                logger.warning("populate_pricing_plans method not found, skipping pricing plans initialization")

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
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    brand_voice_id UUID PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    configuration JSON NOT NULL,
                    markdown_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """).format(sql.Identifier(f"company_brand_voices_{table_suffix}")))

            # Create user brand voices table (keeping for backward compatibility)
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    brand_voice_id UUID PRIMARY KEY,
                    user_id UUID NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    configuration JSON NOT NULL,
                    markdown_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """).format(sql.Identifier(f"user_brand_voices_{table_suffix}")))

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

            # Create user
            cursor.execute("""
                INSERT INTO users (user_id, tenant_id, first_name, last_name, email, password_hash, 
                                 subscription_level, is_admin, email_verified, created_at, plan_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (user_id, tenant_id, first_name, last_name, email, password_hash, 
                  subscription_level.value, is_admin, False, datetime.now(), subscription_level.value))

            user_row = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            if not user_row:
                raise Exception("Failed to create user - no data returned")

            logger.error(f"🔍 DB DEBUG: user_row from database: {user_row}")
            logger.error(f"🔍 DB DEBUG: user_row[0] (user_id) type: {type(user_row[0])}")
            logger.error(f"🔍 DB DEBUG: user_row[0] (user_id) value: {repr(user_row[0])}")

            # Return User object with proper string conversion - user_row is a tuple
            user_obj = User(
                user_id=str(user_row[0]),  # user_id
                tenant_id=str(user_row[1]),  # tenant_id
                first_name=user_row[2],  # first_name
                last_name=user_row[3],  # last_name
                email=user_row[4],  # email
                password_hash=user_row[5],  # password_hash
                subscription_level=SubscriptionLevel(user_row[6]),  # subscription_level
                is_admin=user_row[7],  # is_admin
                email_verified=user_row[8],  # email_verified
                created_at=user_row[9].isoformat() if user_row[9] else None,  # created_at
                plan_id=user_row[10] if len(user_row) > 10 else subscription_level.value  # plan_id
            )
            user_obj.plan_id = subscription_level.value

            logger.error(f"🔍 DB DEBUG: Created User object type: {type(user_obj)}")
            logger.error(f"🔍 DB DEBUG: Created User object user_id: {repr(user_obj.user_id)}")
            logger.error(f"🔍 DB DEBUG: Created User object user_id type: {type(user_obj.user_id)}")

            return user_obj

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
                user.email_verified = row.get('email_verified', False)
                user.created_at = row.get('created_at')
                user.last_login = row.get('last_login')
                user.plan_id = row.get('plan_id', row['subscription_level'])  # Ensure plan_id matches subscription_level
                return user
            return None

        except Exception as e:
            logger.error(f"Error getting user by email: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT * FROM users WHERE user_id = %s
            """, (user_id,))

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
                user.email_verified = row.get('email_verified', False)
                user.created_at = row.get('created_at')
                user.last_login = row.get('last_login')
                user.plan_id = row.get('plan_id', row['subscription_level'])  # Ensure plan_id matches subscription_level
                return user
            return None

        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    def update_user_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP 
                WHERE user_id = %s
            """, (user_id,))

            success = cursor.rowcount > 0
            conn.commit()
            cursor.close()
            conn.close()
            return success

        except Exception as e:
            logger.error(f"Error updating user last login: {e}")
            return False

    def mark_email_verified(self, user_id: str) -> bool:
        """Mark user's email as verified"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE users 
                SET email_verified = TRUE 
                WHERE user_id = %s
            """, (user_id,))

            success = cursor.rowcount > 0
            conn.commit()
            cursor.close()
            conn.close()
            return success

        except Exception as e:
            logger.error(f"Error marking email as verified: {e}")
            return False

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

    def get_organization_invite_by_token(self, token: str) -> Optional[Dict]:
        """Get organization invitation by token"""
        try:
            from email_service import hash_token
            token_hash = hash_token(token)

            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT oit.*, t.name as organization_name, u.first_name as invited_by_name, u.last_name as invited_by_last_name
                FROM organization_invite_tokens oit
                JOIN tenants t ON oit.tenant_id = t.tenant_id
                JOIN users u ON oit.invited_by_user_id = u.user_id
                WHERE oit.token_hash = %s AND oit.expires_at > %s AND oit.used = FALSE
            """, (token_hash, datetime.utcnow()))

            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                return {
                    'token_hash': row['token_hash'],
                    'tenant_id': str(row['tenant_id']),
                    'email': row['email'],
                    'organization_name': row['organization_name'],
                    'invited_by_name': f"{row['invited_by_name']} {row['invited_by_last_name']}",
                    'expires_at': row['expires_at']
                }
            return None

        except Exception as e:
            logger.error(f"Error getting organization invite by token: {e}")
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

            success = cursor.rowcount > 0
            conn.commit()
            cursor.close()
            conn.close()
            return success

        except Exception as e:
            logger.error(f"Error marking organization invite token as used: {e}")
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
            # Validate tenant_id to prevent SQL injection
            if not self._is_safe_identifier(tenant_id):
                logger.error(f"Invalid tenant_id format: {tenant_id}")
                return []

            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            table_name = sql.Identifier(f"company_brand_voices_{tenant_id.replace('-', '_')}")

            logger.info(f"Getting company brand voices from table: {table_name.string}")

            # First, ensure the table exists
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    brand_voice_id UUID PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    configuration JSON NOT NULL,
                    markdown_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """).format(table_name))

            # Commit the table creation before querying
            conn.commit()

            cursor.execute(sql.SQL("""
                SELECT * FROM {} ORDER BY created_at DESC
            """).format(table_name))

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
            # Validate tenant_id to prevent SQL injection
            if not self._is_safe_identifier(tenant_id):
                logger.error(f"Invalid tenant_id format: {tenant_id}")
                return []

            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            table_name = sql.Identifier(f"user_brand_voices_{tenant_id.replace('-', '_')}")
            cursor.execute(sql.SQL("""
                SELECT * FROM {} WHERE user_id = %s ORDER BY name
            """).format(table_name), (user_id,))

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
            # Validate tenant_id to prevent SQL injection
            if not self._is_safe_identifier(tenant_id):
                logger.error(f"Invalid tenant_id format: {tenant_id}")
                raise ValueError("Invalid tenant_id format")

            brand_voice_id = str(uuid.uuid4())

            conn = self.get_connection()
            cursor = conn.cursor()

            if user_id:
                # User brand voice
                table_name = sql.Identifier(f"user_brand_voices_{tenant_id.replace('-', '_')}")
                # Ensure table exists
                cursor.execute(sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {} (
                        brand_voice_id UUID PRIMARY KEY,
                        user_id UUID NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        configuration JSON NOT NULL,
                        markdown_content TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """).format(table_name))
                cursor.execute(sql.SQL("""
                    INSERT INTO {} (brand_voice_id, user_id, name, configuration, markdown_content)
                    VALUES (%s, %s, %s, %s, %s)
                """).format(table_name), (brand_voice_id, user_id, name, json.dumps(configuration), markdown_content))
            else:
                # Company brand voice
                table_name = sql.Identifier(f"company_brand_voices_{tenant_id.replace('-', '_')}")
                # Ensure table exists
                cursor.execute(sql.SQL("""
                    CREATE TABLE IF NOT EXISTS {} (
                        brand_voice_id UUID PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        configuration JSON NOT NULL,
                        markdown_content TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """).format(table_name))
                cursor.execute(sql.SQL("""
                    INSERT INTO {} (brand_voice_id, name, configuration, markdown_content)
                    VALUES (%s, %s, %s, %s)
                """).format(table_name), (brand_voice_id, name, json.dumps(configuration), markdown_content))

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
            # Validate tenant_id to prevent SQL injection
            if not self._is_safe_identifier(tenant_id):
                logger.error(f"Invalid tenant_id format: {tenant_id}")
                raise ValueError("Invalid tenant_id format")

            name = wizard_data['voice_short_name']
            configuration = wizard_data.copy()

            conn = self.get_connection()
            cursor = conn.cursor()

            if user_id:
                # User brand voice
                table_name = sql.Identifier(f"user_brand_voices_{tenant_id.replace('-', '_')}")
                cursor.execute(sql.SQL("""
                    UPDATE {} 
                    SET name = %s, configuration = %s, markdown_content = %s
                    WHERE brand_voice_id = %s AND user_id = %s
                """).format(table_name), (name, json.dumps(configuration), markdown_content, brand_voice_id, user_id))
            else:
                # Company brand voice
                table_name = sql.Identifier(f"company_brand_voices_{tenant_id.replace('-', '_')}")
                cursor.execute(sql.SQL("""
                    UPDATE {} 
                    SET name = %s, configuration = %s, markdown_content = %s
                    WHERE brand_voice_id = %s
                """).format(table_name), (name, json.dumps(configuration), markdown_content, brand_voice_id))

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
            # Validate tenant_id to prevent SQL injection
            if not self._is_safe_identifier(tenant_id):
                logger.error(f"Invalid tenant_id format: {tenant_id}")
                raise ValueError("Invalid tenant_id format")

            brand_voice_id = str(uuid.uuid4())
            name = wizard_data['voice_short_name']

            # Store the comprehensive wizard data as configuration
            configuration = wizard_data.copy()

            conn = self.get_connection()
            cursor = conn.cursor()

            # Always create as company brand voice now (ignoring user_id parameter)
            table_name = sql.Identifier(f"company_brand_voices_{tenant_id.replace('-', '_')}")

            # Ensure table exists
            cursor.execute(sql.SQL("""
                CREATE TABLE IF NOT EXISTS {} (
                    brand_voice_id UUID PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    configuration JSON NOT NULL,
                    markdown_content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """).format(table_name))

            cursor.execute(sql.SQL("""
                INSERT INTO {} (brand_voice_id, name, configuration, markdown_content)
                VALUES (%s, %s, %s, %s)
            """).format(table_name), (brand_voice_id, name, json.dumps(configuration), markdown_content))

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

    def delete_brand_voice(self, tenant_id: str, brand_voice_id: str, user_id: Optional[str] = None) -> bool:
        """Delete a brand voice"""
        try:
            # Validate tenant_id to prevent SQL injection
            if not self._is_safe_identifier(tenant_id):
                logger.error(f"Invalid tenant_id format: {tenant_id}")
                return False

            conn = self.get_connection()
            cursor = conn.cursor()

            if user_id:
                # User brand voice
                table_name = sql.Identifier(f"user_brand_voices_{tenant_id.replace('-', '_')}")
                cursor.execute(sql.SQL("""
                    DELETE FROM {} WHERE brand_voice_id = %s AND user_id = %s
                """).format(table_name), (brand_voice_id, user_id))
            else:
                # Company brand voice
                table_name = sql.Identifier(f"company_brand_voices_{tenant_id.replace('-', '_')}")
                cursor.execute(sql.SQL("""
                    DELETE FROM {} WHERE brand_voice_id = %s
                """).format(table_name), (brand_voice_id,))

            success = cursor.rowcount > 0
            conn.commit()
            cursor.close()
            conn.close()

            if success:
                logger.info(f"Successfully deleted brand voice {brand_voice_id} from tenant {tenant_id}")
            else:
                logger.warning(f"No brand voice found with ID {brand_voice_id} in tenant {tenant_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting brand voice: {e}")
            return False

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

                # Validate tenant_id to prevent SQL injection
                if not self._is_safe_identifier(tenant_id):
                    logger.error(f"Invalid tenant_id format: {tenant_id}")
                    return False

                # Delete user's brand voices from tenant-specific table
                table_name = sql.Identifier(f"user_brand_voices_{tenant_id.replace('-', '_')}")
                try:
                    cursor.execute(sql.SQL("DELETE FROM {} WHERE user_id = %s").format(table_name), (user_id,))
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
            # Validate tenant_id to prevent SQL injection
            if not self._is_safe_identifier(tenant_id):
                logger.error(f"Invalid tenant_id format: {tenant_id}")
                return False

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
                company_table = sql.Identifier(f"company_brand_voices_{table_prefix}")
                user_table = sql.Identifier(f"user_brand_voices_{table_prefix}")
                cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(company_table))
                cursor.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(user_table))
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

            success = cursor.rowcount > 0
            conn.commit()
            cursor.close()
            conn.close()
            return success
        except Exception as e:
            logger.error(f"Error updating user subscription: {e}")
            return False

    def update_user_stripe_info(self, user_id: str, stripe_customer_id: str = None, 
                               stripe_subscription_id: str = None, subscription_status: str = None,
                               current_period_end: datetime = None) -> bool:
        """Update user's Stripe information"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Build dynamic query based on provided parameters
            updates = []
            params = []

            if stripe_customer_id is not None:
                updates.append("stripe_customer_id = %s")
                params.append(stripe_customer_id)

            if stripe_subscription_id is not None:
                updates.append("stripe_subscription_id = %s")
                params.append(stripe_subscription_id)

            if subscription_status is not None:
                updates.append("subscription_status = %s")
                params.append(subscription_status)

            if current_period_end is not None:
                updates.append("current_period_end = %s")
                params.append(current_period_end)

            if not updates:
                return True

            params.append(user_id)
            query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = %s"

            cursor.execute(query, params)
            success = cursor.rowcount > 0
            conn.commit()
            cursor.close()
            conn.close()
            return success
        except Exception as e:
            logger.error(f"Error updating user Stripe info: {e}")
            return False

    def get_user_by_stripe_customer_id(self, stripe_customer_id: str) -> Optional[User]:
        """Get user by Stripe customer ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT * FROM users WHERE stripe_customer_id = %s
            """, (stripe_customer_id,))

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
                user.email_verified = row.get('email_verified', False)
                user.created_at = row.get('created_at')
                user.last_login = row.get('last_login')
                user.stripe_customer_id = row.get('stripe_customer_id')
                user.stripe_subscription_id = row.get('stripe_subscription_id')
                user.subscription_status = row.get('subscription_status', 'free')
                user.current_period_end = row.get('current_period_end')
                user.plan_id = row.get('plan_id', row['subscription_level'])  # Ensure plan_id matches subscription_level
                return user
            return None

        except Exception as e:
            logger.error(f"Error getting user by Stripe customer ID: {e}")
            return None

    def execute_query(self, query: str, params: tuple = None) -> list:
        """Execute a query and return results"""
        conn = self.get_connection()
        if not conn:
            return []

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)

                # If it's a SELECT query, fetch results
                if query.strip().upper().startswith('SELECT'):
                    return cursor.fetchall()
                else:
                    # For INSERT, UPDATE, DELETE, return number of affected rows
                    conn.commit()
                    return cursor.rowcount

        except Exception as e:
            logger.error(f"Database error executing query: {e}")
            conn.rollback()
            return []
        finally:
            conn.close()

    def execute_script(self, script: str) -> bool:
        """Execute a multi-statement SQL script"""
        conn = self.get_connection()
        if not conn:
            return False

        try:
            with conn.cursor() as cursor:
                cursor.execute(script)
                conn.commit()
                logger.info("SQL script executed successfully")
                return True

        except Exception as e:
            logger.error(f"Database error executing script: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def populate_pricing_plans(self):
        """Populate pricing plans if they don't exist"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Check if pricing plans already exist
            cursor.execute("SELECT COUNT(*) FROM pricing_plans")
            count = cursor.fetchone()[0]

            if count > 0:
                logger.info(f"Found {count} existing pricing plans")
                cursor.close()
                conn.close()
                return

            # Insert default pricing plans with the correct column structure
            plans = [
                ('free', 'The Companion', 'Ideal for trying out the service with basic features.', 0, 0, 20000, 10, 0, 'none'),
                ('solo', 'The Practitioner', 'Perfect for individual professionals needing advanced features.', 29, 290, 200000, -1, 1, 'email'),
                ('team', 'The Organization', 'Built for small teams to collaborate and manage AI usage.', 39, 390, 250000, -1, 10, 'priority'),
                ('professional', 'The Powerhouse', 'For businesses requiring extensive AI capabilities and dedicated support.', 82, 820, 1000000, -1, 10, 'top_priority')
            ]

            for plan in plans:
                cursor.execute("""
                    INSERT INTO pricing_plans 
                    (plan_id, name, core_value, price_monthly, price_annual, token_limit, chat_history_limit, brand_voices, support_level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, plan)

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"Populated {len(plans)} pricing plans")

        except Exception as e:
            logger.error(f"Error populating pricing plans: {e}")
            if 'conn' in locals():
                conn.rollback()
                cursor.close()
                conn.close()


    def get_all_pricing_plans(self) -> List[Dict]:
        """Get all pricing plans"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT plan_id, name, core_value, price_monthly, price_annual, 
                       token_limit, chat_history_limit, brand_voices, support_level
                FROM pricing_plans 
                ORDER BY price_monthly ASC
            """)

            plans = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()

            return plans

        except Exception as e:
            logger.error(f"Error getting pricing plans: {e}")
            return []

    def get_user_plan(self, user_id: str) -> Optional[Dict]:
        """Get user's current plan and limits"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT u.subscription_level, p.name as plan_name, p.display_name, p.core_value, p.price_monthly, p.token_limit, 
                       p.chat_history_limit, p.brand_voices, p.support_level
                FROM users u
                LEFT JOIN pricing_plans p ON u.subscription_level::text = p.plan_id
                WHERE u.user_id = %s
            """, (user_id,))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            return dict(result) if result else None

        except Exception as e:
            logger.error(f"Error getting user plan: {e}")
            return None

    def get_user_token_usage(self, user_id: str) -> Optional[Dict]:
        """Get user's token usage"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Reset monthly usage if new month
            current_month = datetime.now().month
            current_year = datetime.now().year

            cursor.execute("""
                UPDATE user_token_usage 
                SET tokens_used_month = 0, current_month = %s, current_year = %s, last_reset = CURRENT_TIMESTAMP
                WHERE user_id = %s AND (current_month != %s OR current_year != %s)
            """, (current_month, current_year, user_id, current_month, current_year))

            # Get or create usage record
            cursor.execute("""
                INSERT INTO user_token_usage (user_id, current_month, current_year)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """, (user_id, current_month, current_year))

            cursor.execute("""
                SELECT * FROM user_token_usage WHERE user_id = %s
            """, (user_id,))

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            if result:
                return dict(result)
            return None

        except Exception as e:
            logger.error(f"Error getting user token usage: {e}")
            return None

    def check_user_limits(self, user_id: str, content_mode: str, estimated_tokens: int) -> Dict:
        """Check if user can perform the requested action within their limits"""
        try:
            plan = self.get_user_plan(user_id)
            usage = self.get_user_token_usage(user_id)

            # If we can't get plan/usage data, allow the request to proceed (fail open for better UX)
            if not plan:
                logger.warning(f"Could not get plan for user {user_id}, allowing request")
                return {'allowed': True}

            if not usage:
                logger.warning(f"Could not get usage for user {user_id}, allowing request")
                return {'allowed': True}

            # Check token limits
            token_limit = plan.get('token_limit', 20000)
            if token_limit != -1:  # -1 means unlimited
                current_usage = usage.get('tokens_used_month', 0)
                if current_usage + estimated_tokens > token_limit:
                    return {'allowed': False, 'error': f'Monthly token limit exceeded ({current_usage}/{token_limit})'}

            return {'allowed': True}

        except Exception as e:
            logger.error(f"Error checking user limits for user {user_id}: {e}")
            # Fail open - allow the request to proceed rather than blocking users
            logger.warning(f"Allowing request for user {user_id} due to limits check error")
            return {'allowed': True}

    def update_user_token_usage(self, user_id: str, tokens_used: int) -> bool:
        """Update user's token usage"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE user_token_usage 
                SET tokens_used_month = tokens_used_month + %s,
                    tokens_used_total = tokens_used_total + %s
                WHERE user_id = %s
            """, (tokens_used, tokens_used, user_id))

            success = cursor.rowcount > 0
            conn.commit()
            cursor.close()
            conn.close()
            return success

        except Exception as e:
            logger.error(f"Error updating user token usage: {e}")
            return False

    def create_chat_session(self, user_id: str, title: str = "New Chat") -> Optional[str]:
        """Create a new chat session"""
        try:
            import uuid
            session_id = str(uuid.uuid4())

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO chat_sessions (session_id, user_id, title)
                VALUES (%s, %s, %s)
            """, (session_id, user_id, title))

            conn.commit()
            cursor.close()
            conn.close()
            return session_id

        except Exception as e:
            logger.error(f"Error creating chat session: {e}")
            return None

    def get_user_chat_sessions(self, user_id: str) -> List[Dict]:
        """Get user's chat sessions"""
        try:
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
            """, (user_id,))

            sessions = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return sessions

        except Exception as e:
            logger.error(f"Error getting user chat sessions: {e}")
            return []

    def get_chat_messages(self, session_id: str) -> List[Dict]:
        """Get messages for a chat session"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT * FROM chat_messages 
                WHERE session_id = %s 
                ORDER BY created_at ASC
            """, (session_id,))

            messages = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return messages

        except Exception as e:
            logger.error(f"Error getting chat messages: {e}")
            return []

    def add_chat_message(self, session_id: str, message_type: str, content: str, content_mode: str = None, brand_voice_id: str = None) -> bool:
        """Add a message to a chat session"""
        try:
            import uuid
            message_id = str(uuid.uuid4())

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO chat_messages (message_id, session_id, message_type, content, content_mode, brand_voice_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (message_id, session_id, message_type, content, content_mode, brand_voice_id))

            # Update session's updated_at timestamp
            cursor.execute("""
                UPDATE chat_sessions 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE session_id = %s
            """, (session_id,))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error adding chat message: {e}")
            return False

    def update_chat_session_title(self, session_id: str, title: str) -> bool:
        """Update chat session title"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE chat_sessions 
                SET title = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE session_id = %s
            """, (title, session_id))

            success = cursor.rowcount > 0
            conn.commit()
            cursor.close()
            conn.close()
            return success

        except Exception as e:
            logger.error(f"Error updating chat session title: {e}")
            return False

    def delete_chat_session(self, session_id: str, user_id: str) -> bool:
        """Delete a chat session and its messages"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Verify session belongs to user
            cursor.execute("""
                DELETE FROM chat_sessions 
                WHERE session_id = %s AND user_id = %s
            """, (session_id, user_id))

            success = cursor.rowcount > 0
            conn.commit()
            cursor.close()
            conn.close()
            return success

        except Exception as e:
            logger.error(f"Error deleting chat session: {e}")
            return False

    def create_organization_invite(self, tenant_id: str, invited_by_user_id: str, email: str, token_hash: str) -> bool:
        """Create an organization invite"""
        try:
            expires_at = datetime.utcnow() + timedelta(days=7)  # 7 days to accept

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO organization_invite_tokens (tenant_id, invited_by_user_id, email, token_hash, expires_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (tenant_id, invited_by_user_id, email, token_hash, expires_at))

            conn.commit()
            cursor.close()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error creating organization invite: {e}")
            return False

    def verify_organization_invite_token(self, token_hash: str) -> Optional[tuple]:
        """Verify organization invite token and return tenant_id and email"""
        try:
            logger.info(f"🔍 DATABASE VERIFICATION DEBUG:")
            logger.info(f"  Token hash: {token_hash}")
            logger.info(f"  Current time: {datetime.utcnow()}")
            
            conn = self.get_connection()
            cursor = conn.cursor()

            # First, let's check if the token exists at all
            cursor.execute("""
                SELECT tenant_id, email, expires_at, used FROM organization_invite_tokens 
                WHERE token_hash = %s
            """, (token_hash,))
            
            all_rows = cursor.fetchall()
            logger.info(f"  All matching tokens: {all_rows}")
            
            # Now check for valid tokens
            cursor.execute("""
                SELECT tenant_id, email FROM organization_invite_tokens 
                WHERE token_hash = %s AND expires_at > %s AND used = FALSE
            """, (token_hash, datetime.utcnow()))

            row = cursor.fetchone()
            cursor.close()
            conn.close()
            
            logger.info(f"  Valid token result: {row}")

            if row:
                return (str(row[0]), row[1])
            return None

        except Exception as e:
            logger.error(f"🚨 DATABASE VERIFICATION ERROR: {e}")
            import traceback
            logger.error(f"🚨 DATABASE ERROR TRACEBACK: {traceback.format_exc()}")
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

            success = cursor.rowcount > 0
            conn.commit()
            cursor.close()
            conn.close()
            return success

        except Exception as e:
            logger.error(f"Error marking organization invite token as used: {e}")
            return False

    def get_pending_invites(self, tenant_id: str) -> List[Dict]:
        """Get pending organization invites for a tenant"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            cursor.execute("""
                SELECT email, created_at, expires_at
                FROM organization_invite_tokens
                WHERE tenant_id = %s AND used = FALSE AND expires_at > %s
                ORDER BY created_at DESC
            """, (tenant_id, datetime.utcnow()))

            invites = [dict(row) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            return invites

        except Exception as e:
            logger.error(f"Error getting pending invites: {e}")
            return []

    def get_invitation_statistics(self):
        """Get invitation and signup statistics from database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Total invitations sent by type
            cursor.execute("""
                SELECT invitation_type, COUNT(*) AS total_sent
                FROM invitations
                GROUP BY invitation_type
                ORDER BY invitation_type;
            """)
            invitations_by_type = [dict(row) for row in cursor.fetchall()]

            # Pending vs accepted invitations
            cursor.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending_invitations,
                    COUNT(*) FILTER (WHERE status = 'accepted') AS accepted_invitations,
                    COUNT(*) FILTER (WHERE status = 'declined') AS declined_invitations
                FROM invitations;
            """)
            status_counts = dict(cursor.fetchone() or {})

            # Recent signups with their source
            cursor.execute("""
                SELECT user_email, signup_source, signup_date
                FROM user_sources
                ORDER BY signup_date DESC
                LIMIT 10; 
            """)
            recent_signups = [dict(row) for row in cursor.fetchall()]

            # List of pending invitations
            cursor.execute("""
                SELECT invite_code, invitee_email, invitation_type, created_at
                FROM invitations
                WHERE status = 'pending'
                ORDER BY created_at DESC
                LIMIT 10;
            """)
            pending_invitations_list = [dict(row) for row in cursor.fetchall()]

            cursor.close()
            conn.close()

            return {
                'invitations_by_type': invitations_by_type,
                'status_counts': status_counts,
                'recent_signups': recent_signups,
                'pending_invitations_list': pending_invitations_list
            }

        except Exception as e:
            logger.error(f"Database error getting invitation statistics: {e}")
            return {
                'invitations_by_type': [],
                'status_counts': {},
                'recent_signups': [],
                'pending_invitations_list': [],
                'error': str(e)
            }


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