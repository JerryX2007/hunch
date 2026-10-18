-- Fictional historical case library and the similar-case results for each alert.

create extension if not exists vector;  -- pgvector, for optional embeddings

create table if not exists public.historical_cases (
  id                  text primary key,          -- e.g. CASE-001
  case_summary        text not null,
  observations        jsonb not null,            -- [{category, direction, subcategory?, change?}]
  timeline            jsonb not null,            -- [{day, category, note}]
  duration_days       integer not null,
  documented_outcome  text not null,             -- only what the fictional record states
  limitations         text not null,
  outcome_category    text,
  disposition         text,
  embedding           vector(384),
  embedding_model     text,
  is_fictional        boolean not null default true,
  created_at          timestamptz not null default now()
);

-- One scoring run per alert + evidence fingerprint (re-used when nothing changed).
create table if not exists public.case_match_runs (
  id                   uuid primary key default gen_random_uuid(),
  alert_id             uuid not null references public.alerts (id) on delete cascade,
  alert_fingerprint    text not null,
  query_signals        text[] not null,
  query_duration_days  integer not null,
  query_text           text not null,
  query_embedding      vector,
  scorer_version       text not null,
  weights              jsonb not null,
  candidates_seen      integer not null,
  created_at           timestamptz not null default now(),
  unique (alert_id, alert_fingerprint)
);

create table if not exists public.case_matches (
  run_id                 uuid not null references public.case_match_runs (id) on delete cascade,
  historical_case_id     text not null references public.historical_cases (id) on delete cascade,
  rank                   integer not null,
  structured_score       real not null,
  temporal_score         real not null,
  semantic_score         real,
  total_score            real not null,
  shared_signals         text[] not null,
  case_only_signals      text[] not null,
  resident_only_signals  text[] not null,
  differences            jsonb not null default '[]'::jsonb,
  primary key (run_id, historical_case_id)
);
