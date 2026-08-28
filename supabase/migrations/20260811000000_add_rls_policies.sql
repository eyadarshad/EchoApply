-- Enable RLS on all user-owned tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;
ALTER TABLE tailored_resumes ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE platform_credentials ENABLE ROW LEVEL SECURITY;

-- Users: own row only
CREATE POLICY "Users can view own record" ON users
  FOR SELECT USING (id = auth.uid());
CREATE POLICY "Users can update own record" ON users
  FOR UPDATE USING (id = auth.uid());

-- Profiles: own row only
CREATE POLICY "Users can view own profile" ON profiles
  FOR ALL USING (user_id = auth.uid());

-- Applications: own rows only
CREATE POLICY "Users can manage own applications" ON applications
  FOR ALL USING (user_id = auth.uid());

-- Tailored resumes: own rows only
CREATE POLICY "Users can manage own tailored resumes" ON tailored_resumes
  FOR ALL USING (user_id = auth.uid());

-- Saved searches: own rows only
CREATE POLICY "Users can manage own alerts" ON saved_searches
  FOR ALL USING (user_id = auth.uid());

-- Platform credentials: own rows only (CRITICAL)
CREATE POLICY "Users can manage own credentials" ON platform_credentials
  FOR ALL USING (user_id = auth.uid());

-- Jobs table: public read (no user_id column)
-- Backend service role writes; all users can read job listings
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can read jobs" ON jobs FOR SELECT USING (true);
CREATE POLICY "Service role can write jobs" ON jobs
  FOR ALL USING (auth.role() = 'service_role');

-- Job cache: service role only
ALTER TABLE job_cache ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role manages cache" ON job_cache
  FOR ALL USING (auth.role() = 'service_role');
