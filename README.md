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
- **Demo data:** the four fictional nurses in `test_data/people.json` (e.g.
  `priya.raman@hunch.test`) sign in with password `hunch-demo` (`HUNCH_DEMO_PASSWORD`).
  The sign-in screen lists them.
- **The same four nurses on live data:** `python -m scripts.create_demo_nurses` creates their
  accounts and links them to the notes they wrote (after `db/migrations/011`).

Sessions live in HttpOnly cookies; expired Supabase sessions renew automatically.
Five wrong passwords in five minutes from one address pause sign-in for that address.

## Gemini reads the notes

With `GEMINI_API_KEY` in `backend/.env`, Gemini reads every care note
(`backend/app/models/note_reader.py`): its language, an English translation if it isn't
English, the changes it reports (eating, drinking, energy, mobility, confusion, pain, sleep,
social, toileting, breathing) and serious events (a fall, chest pain, a hospital transfer...),
each with the note's own words. Python then has the last word (`backend/app/history/ai_read.py`):

- Every quote must really be in the note (or its translation), and every category one Hunch
  knows; anything else is dropped.
- The rules still read every note (the translation, for non-English notes). Their findings
  always count, and they decide what's ruled out ("denies pain").
- What only Gemini found is tagged **Read by AI** on the resident page; translations are shown
  next to the original.
- Each note is read once: the reading is saved with the note (`care_notes.ai_reading`) and in
  `backend/.cache/`. A new note is read when it's saved; `run.py` reads older notes in the
  background, or run `python -m scripts.read_notes` from `backend/`. Reading the whole history
  matters: a resident's usual days and recent days must be read the same way to compare fairly.
- Without a key (or if Gemini fails), the rules read the notes as before. A recent note that
  nothing could read, and that doesn't look like English, puts the resident on **Keep an eye
  on** with "A recent note needs reading", never quiet.

`/api/health` shows how many notes Gemini has read. Model: `gemini-3.5-flash-lite`, falling
back to `gemini-3.1-flash-lite` (set `GEMINI_NOTE_MODEL` to change it).

**On live Supabase:** run `db/migrations/012_note_ai_reading.sql` once, then
`python -m scripts.read_notes` once to read the existing notes.

## Voice notes

Every note box (PSW note, resident note, admission note) has a **Speak** button. Tap it,
talk, and the words appear in the box as you go. It uses the browser's built-in speech
recognition, asks for English, and needs `https` or `localhost` plus an internet connection.

- **Chrome / Edge:** keeps listening until you tap again (audio goes to Google's speech service).
- **Safari and every iPhone browser:** listens for one phrase per tap and stops by itself
  after a pause (Safari's continuous mode keeps switching the microphone off and on).
  Needs Dictation turned on in the device's keyboard settings.
- **Brave, Firefox, browsers inside desktop apps:** no speech service, so the button is
  replaced by a note to use Chrome, Edge or Safari, or the keyboard's own dictation key.

## Deploy on Vercel

One Vercel project runs everything: `server.py` loads the FastAPI app, which serves the
API under `/api` and the built web app (Vercel runs `npm run build` in `frontend/`, set in
`vercel.json`). Python packages come from the root `pyproject.toml`.

1. On vercel.com: **Add New › Project**, import this GitHub repo. Leave the root
   directory as `./`; the framework should show **FastAPI**.
2. Add these **Environment Variables** (same values as `backend/.env`):
   `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and
   `HUNCH_MODE=supabase`, and `GEMINI_API_KEY` so Gemini reads new notes and writes the
   alert summaries (without it, notes are read by the rules only). Read the existing notes
   once from your computer (see "Gemini reads the notes").
3. **Deploy**, then open `https://<your-project>.vercel.app/api/health`: it should say
   `"mode": "supabase"` and `"database": "ok"`.

Use Supabase mode on Vercel: demo mode keeps notes in memory, and Vercel's functions don't
keep memory between requests. Every push to `main` redeploys.

## How it fits together

```
care notes ─▶ note_reader.py  Gemini: language, English translation, changes and events, with quotes
           ─▶ ai_read.py  Python checks every quote against the note; merges with the rules
           ─▶ extract.py  rule-based signals, each tied to the exact phrase (negation-aware)
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
    history/        the pipeline: ai_read (checks Gemini's reading), extract, check, narrative, match, service
    explanation.py  LLM prompt + validator + template fallback for summaries
    models/         Gemini: note_reader (reads every note), parser (older single-note parser)
    routers/        health, residents (+ notes), history (check, run, alerts, similar cases)
    database.py     Supabase client + table helpers
    repositories/   per-table CRUD wrappers (residents, care_notes, observations, alerts, ...)
    auth.py         Supabase email/password sign-in, token check, logout
    utils/          error formatting + DB operation logging
  scripts/          seed_db, check_db, run_history_check (--eval), read_notes, dump_schema
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
| POST | `/api/residents` | add a resident: `display_name`, optional `id` (default: next free 2W-NNN) and `first_note` |
| GET | `/api/residents/next-id` | the ID a new resident gets by default |
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
