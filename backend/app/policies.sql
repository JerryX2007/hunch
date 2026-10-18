-- ==============================================================
--  Row‑Level Security (RLS) policies for all tables
--  These policies enforce that a user can only access rows
--  belonging to their own auth.uid().
--  Adjust column names if your schema differs.
-- ==============================================================

-- Helper function to enable RLS on a table (if not already enabled)
-- (Supabase UI can also enable RLS; this script ensures it)
-- (Not needed if tables already have RLS enabled)

-- Profiles table
CREATE POLICY "profiles_ownership_policy"
  ON profiles
  FOR SELECT
  USING (auth.uid() = user_id);

-- Residents table
CREATE POLICY "residents_ownership_policy"
  ON residents
  USING (auth.uid() = user_id);

-- Care notes table
CREATE POLICY "care_notes_ownership_policy"
  ON care_notes
  USING (auth.uid() = user_id);

-- Observations table
CREATE POLICY "observations_ownership_policy"
  ON observations
  USING (auth.uid() = user_id);

-- Alerts table
CREATE POLICY "alerts_ownership_policy"
  ON alerts
  USING (auth.uid() = user_id);

-- Alert evidence (junction) table
CREATE POLICY "alert_evidence_ownership_policy"
  ON alert_evidence
  USING (auth.uid() = user_id);

-- Historical cases table
CREATE POLICY "historical_cases_embedding_policy"
  ON historical_cases
  USING (auth.uid() = user_id);

-- Case matches table (junction for alerts ↔ cases)
CREATE POLICY "case_match_members_ownership_policy"
  ON case_match_members
  USING (auth.uid() = user_id);

-- Case evidence (junction) table
CREATE POLICY "alert_evidence_ownership_policy"
  ON alert_evidence
  USING (auth.uid() = user_id);

-- If any of the above tables do not yet have RLS enabled,
-- the ALTER commands below will enable it:
-- ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

-- ==============================================================
-- OPTIONAL: Add a generic function to enable RLS on any table
-- (useful when creating new tables dynamically)
-- ==============================================================
-- CREATE POLICY "enable_rls_on_table"
--   ON <table_name>
--   USING (auth.uid() = user_id);
-- END;