# Hunch

PSWs and nurses log care notes about long-term care residents; Hunch compares each resident with
their own usual pattern, explains what changed (quoting the notes), and shows what happened in
similar past cases. All data in this repo is fictional.

## Run everything

```bash
python run.py
```

Then open http://localhost:5173/nurse. One command starts the API, runs the analysis for every
resident, and starts the web app. Ctrl+C stops it all.

| Command | What it does |
|---|---|
| `python run.py` | Supabase if `backend/.env` is filled in, otherwise built-in demo data |
| `python run.py --demo` | Always use in-memory demo data (no database or network; resets on restart) |
| `python run.py --seed` | Load `test_data/` into Supabase first |
| `python run.py --build` | Build the web app and serve everything from http://localhost:8000 |
| `python run.py --api-only` | Just the API (docs at http://localhost:8000/docs) |

Needs Python 3.10+ and Node.js 20+. The first run creates `backend/.venv`, installs the Python
packages (again whenever `requirements.txt` gains one) and the web app's npm packages.
Optional: `cp backend/.env.example backend/.env` and fill in Supabase URL + keys and `GEMINI_API_KEY`.

## How it fits together

```
care notes ─▶ extract.py  rule-based signals, each tied to the exact phrase (negation-aware)
           ─▶ check.py    resident vs their own baseline → urgent / alert / watch / quiet
           ─▶ narrative.py + explanation.py  plain-language summary; Gemini if a key is set,
                          every claim validated against evidence IDs, else a template
           ─▶ match.py    similar fictional past cases: what's shared, what differs, outcome
           ─▶ service.py  saves alerts, evidence and matches (store.py: Supabase or in-memory)
           ─▶ API (FastAPI) ─▶ web app: nurse dashboard, resident page, PSW note page
```

## Layout

```
run.py              one command to run everything
backend/            FastAPI (Python)
  app/
    main.py         app setup, routers under /api, serves frontend/dist when built
    store.py        data access: SupabaseStore or MemoryStore (demo)
    history/        the pipeline: extract, check, narrative, match, service
    explanation.py  LLM prompt + validator + template fallback for summaries
    models/         Gemini note parser (optional; python -m app.models.test_parser)
    routers/        health, residents (+ notes), history (check, run, alerts, similar cases)
    database.py     Supabase client + table helpers
    repositories/   per-table CRUD wrappers (residents, care_notes, observations, alerts, ...)
    auth.py         Supabase email/password sign-in, token check, logout
    utils/          error formatting + DB operation logging
  scripts/          seed_db, check_db, run_history_check (--eval), dump_schema
  tests/            pytest (offline, fake Supabase in conftest.py): python -m pytest -q
db/migrations/      SQL to create the Supabase schema (see db/README.md)
frontend/           Vite + React + TypeScript + Tailwind
  src/pages/        Nurse (dashboard), ResidentProfile, Psw (log a note), Join
test_data/          fictional residents, notes, case library, eval scenarios
ML/                 separate prototype: PSW icon "hunch" scoring engine (not wired in)
```

## API

| Method | Path | |
|---|---|---|
| GET | `/api/health` | mode (demo/supabase), database status, whether Gemini is on |
| GET | `/api/residents?q=` | residents with today's tier and latest alert, most concerning first |
| POST | `/api/residents` | add a resident (`id`, `display_name`, optional baseline dates) |
| GET | `/api/residents/{id}` | profile, live check with evidence, alert + summary, similar cases, last 10 notes |
| GET/POST | `/api/residents/{id}/notes` | last notes / log a note (re-runs that resident) |
| POST | `/api/history/run` | run the check for everyone and save alerts + similar cases |
| GET | `/api/history/check` | compute only, writes nothing |
| GET | `/api/alerts`, `/api/alerts/{id}` | alerts (urgent first) |
| PATCH | `/api/alerts/{id}/status` | nurse review: reviewed / needs_assessment / dismissed / open |
| GET | `/api/alerts/{id}/similar-cases` | ranked past cases with documented outcomes |
| POST | `/api/auth/signin` | email (`username` form field) + password → access/refresh token (Supabase only) |
| GET | `/api/auth/me` | current user from `Authorization: Bearer <token>` |
| POST | `/api/auth/logout` | revoke the user's sessions (needs the service key) |
| GET/PUT | `/api/profile/me` | your staff profile (name, role); needs a Bearer token |

## Adding things

- New endpoint: add `backend/app/routers/<name>.py`, then `app.include_router(<name>.router, prefix="/api")` in `main.py`.
- New page: add `frontend/src/pages/<Name>.tsx` and a `<Route>` in `App.tsx`.
- New API type: update `backend/app/schemas.py` and `frontend/src/api/types.ts`.
- Schema change: add a numbered file in `db/migrations/`, then `python -m scripts.dump_schema`.
