-- Enable Row Level Security (RLS) on all tables that should be restricted
-- This script creates policies that tie each row to the authenticated user (auth.uid())

-- Helper function to generate policy statements
-- You can run this in Supabase SQL editor or via the Supabase CLI

-- Profiles table
CREATE POLICY "profiles_ownership_policy"
  ON profiles
  FOR SELECT
  USING (auth.uid() = user_id);

-- Residents table (if separate)
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
CREATE POLICY "historical_cases_ownership_policy"
  ON historical_cases
  USING (auth.uid() = user_id);

-- Case matches table
CREATE POLICY "case_match_members_ownership_policy"
  ON case_match_members
  USING (auth.uid() = user_id);

-- Case evidence (if separate)
CREATE POLICY "case_pagination_ownership_policy"
  ON latest_case_matches
  USING (auth.uid() = user_id);

-- Alert outcome spread table
CREATE POLICY "alert_outcome_spread_ownership_policy"
  ON latest_outcome_spread
  USING (auth.uid() = user_id);

-- Grant RLS enable on all tables (if not already enabled)
DO $$
BEGIN
  IF NOT EXISTS (SELECT * FROM pg_policies WHERE tablename = 'profiles') THEN
    ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
  END IF;
  IF NOT EXISTS (SELECT * FROM pg_policies WHERE tablename = 'care_notes') THEN
    ALTER TABLE care_notes ENABLE ROW LEVEL SECURITY;
  END IF;
  IF NOT EXISTS (SELECT * FROM pg_policies WHERE tablename = 'observations') THEN
    ALTER TABLE observations ENABLE ROW LEVEL SECURITY;
  END IF;
  IF NOT EXISTS (SELECT * FROM pg_policies WHERE tablename = 'alerts') THEN
    ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
  END IF;
  IF NOT EXISTS (SELECT * FROM pg_policies WHERE tablename = 'alert_evidence') THEN
    ALTER TABLE alert_evidence ENABLE ROW LEVEL SECURITY;
  END IF;
  IF NOT EXISTS (SELECT * FROM pg_policies WHERE tablename = 'historical_cases') THEN
    ALTER TABLE historical_cases ENABLE ROW LEVEL SECURITY;
  END IF;
  IF NOT EXISTS (SELECT * FROM pg_policies WHERE tablename = 'case_match_members') THEN
    ALTER TABLE case_match_members ENABLE ROW LEVEL SECURITY;
  END IF;
  IF NOT EXISTS (SELECT * FROM pg_policies WHERE tablename = 'alert_evidence') THEN
    ALTER TABLE alert_evidence ENABLE ROW LEVEL SECURITY;
  END IF;
END $$;