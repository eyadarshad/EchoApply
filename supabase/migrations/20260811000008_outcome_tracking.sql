ALTER TABLE applications ADD COLUMN IF NOT EXISTS outcome TEXT;  -- 'no_response', 'rejected', 'interview', 'offer'
ALTER TABLE applications ADD COLUMN IF NOT EXISTS outcome_at TIMESTAMPTZ;
ALTER TABLE applications ADD COLUMN IF NOT EXISTS interview_count INTEGER DEFAULT 0;
