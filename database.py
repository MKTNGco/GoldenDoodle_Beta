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

            # Create organization invite tokens table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS organization_invite_tokens (
                    invite_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    tenant_id UUID NOT NULL,
                    invited_by_user_id UUID NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    token_hash VARCHAR(255) NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
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
            logger.info("Main database initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing main database: {e}")
            raise

    def create_tenant_database(self, tenant: Tenant):
        """Create a tenant-specific database"""
        try:
            # Note: In a real Neon setup, you would create a separate database
            # For this implementation, we'll create tenant-specific tables in the main database
            # with tenant_id prefixes to simulate separate databases

            conn = self.get_connection()
            cursor = conn.cursor()

            # Create company brand voices table if it's a company tenant
            if tenant.tenant_type == TenantType.COMPANY:
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS company_brand_voices_{tenant.tenant_id.replace('-', '_')} (
                        brand_voice_id UUID PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        configuration JSON NOT NULL,
                        markdown_content TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

            # Create user brand voices table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS user_brand_voices_{tenant.tenant_id.replace('-', '_')} (
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
            logger.info(f"Tenant database created for {tenant.tenant_id}")

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
                # Add created_at if available
                if len(row) > 8:
                    user.created_at = row['created_at']
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
            cursor.execute(f"""
                SELECT * FROM {table_name} ORDER BY name
            """)

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            brand_voices = []
            for row in rows:
                brand_voices.append(BrandVoice(
                    brand_voice_id=str(row['brand_voice_id']),
                    name=row['name'],
                    configuration=row['configuration'],
                    markdown_content=row['markdown_content']
                ))

            return brand_voices

        except Exception as e:
            logger.error(f"Error getting company brand voices: {e}")
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
                cursor.execute(f"""
                    INSERT INTO {table_name} (brand_voice_id, user_id, name, configuration, markdown_content)
                    VALUES (%s, %s, %s, %s, %s)
                """, (brand_voice_id, user_id, name, json.dumps(configuration), markdown_content))
            else:
                # Company brand voice
                table_name = f"company_brand_voices_{tenant_id.replace('-', '_')}"
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
        """Create a comprehensive brand voice with full wizard data"""
        try:
            brand_voice_id = str(uuid.uuid4())
            name = wizard_data['voice_short_name']

            # Store the comprehensive wizard data as configuration
            configuration = wizard_data.copy()

            conn = self.get_connection()
            cursor = conn.cursor()

            if user_id:
                # User brand voice
                table_name = f"user_brand_voices_{tenant_id.replace('-', '_')}"
                cursor.execute(f"""
                    INSERT INTO {table_name} (brand_voice_id, user_id, name, configuration, markdown_content)
                    VALUES (%s, %s, %s, %s, %s)
                """, (brand_voice_id, user_id, name, json.dumps(configuration), markdown_content))
            else:
                # Company brand voice
                table_name = f"company_brand_voices_{tenant_id.replace('-', '_')}"
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
                       u.password_hash
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
                    password_hash=row[9]
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
            cursor.execute("DELETE FROM organization_invite_tokens WHERE tenant_id = %s", (tenant_id,))

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

    def get_pending_invites(self, tenant_id: str) -> List[dict]:
        """Get pending invites for an organization"""
        try:
            from datetime import datetime

            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT oit.email, oit.created_at, u.first_name, u.last_name
                FROM organization_invite_tokens oit
                JOIN users u ON oit.invited_by_user_id = u.user_id
                WHERE oit.tenant_id = %s AND oit.used = FALSE AND oit.expires_at > %s
                ORDER BY oit.created_at DESC
            """, (tenant_id, datetime.utcnow()))

            invites = []
            for row in cursor.fetchall():
                invites.append({
                    'email': row[0],
                    'created_at': row[1],
                    'invited_by': f"{row[2]} {row[3]}"
                })

            cursor.close()
            conn.close()
            return invites

        except Exception as e:
            logger.error(f"Error getting pending invites: {e}")
            return []

# Global database manager instance
db_manager = DatabaseManager()

def init_databases():
    """Initialize all databases"""
    db_manager.init_main_database()