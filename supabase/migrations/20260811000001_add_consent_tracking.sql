CREATE TABLE IF NOT EXISTS user_consents (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL,  -- 'data_processing', 'ai_processing', 'credential_storage', 'analytics'
    granted BOOLEAN NOT NULL DEFAULT FALSE,
    granted_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    ip_address TEXT,
    PRIMARY KEY (user_id, consent_type)
);

-- Enable RLS
ALTER TABLE user_consents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own consent" ON user_consents
  FOR ALL USING (user_id = auth.uid());
