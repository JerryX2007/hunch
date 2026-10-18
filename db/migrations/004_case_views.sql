-- Read views for the similar-cases page: the newest run per alert, joined to the case library.
-- security_invoker: the views respect the caller's row-level security (Postgres 15+).

create or replace view public.latest_case_matches
with (security_invoker = true) as
select
  r.alert_id,
  m.rank,
  m.historical_case_id,
  c.case_summary,
  c.documented_outcome,
  c.outcome_category,
  c.disposition,
  c.limitations,
  c.duration_days,
  c.timeline,
  m.total_score,
  m.structured_score,
  m.temporal_score,
  m.semantic_score,
  m.shared_signals,
  m.case_only_signals,
  m.resident_only_signals,
  m.differences,
  r.scorer_version,
  r.created_at as matched_at
from (
  select distinct on (alert_id) *
  from public.case_match_runs
  order by alert_id, created_at desc
) r
join public.case_matches m on m.run_id = r.id
join public.historical_cases c on c.id = m.historical_case_id;

create or replace view public.latest_outcome_spread
with (security_invoker = true) as
select alert_id, outcome_category, count(*) as n
from public.latest_case_matches
group by alert_id, outcome_category;
