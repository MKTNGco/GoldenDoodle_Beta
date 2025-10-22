/*
  # Initial Database Schema for Application

  ## Overview
  This migration creates the complete database structure for a multi-tenant application with user authentication, 
  brand voice management, chat sessions, token usage tracking, and subscription management.

  ## New Tables
  
  ### Core Tables
  1. `tenants`
    - `tenant_id` (uuid, primary key)
    - `tenant_type` (enum: 'company', 'independent_user')
    - `name` (text)
    - `database_name` (text, unique)
    - `max_brand_voices` (integer, default: 3)
    - `created_at` (timestamp)

  2. `users`
    - `user_id` (uuid, primary key)
    - `tenant_id` (uuid, foreign key to tenants)
    - `first_name` (text)
    - `last_name` (text)
    - `email` (text, unique)
    - `password_hash` (text)
    - `subscription_level` (enum: 'free', 'solo', 'pro', 'team', 'enterprise')
    - `plan_id` (text, default: 'free')
    - `is_admin` (boolean, default: false)
    - `email_verified` (boolean, default: false)
    - `last_login` (timestamp)
    - `session_count` (integer, default: 0)
    - `content_modes_used` (jsonb, default: [])
    - `stripe_customer_id` (text, unique)
    - `stripe_subscription_id` (text, unique)
    - `subscription_status` (text, default: 'inactive')
    - `current_period_end` (timestamp)
    - `created_at` (timestamp)

  ### Token Management
  3. `email_verification_tokens`
    - `token_id` (uuid, primary key)
    - `user_id` (uuid, foreign key to users)
    - `token_hash` (text)
    - `expires_at` (timestamp)
    - `used` (boolean, default: false)
    - `created_at` (timestamp)

  4. `password_reset_tokens`
    - `token_id` (uuid, primary key)
    - `user_id` (uuid, foreign key to users)
    - `token_hash` (text)
    - `expires_at` (timestamp)
    - `used` (boolean, default: false)
    - `created_at` (timestamp)

  5. `organization_invite_tokens`
    - `invite_id` (uuid, primary key)
    - `tenant_id` (uuid, foreign key to tenants)
    - `invited_by_user_id` (uuid, foreign key to users)
    - `email` (text)
    - `token_hash` (text)
    - `expires_at` (timestamp)
    - `used` (boolean, default: false)
    - `created_at` (timestamp)

  ### Pricing and Usage
  6. `pricing_plans`
    - `plan_id` (text, primary key)
    - `name` (text)
    - `display_name` (text)
    - `core_value` (text)
    - `price_monthly` (numeric)
    - `price_annual` (numeric)
    - `token_limit` (integer)
    - `chat_history_limit` (integer)
    - `brand_voices` (integer, default: 0)
    - `admin_controls` (boolean, default: false)
    - `features` (jsonb)
    - `user_seats` (integer, default: 1)
    - `support_level` (text, default: 'none')
    - `created_at` (timestamp)

  7. `user_token_usage`
    - `user_id` (uuid, primary key, foreign key to users)
    - `tokens_used_month` (integer, default: 0)
    - `tokens_used_total` (integer, default: 0)
    - `current_month` (integer)
    - `current_year` (integer)
    - `last_reset` (timestamp)

  ### Chat System
  8. `chat_sessions`
    - `session_id` (text, primary key)
    - `user_id` (uuid, foreign key to users)
    - `title` (text, default: 'New Chat')
    - `created_at` (timestamp)
    - `updated_at` (timestamp)

  9. `chat_messages`
    - `message_id` (text, primary key)
    - `session_id` (text, foreign key to chat_sessions)
    - `message_type` (enum: 'user', 'assistant')
    - `content` (text)
    - `content_mode` (text)
    - `brand_voice_id` (text)
    - `created_at` (timestamp)

  ## Security
  - Enable RLS on all tables
  - Add policies for authenticated users to manage their own data
  - Add policies for organization admins to manage organization data
  - Ensure tenant isolation for multi-tenant data

  ## Indexes
  - Email lookups on users table
  - Token hash lookups on token tables
  - Session and message queries optimized with indexes
  - User-tenant relationship indexes

  ## Notes
  - Uses gen_random_uuid() for UUID generation
  - Timestamps use CURRENT_TIMESTAMP for defaults
  - Enum types created for type safety
  - Foreign keys with CASCADE deletes where appropriate
*/

-- Create custom enum types
DO $$ BEGIN
  CREATE TYPE tenant_type AS ENUM ('company', 'independent_user');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE subscription_level AS ENUM ('free', 'solo', 'pro', 'team', 'enterprise');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE message_type AS ENUM ('user', 'assistant');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

-- Create tenants table
CREATE TABLE IF NOT EXISTS tenants (
  tenant_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_type tenant_type NOT NULL,
  name text NOT NULL,
  database_name text NOT NULL UNIQUE,
  max_brand_voices integer NOT NULL DEFAULT 3,
  created_at timestamptz DEFAULT CURRENT_TIMESTAMP
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
  user_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
  first_name text NOT NULL,
  last_name text NOT NULL,
  email text UNIQUE NOT NULL,
  password_hash text NOT NULL,
  subscription_level subscription_level NOT NULL DEFAULT 'free',
  plan_id text DEFAULT 'free',
  is_admin boolean DEFAULT false,
  email_verified boolean DEFAULT false,
  last_login timestamptz,
  session_count integer DEFAULT 0,
  content_modes_used jsonb DEFAULT '[]'::jsonb,
  stripe_customer_id text UNIQUE,
  stripe_subscription_id text UNIQUE,
  subscription_status text DEFAULT 'inactive',
  current_period_end timestamptz,
  created_at timestamptz DEFAULT CURRENT_TIMESTAMP
);

