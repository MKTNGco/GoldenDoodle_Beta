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
                    tenant_id UUID REFERENCES tenants(tenant_id),
                    first_name VARCHAR(255) NOT NULL,
                    last_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    subscription_level subscription_level NOT NULL,
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
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
                INSERT INTO users (user_id, tenant_id, first_name, last_name, email, password_hash, subscription_level, is_admin)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user.user_id, user.tenant_id, user.first_name, user.last_name, user.email, user.password_hash, 
                  user.subscription_level.value, user.is_admin))
            
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
                return User(
                    user_id=str(row['user_id']),
                    tenant_id=str(row['tenant_id']),
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    email=row['email'],
                    password_hash=row['password_hash'],
                    subscription_level=SubscriptionLevel(row['subscription_level']),
                    is_admin=row['is_admin']
                )
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
        """Verify user password"""
        return check_password_hash(user.password_hash, password)

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

# Global database manager instance
db_manager = DatabaseManager()

def init_databases():
    """Initialize all databases"""
    db_manager.init_main_database()
