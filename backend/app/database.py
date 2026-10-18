"""Backend database access – connection setup and low‑level helpers.

Only generic utilities belong here; all table‑specific CRUD logic lives in
the repository modules under ``backend/app/repositories``.
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend root detection – works whether the process is started from the
# repo root or from a sub‑directory (e.g. when running uvicorn).
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent  # .../backend
REPO_DIR = BACKEND_DIR.parent

# ---------------------------------------------------------------------------
# Load a .env file placed next to the backend folder (backend/.env)
# ---------------------------------------------------------------------------
load_dotenv(BACKEND_DIR / ".env")


# ---------------------------------------------------------------------------
# Environment resolution
# ---------------------------------------------------------------------------
def _env(*names: str) -> Optional[str]:
    """Return the first non‑empty value among ``names``."""
    for name in names:
        val = os.getenv(name)
        if val:
            return val
    return None


SUPABASE_URL = _env("SUPABASE_URL", "VITE_SUPABASE_URL")
_ANON_KEY = _env("SUPABASE_ANON_KEY", "VITE_SUPABASE_ANON_KEY")
_SERVICE_KEY = _env("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not (_ANON_KEY or _SERVICE_KEY):
    raise RuntimeError(
        "Supabase is not configured. Copy backend/.env.example to backend/.env "
        "and fill in SUPABASE_URL and at least one key."
    )

# Admin client (used for RLS‑protected tables)
supabase_admin: Optional[Client] = (
    create_client(SUPABASE_URL, _SERVICE_KEY) if _SERVICE_KEY else None
)

# General client – service key if we have it, otherwise the anon key.
supabase: Client = supabase_admin or create_client(SUPABASE_URL, _ANON_KEY)

if supabase_admin is None:
    log.warning(
        "SUPABASE_SERVICE_ROLE_KEY not set; using the anon key. Tables with "
        "row‑level security may return no rows and reject writes."
    )


# ---------------------------------------------------------------------------
# Admin helper – required for tables protected by Row‑Level Security
# ---------------------------------------------------------------------------
def _require_admin() -> Client:
    if supabase_admin is None:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is not set. The case tables are protected "
            "by row‑level security and cannot be read or written with the anon key."
        )
    return supabase_admin


# ---------------------------------------------------------------------------
# Generic low‑level helpers (shared by all repositories)
# ---------------------------------------------------------------------------
def _list(table: str, **filters: Any) -> List[Dict[str, Any]]:
    q = supabase.table(table).select("*")
    for col, val in filters.items():
        q = q.eq(col, val)
    return q.execute().data


def _get(table: str, row_id: str) -> Optional[Dict[str, Any]]:
    resp = supabase.table(table).select("*").eq("id", row_id).maybe_single().execute()
    return resp.data if resp is not None else None


def _upsert(table: str, row: Dict[str, Any], require_id: bool = False) -> Dict[str, Any]:
    if require_id and not row.get("id"):
        raise ValueError(f"{table} row must have an 'id' field.")
    data = supabase.table(table).upsert(row).execute().data
    if not data:
        raise RuntimeError(
            f"Upsert into {table} returned no row (row‑level security may be hiding it)."
        )
    return data[0]


def _delete(table: str, row_id: str) -> None:
    supabase.table(table).delete().eq("id", row_id).execute()


# ---------------------------------------------------------------------------
# Optional mock‑testing hook – runs when the environment variable
# ``RUN_MOCKS=true`` is set.  It only verifies that the module can be
# imported and that a Supabase client object exists; it does not hit the
# real backend.
# ---------------------------------------------------------------------------
if os.getenv("RUN_MOCKS", "false").lower() == "true":
    """Placeholder for mock tests when developing without a live Supabase."""
    import asyncio

    async def _mock_test():
        """Very small sanity‑check that the module can be imported and the client exists."""
        # In a real test suite you would patch `supabase.table(...)` etc.
        assert supabase is not None, "Supabase client not initialised"
        print("✅ Mock test passed – client is present")

    asyncio.run(_mock_test())


# ---------------------------------------------------------------------------
# Simple health check – used by the /health endpoint
# ---------------------------------------------------------------------------
def ping() -> bool:
    """Cheap connectivity test."""
    supabase.table("residents").select("id").limit(1).execute()
    return True