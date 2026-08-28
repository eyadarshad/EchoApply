-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (integrates with Supabase Auth or can be used standalone)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    major TEXT,
    location TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Profiles table (one profile per user)
CREATE TABLE IF NOT EXISTS profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    parsed_resume_json JSONB DEFAULT '{}'::jsonb,
    github_json JSONB DEFAULT '{}'::jsonb,
    linkedin_json JSONB DEFAULT '{}'::jsonb,
    portfolio_json JSONB DEFAULT '{}'::jsonb,
    profile_embedding vector(768),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    remote BOOLEAN DEFAULT FALSE,
    jd_text TEXT NOT NULL,
    apply_url TEXT,
    jd_embedding vector(768),
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    job_hash TEXT UNIQUE NOT NULL
);

-- Index for job_hash lookup and similarity searches
CREATE INDEX IF NOT EXISTS idx_jobs_job_hash ON jobs(job_hash);

-- Applications table (tracks user applications and prevents double applying)
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    job_hash TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    applied_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_job_hash UNIQUE (user_id, job_hash)
);

-- Indexes for quick application checks
CREATE INDEX IF NOT EXISTS idx_applications_user_hash ON applications(user_id, job_hash);

-- Tailored Resumes table
CREATE TABLE IF NOT EXISTS tailored_resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    content_json JSONB NOT NULL,
    pdf_path TEXT,
    docx_path TEXT,
    ats_score INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Technique Library table
CREATE TABLE IF NOT EXISTS technique_library (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    technique TEXT NOT NULL,
    applies_to_major TEXT[] NOT NULL, -- list of majors it applies to
    reader_weight REAL DEFAULT 1.0,  -- Weight: ATS-optimized vs human-oriented
    source_url TEXT,
    last_verified TIMESTAMPTZ DEFAULT NOW()
);

-- Job Cache table
CREATE TABLE IF NOT EXISTS job_cache (
    query_hash TEXT PRIMARY KEY,
    results_json JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

-- Create index for cache cleanup
CREATE INDEX IF NOT EXISTS idx_job_cache_expires_at ON job_cache(expires_at);

-- Saved Searches (Job Alerts)
CREATE TABLE IF NOT EXISTS saved_searches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    keywords TEXT NOT NULL,
    location TEXT,
    alert_interval TEXT DEFAULT 'weekly',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_saved_searches_user ON saved_searches(user_id);

-- Platform Credentials (encrypted session cookies)
CREATE TABLE IF NOT EXISTS platform_credentials (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    cookies_encrypted TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, platform)
);
