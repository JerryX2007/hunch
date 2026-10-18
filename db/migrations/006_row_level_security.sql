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
