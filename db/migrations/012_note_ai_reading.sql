-- Gemini's reading of each care note: language, English translation, observations and
-- serious events, each with the note's own words, after the backend has checked them
-- (backend/app/history/ai_read.py). Saved once per note so it's never read twice.
-- extraction_status becomes 'ai_read' for notes that have one.
-- Adds one empty column; changes no existing data. Safe to run more than once.

alter table public.care_notes add column if not exists ai_reading jsonb;

-- Check: expect one row.
select column_name, data_type from information_schema.columns
where table_schema = 'public' and table_name = 'care_notes' and column_name = 'ai_reading';
