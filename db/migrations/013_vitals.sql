-- Vitals (temperature, SpO2, pulse, breathing rate, blood pressure) and each resident's
-- medical history. Adds one table and one column; changes no existing data.
-- Safe to run more than once. Then load the seed vitals: python -m scripts.reseed_notes

create table if not exists public.vitals (
  id            uuid primary key default gen_random_uuid(),
  resident_id   text not null references public.residents (id) on delete cascade,
  recorded_at   timestamptz not null,
  temp_c        numeric(3,1) check (temp_c between 30 and 43),
  spo2          smallint check (spo2 between 50 and 100),
  pulse         smallint check (pulse between 25 and 220),
  resp_rate     smallint check (resp_rate between 4 and 60),
  bp_systolic   smallint check (bp_systolic between 50 and 260),
  bp_diastolic  smallint check (bp_diastolic between 20 and 160),
  author_role   text,
  author_name   text,          -- who took them
  author_id     uuid,
  source        text not null default 'entered',
  created_at    timestamptz not null default now()
);
create index if not exists vitals_resident_time on public.vitals (resident_id, recorded_at desc);

-- Same rule as every other table (006): signed-in staff read; the backend writes with the service key.
alter table public.vitals enable row level security;
drop policy if exists "signed-in staff can read" on public.vitals;
create policy "signed-in staff can read" on public.vitals for select to authenticated using (true);

-- Medical history, e.g. ["COPD (severe)", "Type 2 diabetes"]. Context for nurses only.
alter table public.residents add column if not exists conditions jsonb not null default '[]'::jsonb;

-- Check: expect 2 rows.
select table_name, column_name from information_schema.columns
where table_schema = 'public'
  and ((table_name = 'vitals' and column_name = 'temp_c') or (table_name = 'residents' and column_name = 'conditions'));
