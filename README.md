# Hunch

PSWs and nurses log care notes about long-term care residents; Hunch compares each resident with
their own usual pattern, explains what changed (quoting the notes), and shows what happened in
similar past cases. All data in this repo is fictional.

## Run everything

```bash
python run.py
```

Then open http://localhost:5173/nurse and sign in. One command starts the API, runs the analysis for every
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

## Nurse sign-in

Each nurse has their own account, and every account is a nurse. The resident screen
needs a signed-in nurse; PSWs log notes at `/psw` without signing in.

- **Live data (Supabase):** create accounts from `backend/`:
  `python -m scripts.create_nurse --email dana@example.com --name "Dana Lee"`
  (asks for the password; run it again to change the name or password).
- **Demo data:** one built-in account, `nurse@demo.hunch` / `hunch-demo`, shown on the
  sign-in screen. Change it with `HUNCH_DEMO_EMAIL` / `HUNCH_DEMO_PASSWORD`.

Sessions live in HttpOnly cookies; expired Supabase sessions renew automatically.
Five wrong passwords in five minutes from one address pause sign-in for that address.

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
  src/pages/        Nurse (list + resident detail), Psw (log a note), Join
  src/components/   ResidentDetail, Badges, Toast, format (labels, dates)
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
| POST | `/api/auth/signin` | `{email, password}` → sets the session cookies (HttpOnly) |
| GET | `/api/auth/me` | who is signed in on this browser (never 401) |
| POST | `/api/auth/logout` | sign out |
| GET/PUT | `/api/profile/me` | your name |

Nurse endpoints (resident details, alerts, reviews, history check) need a signed-in nurse. Without sign-in, `/api/residents` returns only IDs and names, and
`POST /api/residents/{id}/notes` still works, so PSWs log notes without an account.

## Adding things

- New endpoint: add `backend/app/routers/<name>.py`, then `app.include_router(<name>.router, prefix="/api")` in `main.py`.
- New page: add `frontend/src/pages/<Name>.tsx` and a `<Route>` in `App.tsx`.
- New API type: update `backend/app/schemas.py` and `frontend/src/api/types.ts`.
- Schema change: add a numbered file in `db/migrations/`, then `python -m scripts.dump_schema`.
