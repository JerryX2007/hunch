-- Hunch core tables: who the residents are and what staff wrote about them.
-- Rebuilt from backend/schema_snapshot.json (column names, types, NOT NULLs).
-- Defaults, checks and policies are inferred from how the code writes rows;
-- compare with the live project before relying on them (see db/README.md).

create extension if not exists pgcrypto;  -- gen_random_uuid()

-- Staff profiles, one per Supabase auth user.
create table if not exists public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  full_name   text not null,
  role        text not null,               -- e.g. PSW, RPN, RN, NP
  created_at  timestamptz not null default now()
);

-- Fictional residents. id is a readable demo ID such as DEMO-014.
create table if not exists public.residents (
  id              text primary key,
  display_name    text not null,
  baseline_start  date,
  baseline_end    date,
  created_at      timestamptz not null default now()
);

-- Original care notes. Never overwritten by the analysis.
create table if not exists public.care_notes (
  id                 uuid primary key default gen_random_uuid(),
  resident_id        text not null references public.residents (id) on delete cascade,
  note_text          text not null,
  recorded_at        timestamptz not null,
  author_role        text,
  extraction_status  text not null default 'pending',
  created_at         timestamptz not null default now()
);
create index if not exists care_notes_resident_time on public.care_notes (resident_id, recorded_at desc);

-- Structured observations extracted from notes (one per note + signal).
create table if not exists public.observations (
  id                uuid primary key default gen_random_uuid(),
  note_id           uuid not null references public.care_notes (id) on delete cascade,
  resident_id       text not null references public.residents (id) on delete cascade,
  category          text,          -- nutrition, fluids, energy, mobility, toileting, pain, ...
  subcategory       text,          -- toileting only: urine / bowel
  change            text,          -- toileting only: increased / decreased
  observation_text  text,
  direction         text,          -- worsening / improving / neutral
  numeric_value     numeric,
  unit              text,
  assertion         text not null default 'present',  -- present / negated / uncertain / historical
  confidence        numeric,
  evidence_span     text,          -- exact words from the note
  recorded_at       timestamptz,
  created_at        timestamptz not null default now()
);
create index if not exists observations_resident on public.observations (resident_id, recorded_at);
