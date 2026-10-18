# Plan: Tasks #1‑#3 – Repository import check, package init, and router wiring

## Goal
Validate that the newly‑moved repository modules import correctly, ensure the `repositories` folder is a proper Python package, and wire at least one FastAPI router (`residents`) to use its repository instead of the old inline functions.

## Outline of steps

### Task #1 – Import sanity check
1. Run `python -c "import backend.app.repositories.profiles_repository; print('profiles ok')"`.
2. Run the same for `care_notes_repository`, `observations_repository`, `alerts_repository`, `alert_evidence_repository`, `historical_cases_repository`.
3. Verify no `ImportError` or `ModuleNotFoundError` appears.
4. If an error occurs, inspect the import path (`from backend.app.database import supabase`) and fix the `backend/app/__init__.py` / `backend/__init__.py` as needed.

### Task #2 – Make `repositories` a proper package
1. Ensure `backend/app/repositories/__init__.py` exists (already created, empty is fine).
2. Optionally add a minimal `__all__` list for convenience:
   ```python
   __all__ = [
       "profiles_repository",
       "care_notes_repository",
       "observations_repository",
       "alerts_repository",
       "alert_evidence_repository",
       "historical_cases_repository",
   ]
   ```
3. Run `python -c "from backend.app.repositories import *; print('repositories package imported')"`.

### Task #3 – Wire the FastAPI `residents` router to its repository
1. Edit `backend/app/routers/residents.py`:
   - Add import: `from backend.app.repositories.residents_repository import list_all, get_by_id, upsert as upsert_resident, delete as delete_resident`.
   - Add FastAPI dependency import: `from backend.app.dependencies import get_supabase`.
   - Modify `list_residents` endpoint to call `list_all()` using `Depends(get_supabase)`.
   - Keep the `get_resident` endpoint using `get_by_id`.
   - Keep the `create_resident`/`update_resident` stubs or remove them if not needed.
2. Run the FastAPI app: `uvicorn backend.app.main:app --reload`.
3. Open `http://localhost:8000/docs` and confirm that the `/api/residents` endpoint appears and returns data (initially empty until seed data is added).
4. Verify that no other routers (`health`, `profile`) break; they should continue to work unchanged.

## Success criteria
- All six repository modules import without errors.
- `from backend.app.repositories import *` works.
- The `/api/residents` GET endpoint returns a JSON list (empty list is fine) and does not raise 500.
- The existing `/api/health` endpoint still returns `{"status":"ok"}`.

## Post‑plan actions (after approval)
- If any import fails, adjust `backend/app/__init__.py` or the repository import statements.
- Add service‑layer examples or unit tests in `backend/tests/` as a follow‑up.
- Consider adding `__all__` to each repository file for a cleaner public API.
