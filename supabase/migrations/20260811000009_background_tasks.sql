CREATE TABLE IF NOT EXISTS background_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_type TEXT NOT NULL,  -- 'auto_apply', 'alert_check', 'tailor'
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'success', 'failed', 'needs_action'
    payload JSONB DEFAULT '{}',
    result JSONB DEFAULT '{}',
    logs TEXT[] DEFAULT '{}',
    error TEXT,
    priority INTEGER DEFAULT 0, -- 0=normal, 1=high
    retries INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bg_tasks_status ON background_tasks(status, priority DESC, created_at);

-- Enable RLS
ALTER TABLE background_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own background tasks" ON background_tasks
  FOR ALL USING (user_id = auth.uid());
