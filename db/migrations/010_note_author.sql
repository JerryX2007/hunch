-- Who wrote each note: the signed-in nurse's name and account ID.
-- Notes from people who aren't signed in (PSWs on the note screen) leave these empty
-- and keep author_role = 'PSW'. Adds two empty columns; changes no existing data.
-- Safe to run more than once.

alter table public.care_notes add column if not exists author_name text;
alter table public.care_notes add column if not exists author_id uuid;

-- Check: expect two rows.
select column_name, data_type from information_schema.columns
where table_schema = 'public' and table_name = 'care_notes' and column_name in ('author_name', 'author_id')
order by 1;
