-- =============================================================================
-- Hunch: one-time update for the LIVE Supabase project (mbvvsziqpvozcijkhdiy)
-- Paste all of this into Supabase → SQL Editor → New query → Run.
--
-- What it does (same as db/migrations/005-008, combined):
--   005  creates eval_scenarios (test labels used by scripts/seed_db.py)
--   006  turns on row-level security everywhere: signed-in staff can read;
--        only the backend (service-role key) writes
--   007  lets alerts.status take the nurse review values
--        (open / reviewed / needs_assessment / dismissed)
--   008  staff can create/edit only their own profile
--
-- Safe to run more than once. All-or-nothing: if any statement fails, nothing changes.
-- No data is deleted or rewritten. Needs: backend/.env has SUPABASE_SERVICE_ROLE_KEY
-- (the backend reads/writes with it; it bypasses row-level security).
-- =============================================================================

begin;

-- ---------------------------------------------------------------------------
-- 005_eval_scenarios.sql
-- ---------------------------------------------------------------------------
-- Expected answers for the test residents (test_data/eval_scenarios.json).
-- Test labels only: the scorer never reads this table.

create table if not exists public.eval_scenarios (
  resident_id  text not null references public.residents (id) on delete cascade,
  scenario     text not null,
  expected     jsonb not null,
  primary key (resident_id, scenario)
);

-- ---------------------------------------------------------------------------
-- 006_row_level_security.sql
-- ---------------------------------------------------------------------------
-- Row-level security. The backend uses the service-role key, which bypasses RLS.
-- The browser never talks to Supabase directly (it calls the FastAPI backend), so
-- the anon key gets no access; signed-in staff may read.

do $$
declare t text;
begin
  foreach t in array array['profiles', 'residents', 'care_notes', 'observations', 'alerts',
                           'alert_evidence', 'historical_cases', 'case_match_runs',
                           'case_matches', 'eval_scenarios']
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists "signed-in staff can read" on public.%I', t);
    execute format('create policy "signed-in staff can read" on public.%I for select to authenticated using (true)', t);
  end loop;
end $$;

-- ---------------------------------------------------------------------------
-- 007_alert_review_statuses.sql
-- ---------------------------------------------------------------------------
-- For a project created before these files existed: make alerts.status accept the
-- nurse review values the app uses (open, reviewed, needs_assessment, dismissed).
-- Safe to run on any database; existing rows aren't re-checked (NOT VALID).

do $$
declare c text;
begin
  for c in
    select con.conname from pg_constraint con
    join pg_class rel on rel.oid = con.conrelid
    join pg_namespace ns on ns.oid = rel.relnamespace
    where ns.nspname = 'public' and rel.relname = 'alerts' and con.contype = 'c'
      and pg_get_constraintdef(con.oid) ilike '%status%'
  loop
    execute format('alter table public.alerts drop constraint %I', c);
  end loop;
end $$;

alter table public.alerts
  add constraint alerts_status_check
  check (status in ('open', 'reviewed', 'needs_assessment', 'dismissed')) not valid;
alter table public.alerts alter column status set default 'open';

-- ---------------------------------------------------------------------------
-- 008_profile_policies.sql
-- ---------------------------------------------------------------------------
-- Per-user rules for staff profiles (replaces backend/policies.sql and backend/app/policies.sql,
-- which referenced user_id columns and a case_match_members table that don't exist).
--
-- Access model:
--   * clinical tables (residents, notes, alerts, cases, ...) have no per-row owner: any
--     signed-in staff member may read them (006), and only the backend writes, using the
--     service-role key, which bypasses RLS;
--   * a profile belongs to one auth user (profiles.id = auth.uid()): staff can create and
--     edit their own profile, and read everyone's (to see who wrote a note).
-- Views (latest_case_matches, latest_outcome_spread) can't have policies; they use
-- security_invoker (004), so the policies of the tables underneath apply.

alter table public.profiles enable row level security;

drop policy if exists "staff can create their own profile" on public.profiles;
create policy "staff can create their own profile" on public.profiles
  for insert to authenticated
  with check (auth.uid() = id);

drop policy if exists "staff can update their own profile" on public.profiles;
create policy "staff can update their own profile" on public.profiles
  for update to authenticated
  using (auth.uid() = id)
  with check (auth.uid() = id);

commit;

-- ---------------------------------------------------------------------------
-- Check (read-only): expect 1 row for the status rule, RLS on for every table,
-- and three profile policies (read, create own, update own).
-- ---------------------------------------------------------------------------
select conname, pg_get_constraintdef(oid) as rule
from pg_constraint where conrelid = 'public.alerts'::regclass and conname = 'alerts_status_check';

select c.relname as table_name, c.relrowsecurity as rls_on
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r' order by 1;

select tablename, policyname, cmd from pg_policies
where schemaname = 'public' and tablename = 'profiles' order by policyname;
