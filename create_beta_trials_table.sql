
-- Create beta_trials table
CREATE TABLE IF NOT EXISTS beta_trials (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    invite_code VARCHAR(20) NULL,
    trial_start TIMESTAMP NOT NULL,
    trial_end TIMESTAMP NOT NULL,
    trial_days INTEGER NOT NULL,
    trial_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expired_at TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_beta_trials_user_email ON beta_trials(user_email);
CREATE INDEX IF NOT EXISTS idx_beta_trials_user_id ON beta_trials(user_id);
CREATE INDEX IF NOT EXISTS idx_beta_trials_status ON beta_trials(status);
CREATE INDEX IF NOT EXISTS idx_beta_trials_trial_type ON beta_trials(trial_type);
CREATE INDEX IF NOT EXISTS idx_beta_trials_trial_end ON beta_trials(trial_end);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_beta_trials_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_beta_trials_updated_at 
    BEFORE UPDATE ON beta_trials 
    FOR EACH ROW 
    EXECUTE FUNCTION update_beta_trials_updated_at_column();
