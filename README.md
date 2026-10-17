# Hunch

PSWs in long-term care log quick "hunches" about residents; a nurse dashboard turns them into early, explained warnings.

## Layout

```
backend/            FastAPI (Python)
  app/
    main.py         app setup, CORS, routers mounted under /api
    config.py       settings from env / backend/.env
    database.py     Supabase client + table helpers (needs backend/.env)
    schemas.py      API models (keep in sync with frontend/src/api/types.ts)
    routers/        one file per resource (health, residents, ...)
  scripts/check_db.py  read-only check that every table is reachable
  requirements.txt
  .env.example
frontend/           Vite + React + TypeScript + Tailwind
  src/
    App.tsx         routes
    api/            fetch client + shared types
    components/     shared UI (Layout, ...)
    pages/          Home, Join, Psw, Nurse, ResidentProfile
```

## Run locally

Backend (http://localhost:8000, docs at /docs):

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in SUPABASE_URL and the two keys
python -m scripts.check_db  # confirm the database connection
uvicorn app.main:app --reload
```

Frontend (http://localhost:5173):

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api/*` to the backend, so the frontend always calls relative URLs like `/api/residents`.

## Adding things

- New endpoint: add `backend/app/routers/<name>.py`, then `app.include_router(<name>.router, prefix="/api")` in `main.py`.
- New page: add `frontend/src/pages/<Name>.tsx` and a `<Route>` in `App.tsx`.
- New API type: update both `backend/app/schemas.py` and `frontend/src/api/types.ts`.
