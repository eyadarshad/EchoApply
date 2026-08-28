-- Add expires_at column to platform_credentials if it doesn't exist
ALTER TABLE platform_credentials ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

-- Update existing records to expire in 30 days
UPDATE platform_credentials SET expires_at = updated_at + INTERVAL '30 days' WHERE expires_at IS NULL;

-- Function to purge expired entries
CREATE OR REPLACE FUNCTION purge_expired_records() RETURNS void AS $$
BEGIN
    -- Purge expired platform credentials
    DELETE FROM platform_credentials WHERE expires_at < NOW();
    
    -- Purge expired job cache
    DELETE FROM job_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;
