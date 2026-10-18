-- Alerts (one per resident, updated in place by the history check) and their evidence.

create table if not exists public.alerts (
  id               uuid primary key default gen_random_uuid(),
  resident_id      text not null references public.residents (id) on delete cascade,
  title            text not null,
  summary          text,
  explanation      jsonb,          -- full history check + evidence + plain-language summary
  triggered_rules  jsonb,
  status           text not null default 'open'
                   check (status in ('open', 'reviewed', 'needs_assessment', 'dismissed')),
  urgent           boolean not null default false,
  created_at       timestamptz not null default now()
);
create index if not exists alerts_resident_time on public.alerts (resident_id, created_at desc);

create table if not exists public.alert_evidence (
  alert_id        uuid not null references public.alerts (id) on delete cascade,
  observation_id  uuid not null references public.observations (id) on delete cascade,
  primary key (alert_id, observation_id)
);
