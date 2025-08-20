
-- Create invitations table
CREATE TABLE IF NOT EXISTS invitations (
    id SERIAL PRIMARY KEY,
    invite_code VARCHAR(20) UNIQUE NOT NULL,
    invitee_email VARCHAR(255) NOT NULL,
    organization_name VARCHAR(255) NOT NULL,
    invitation_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at TIMESTAMP NULL,
    expired_at TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create user_sources table
CREATE TABLE IF NOT EXISTS user_sources (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    signup_source VARCHAR(100) NOT NULL,
    invite_code VARCHAR(20) NULL,
    signup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tracked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invite_code) REFERENCES invitations(invite_code) ON DELETE SET NULL
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_invitations_code ON invitations(invite_code);
CREATE INDEX IF NOT EXISTS idx_invitations_email ON invitations(invitee_email);
CREATE INDEX IF NOT EXISTS idx_invitations_type ON invitations(invitation_type);
CREATE INDEX IF NOT EXISTS idx_invitations_status ON invitations(status);
CREATE INDEX IF NOT EXISTS idx_user_sources_email ON user_sources(user_email);
CREATE INDEX IF NOT EXISTS idx_user_sources_source ON user_sources(signup_source);
CREATE INDEX IF NOT EXISTS idx_user_sources_invite_code ON user_sources(invite_code);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_invitations_updated_at 
    BEFORE UPDATE ON invitations 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
