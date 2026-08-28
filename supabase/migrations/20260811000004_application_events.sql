CREATE TABLE IF NOT EXISTS application_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT,
    actor TEXT NOT NULL,  -- 'user', 'system', 'ai'
    payload JSONB DEFAULT '{}',
    model_version TEXT,
    resume_version_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_app_events_app ON application_events(application_id, created_at);

-- Enable RLS
ALTER TABLE application_events ENABLE ROW LEVEL SECURITY;

-- Allow users to manage only events for their own applications
CREATE POLICY "Users can manage own application events" ON application_events
  FOR ALL USING (
    application_id IN (
      SELECT id FROM applications WHERE user_id = auth.uid()
    )
  );
