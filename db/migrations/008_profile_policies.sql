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
