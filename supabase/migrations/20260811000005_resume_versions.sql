CREATE TABLE IF NOT EXISTS resume_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    parsed_resume_json JSONB NOT NULL,
    source TEXT DEFAULT 'upload',  -- 'upload', 'edit', 'tailor'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, version_number)
);

-- Link applications to specific resume versions if not already done
ALTER TABLE applications ADD COLUMN IF NOT EXISTS resume_version_id UUID REFERENCES resume_versions(id) ON DELETE SET NULL;

-- Enable RLS
ALTER TABLE resume_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own resume versions" ON resume_versions
  FOR ALL USING (user_id = auth.uid());