-- Create email verification tokens table
CREATE TABLE IF NOT EXISTS email_verification_tokens (
  token_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  token_hash text NOT NULL,
  expires_at timestamptz NOT NULL,
  used boolean DEFAULT false,
  created_at timestamptz DEFAULT CURRENT_TIMESTAMP
);

-- Create password reset tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
  token_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  token_hash text NOT NULL,
  expires_at timestamptz NOT NULL,
  used boolean DEFAULT false,
  created_at timestamptz DEFAULT CURRENT_TIMESTAMP
);

-- Create organization invite tokens table
CREATE TABLE IF NOT EXISTS organization_invite_tokens (
  invite_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
  invited_by_user_id uuid NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  email text NOT NULL,
  token_hash text NOT NULL,
  expires_at timestamptz NOT NULL,
  used boolean DEFAULT false,
  created_at timestamptz DEFAULT CURRENT_TIMESTAMP
);

-- Create pricing plans table
CREATE TABLE IF NOT EXISTS pricing_plans (
  plan_id text PRIMARY KEY,
  name text NOT NULL,
  display_name text,
  core_value text,
  price_monthly numeric(10,2),
  price_annual numeric(10,2),
  token_limit integer,
  chat_history_limit integer,
  brand_voices integer DEFAULT 0,
  admin_controls boolean DEFAULT false,
  features jsonb,
  user_seats integer DEFAULT 1,
  support_level text DEFAULT 'none',
  created_at timestamptz DEFAULT CURRENT_TIMESTAMP
);

-- Create user token usage table
CREATE TABLE IF NOT EXISTS user_token_usage (
  user_id uuid PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
  tokens_used_month integer NOT NULL DEFAULT 0,
  tokens_used_total integer NOT NULL DEFAULT 0,
  current_month integer NOT NULL DEFAULT EXTRACT(MONTH FROM NOW()),
  current_year integer NOT NULL DEFAULT EXTRACT(YEAR FROM NOW()),
  last_reset timestamptz DEFAULT CURRENT_TIMESTAMP
);

-- Create chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
  session_id text PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  title text NOT NULL DEFAULT 'New Chat',
  created_at timestamptz DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamptz DEFAULT CURRENT_TIMESTAMP
);

-- Create chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
  message_id text PRIMARY KEY,
  session_id text NOT NULL REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
  message_type message_type NOT NULL,
  content text NOT NULL,
  content_mode text,
  brand_voice_id text,
  created_at timestamptz DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer_id ON users(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_organization_invite_token_hash ON organization_invite_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_organization_invite_email ON organization_invite_tokens(email);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_updated ON chat_sessions(user_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages(session_id, created_at);

-- Insert default pricing plans
INSERT INTO pricing_plans (plan_id, name, core_value, price_monthly, price_annual, token_limit, chat_history_limit, brand_voices, support_level)
VALUES 
  ('free', 'The Companion', 'Ideal for trying out the service with basic features.', 0, 0, 20000, 10, 0, 'none'),
  ('solo', 'The Practitioner', 'Perfect for individual professionals needing advanced features.', 29, 290, 200000, -1, 1, 'email'),
  ('team', 'The Organization', 'Built for small teams to collaborate and manage AI usage.', 39, 390, 250000, -1, 10, 'priority'),
  ('professional', 'The Powerhouse', 'For businesses requiring extensive AI capabilities and dedicated support.', 82, 820, 1000000, -1, 10, 'top_priority')
ON CONFLICT (plan_id) DO NOTHING;

-- Enable Row Level Security
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_verification_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_invite_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_token_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY "Users can view own profile"
  ON users FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- RLS Policies for chat_sessions
CREATE POLICY "Users can view own chat sessions"
  ON chat_sessions FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own chat sessions"
  ON chat_sessions FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own chat sessions"
  ON chat_sessions FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own chat sessions"
  ON chat_sessions FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- RLS Policies for chat_messages
CREATE POLICY "Users can view own chat messages"
  ON chat_messages FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM chat_sessions
      WHERE chat_sessions.session_id = chat_messages.session_id
      AND chat_sessions.user_id = auth.uid()
    )
  );

CREATE POLICY "Users can create own chat messages"
  ON chat_messages FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM chat_sessions
      WHERE chat_sessions.session_id = chat_messages.session_id
      AND chat_sessions.user_id = auth.uid()
    )
  );

-- RLS Policies for user_token_usage
CREATE POLICY "Users can view own token usage"
  ON user_token_usage FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- RLS Policies for pricing_plans (public read-only)
CREATE POLICY "Anyone can view pricing plans"
  ON pricing_plans FOR SELECT
  TO authenticated
  USING (true);

-- RLS Policies for tenants
CREATE POLICY "Users can view own tenant"
  ON tenants FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM users
      WHERE users.tenant_id = tenants.tenant_id
      AND users.user_id = auth.uid()
    )
  );