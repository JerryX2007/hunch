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
