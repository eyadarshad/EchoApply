CREATE TABLE IF NOT EXISTS usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,  -- 'llm_call', 'pdf_generation', 'job_search', 'tailor'
    tokens_used INTEGER DEFAULT 0,
    cost_usd NUMERIC(10,6) DEFAULT 0,
    model TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_user_date ON usage_records(user_id, created_at);

-- Enable RLS
ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own usage records" ON usage_records
  FOR SELECT USING (user_id = auth.uid());
