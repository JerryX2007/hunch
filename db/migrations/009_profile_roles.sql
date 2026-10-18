-- Every account is a nurse: profiles.role is "nurse".
-- The live project had an older profiles_role_check with other values, so
-- scripts/create_nurse.py couldn't save the profile. This replaces that rule.
-- Safe to run more than once. The only data change: any profile with an old
-- RN / RPN / NP role (written by an earlier version of the app) becomes "nurse".

do $$
declare c record;
begin
  for c in
    select con.conname, pg_get_constraintdef(con.oid) as def
    from pg_constraint con
    join pg_class rel on rel.oid = con.conrelid
    join pg_namespace ns on ns.oid = rel.relnamespace
    where ns.nspname = 'public' and rel.relname = 'profiles' and con.contype = 'c'
      and pg_get_constraintdef(con.oid) ilike '%role%'
  loop
    raise notice 'Replacing % : %', c.conname, c.def;  -- shows the old rule in the Messages tab
    execute format('alter table public.profiles drop constraint %I', c.conname);
  end loop;
end $$;

update public.profiles set role = 'nurse' where role in ('RN', 'RPN', 'NP');

alter table public.profiles alter column role set default 'nurse';
alter table public.profiles
  add constraint profiles_role_check check (role = 'nurse') not valid;

-- Check: expect one row, CHECK (role = 'nurse').
select conname, pg_get_constraintdef(oid) as rule
from pg_constraint where conrelid = 'public.profiles'::regclass and conname = 'profiles_role_check';
