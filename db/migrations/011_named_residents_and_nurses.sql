-- Name the demo unit: residents get names and unit IDs (DEMO-014 -> 2W-014, "Evelyn Brooks"),
-- and every note without a writer gets one of the unit's four nurses.
-- Same people as test_data/people.json. Run after 010, and before re-running scripts/seed_db.
--
-- What changes:
--   * each DEMO-0xx resident moves to its 2W-0xx ID with a name; every table that points at
--     residents (care_notes, observations, alerts, eval_scenarios, and any other foreign key)
--     follows, then the old resident row is removed
--   * care_notes.author_name is filled on notes that don't have one (random nurse, but the
--     same pick every run); author_id is linked when that nurse's account exists
-- Nothing else is deleted. All-or-nothing, and safe to run more than once.

begin;

alter table public.care_notes add column if not exists author_name text;
alter table public.care_notes add column if not exists author_id uuid;

create temporary table people_map (old_id text primary key, new_id text not null, name text not null) on commit drop;
insert into people_map values
  ('DEMO-011', '2W-011', 'Margaret Chen'),
  ('DEMO-012', '2W-012', 'Harold Okafor'),
  ('DEMO-013', '2W-013', 'Rosa Marchetti'),
  ('DEMO-014', '2W-014', 'Evelyn Brooks'),
  ('DEMO-015', '2W-015', 'Arjun Mehta'),
  ('DEMO-016', '2W-016', 'Dorothy Kowalski'),
  ('DEMO-017', '2W-017', 'Walter Nguyen'),
  ('DEMO-018', '2W-018', 'Lillian Haddad'),
  ('DEMO-019', '2W-019', 'George Fitzgerald'),
  ('DEMO-020', '2W-020', 'Agnes Tremblay'),
  ('DEMO-021', '2W-021', 'Frank Adeyemi'),
  ('DEMO-022', '2W-022', 'Irene Santos');

-- 1. new resident rows, copied from the old ones
insert into public.residents (id, display_name, baseline_start, baseline_end, created_at)
select m.new_id, m.name, r.baseline_start, r.baseline_end, r.created_at
from people_map m join public.residents r on r.id = m.old_id
on conflict (id) do nothing;

-- 2. everything that points at a resident follows it
do $$
declare t record;
begin
  -- an eval label that already exists under the new ID wins (e.g. seed_db ran first)
  if to_regclass('public.eval_scenarios') is not null then
    delete from public.eval_scenarios e using people_map m
    where e.resident_id = m.old_id
      and exists (select 1 from public.eval_scenarios x where x.resident_id = m.new_id and x.scenario = e.scenario);
  end if;
  for t in
    select distinct c.conrelid::regclass::text as tbl, a.attname as col
    from pg_constraint c
    join pg_attribute a on a.attrelid = c.conrelid and a.attnum = c.conkey[1]
    where c.contype = 'f' and c.confrelid = 'public.residents'::regclass and array_length(c.conkey, 1) = 1
    union
    select k.tbl, 'resident_id' from (values ('public.care_notes'), ('public.observations'),
                                             ('public.alerts'), ('public.eval_scenarios')) k(tbl)
    where to_regclass(k.tbl) is not null
  loop
    execute format('update %s t set %I = m.new_id from people_map m where t.%I = m.old_id', t.tbl, t.col, t.col);
  end loop;
end $$;

-- 3. remove the old resident rows (nothing points at them any more)
delete from public.residents r using people_map m where r.id = m.old_id;

-- 4. names on residents that still show their ID (a re-run, or seeded with new IDs)
update public.residents r set display_name = m.name
from people_map m
where r.id = m.new_id and r.display_name in (m.old_id, m.new_id);

-- 5. a nurse for every note without a writer: random, but the same pick every run
update public.care_notes
set author_name = (array['Priya Raman', 'Daniel Osei', 'Grace Liu', 'Mateo Alvarez'])[((hashtext(id::text) % 4) + 4) % 4 + 1]
where author_name is null;

-- 6. link notes to the nurses' accounts, if they exist yet (scripts/create_demo_nurses.py also does this)
update public.care_notes n set author_id = u.id
from auth.users u
join (values
    ('Priya Raman', 'priya.raman@hunch.test'),
    ('Daniel Osei', 'daniel.osei@hunch.test'),
    ('Grace Liu', 'grace.liu@hunch.test'),
    ('Mateo Alvarez', 'mateo.alvarez@hunch.test')
  ) v(name, email) on lower(u.email) = v.email
where n.author_name = v.name and n.author_id is null;

commit;

-- Check: residents now have unit IDs and names; notes per nurse.
select id, display_name from public.residents order by id;
select coalesce(author_name, '(none)') as written_by, count(*) as notes,
       count(author_id) as linked_to_account
from public.care_notes group by 1 order by 2 desc;
