-- Migration: Create audit_history table for CV and LinkedIn audit score tracking
CREATE TABLE IF NOT EXISTS audit_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    audit_type TEXT NOT NULL CHECK (audit_type IN ('cv', 'linkedin')),
    total_score INTEGER NOT NULL,
    max_score INTEGER NOT NULL DEFAULT 100,
    quality_label TEXT NOT NULL,
    dimensions JSONB NOT NULL,
    top_3_changes JSONB,
    target_role TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_history_user ON audit_history(user_id, audit_type, created_at DESC);
