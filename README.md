# Hunch Backend

## Overview
This backend provides a FastAPI‑based REST service for the Hunch hackathon project. It uses **Supabase** (PostgREST + Realtime) as the data store and authenticates via Supabase Auth. The code is organised into a clean layered architecture:

```
backend/
├─ .env                # runtime config (VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, optionally SUPABASE_SERVICE_ROLE_KEY)
├─ requirements.txt   # python dependencies
└─ backend/
   ├─ __init__.py
   ├─ app/
   │   ├─ __init__.py
   │   ├─ main.py              # FastAPI entry point, mounts routers under /api
   │   ├─ config.py            # pydantic Settings (reads .env)
   │   ├─ database.py          # Supabase client creation + generic helpers (_list, _get, _upsert, _delete, ping)
   │   ├─ dependencies.py      # get_supabase() FastAPI dependency
   │   ├─ models/              # SQLModel entities (optional ORM mapping)
   │   ├─ schemas/             # Pydantic request/response models
   │   ├─ repositories/        # CRUD wrappers around the Supabase client
   │   │   ├─ __init__.py
   │   │   ├─ profiles_repository.py
   │   │   ├─ care_notes_repository.py
   │   │   ├─ observations_repository.py
   │   │   ├─ alerts_repository.py
   │   │   ├─ alert_evidence_repository.py
   │   │   └─ historical_cases_repository.py
   │   ├─ services/            # Optional business‑logic layer (e.g. alert_service.py)
   │   ├─ routers/             # FastAPI route modules
   │   │   ├─ __init__.py
   │   │   ├─ health.py
   │   │   ├─ residents.py
   │   │   └─ ... (other entity routers)
   │   └─ utils/
   │       └─ error_format.py   # format_supabase_error(), log_db_operation()
   └─ tests/                   # pytest suite with mock_supabase fixture
```

### How it works
1. **`backend/database.py`** creates a single `supabase: Client` object that is shared by all repositories.
2. **Each repository** (`*_repository.py`) implements CRUD (list, get‑by‑id, upsert, delete) for one table and logs/format errors via `backend/app/utils/error_format.py`.
3. **FastAPI routers** (`backend/app/routers/`) call the repositories through `Depends(get_supabase)`.
4. **Services** (optional) can coordinate multiple repositories for business rules.
5. **Tests** use `pytest` with a `mock_supabase` fixture that patches the Supabase client, so they run without a live project.

### Adding a new table‑repository
1. Create `backend/app/repositories/<table>_repository.py` following the pattern of the existing ones.
2. Add the new file name to `backend/app/repositories/__init__.py` `__all__`.
3. Import and use the repository in the corresponding FastAPI router.

### Running the API (development)
```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Copy the example env file and fill in your Supabase credentials
cp backend/.env.example backend/.env
# Edit .env if you have a service‑role key, otherwise keep the defaults.

# 2. Start the server
uvicorn backend.app.main:app --reload   # or use the provided run script

# 3. Visit the auto‑generated OpenAPI docs
#    http://127.0.0.1:8000/docs
```

### Testing
```bash
# Unit‑level (mocked)
pytest backend/tests/ -v

# Quick sanity check (server must be running)
curl http://127.0.0.1:8000/api/residents   # returns [] until data is seeded
```

### Adding data
Data is stored in the Supabase project linked in `.env`. Use the Supabase Dashboard or the SQL editor to insert rows; the repositories already map to the tables defined in your schema.

---
**Generated with Claude Code**