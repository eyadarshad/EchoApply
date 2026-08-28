-- Create the application_status enum type
DO $$ BEGIN
    CREATE TYPE application_status AS ENUM (
        'discovered', 'saved', 'tailoring', 'ready_to_apply',
        'user_review', 'applied', 'confirmation_pending',
        'confirmed', 'failed', 'needs_action', 'withdrawn',
        'rejected', 'interview', 'offer', 'accepted'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Alter applications status column type
ALTER TABLE applications 
    ALTER COLUMN status TYPE TEXT; -- Temp fallback/conversion to avoid type mismatch, or convert directly

-- Since existing statuses might be strings like 'pending', we will clean/map them
UPDATE applications SET status = 'ready_to_apply' WHERE status = 'pending';
UPDATE applications SET status = 'applied' WHERE status NOT IN (
    'discovered', 'saved', 'tailoring', 'ready_to_apply',
    'user_review', 'applied', 'confirmation_pending',
    'confirmed', 'failed', 'needs_action', 'withdrawn',
    'rejected', 'interview', 'offer', 'accepted'
);

ALTER TABLE applications 
    ALTER COLUMN status TYPE application_status USING status::application_status,
    ALTER COLUMN status SET DEFAULT 'discovered'::application_status;
