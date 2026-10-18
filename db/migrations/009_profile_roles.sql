-- Let profiles.role take the roles the app uses: RN, RPN, NP, PSW, other.
-- The live project had an older profiles_role_check with different values, so
-- scripts/create_nurse.py couldn't save "RN". Existing profiles aren't re-checked (NOT VALID).
-- Safe to run more than once. Changes no data.

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

alter table public.profiles
  add constraint profiles_role_check
  check (role in ('RN', 'RPN', 'NP', 'PSW', 'other')) not valid;

-- Check: expect one row listing the five roles.
select conname, pg_get_constraintdef(oid) as rule
from pg_constraint where conrelid = 'public.profiles'::regclass and conname = 'profiles_role_check';
