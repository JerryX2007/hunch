# Database (Supabase / Postgres)

Run the files in `migrations/` in order (Supabase dashboard → SQL Editor, or `psql -f`) on a new project,
then load the demo data from `backend/`:

```bash
python -m scripts.seed_db            # residents, care notes, case library, eval scenarios
python -m scripts.check_db           # read-only: is every table reachable?
```

Or just `python run.py --seed` from the repo root.

| File | Creates |
|---|---|
| `001_core.sql` | `profiles`, `residents`, `care_notes`, `observations` |
| `002_alerts.sql` | `alerts`, `alert_evidence` |
| `003_case_library.sql` | `historical_cases`, `case_match_runs`, `case_matches` (pgvector) |
| `004_case_views.sql` | `latest_case_matches`, `latest_outcome_spread` views |
| `005_eval_scenarios.sql` | `eval_scenarios` (test labels) |
| `006_row_level_security.sql` | RLS on every table: signed-in users read, backend writes with the service key |
| `007_alert_review_statuses.sql` | Lets `alerts.status` take the review values (open / reviewed / needs_assessment / dismissed). **Run this one on the existing project too.** |
| `008_profile_policies.sql` | Staff can create and edit their own profile (`profiles.id = auth.uid()`). Run on the existing project too. |

**These files were rebuilt from `backend/schema_snapshot.json`** (column names, types and NOT NULLs match
the live project as of the snapshot). Defaults, CHECK constraints, policies and the two view
definitions were inferred from the code, because the original SQL was only ever typed into the
Supabase SQL Editor. To compare with the live project:

```bash
supabase db dump --schema public > /tmp/live.sql   # or: pg_dump --schema-only --schema=public "$DATABASE_URL"
```

When you change the schema, add a new numbered file here (don't edit old ones), then run
`python -m scripts.dump_schema` to refresh the snapshot.
