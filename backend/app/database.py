"""Backend database access for Supabase.

One place for the Supabase client plus small helpers for each table:

- profiles
- residents
- care_notes
- observations
- alerts
- alert_evidence (junction: alert <-> observation)
- historical_cases, case_match_runs, case_matches (similar-case retrieval)

Notes on the supabase-py client (v2):
- ``.execute()`` returns an ``APIResponse`` with ``.data``. There is no
  ``raise_for_status()``: a failed request raises ``postgrest.APIError``.
- ``insert``/``upsert`` return the written rows by default, so no ``.select()``
  is needed afterwards.
- ``.single()`` raises when no row matches; ``.maybe_single()`` gives ``None``.

Keys: the backend is a trusted server, so it uses the service-role / secret
key when one is set (it bypasses row-level security). Without it, it falls
back to the anon / publishable key, and RLS-protected tables may silently
return no rows. Never give the service key a VITE_ prefix: anything prefixed
VITE_ is bundled into the browser.
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

BACKEND_DIR = Path(__file__).resolve().parent.parent  # .../backend
REPO_DIR = BACKEND_DIR.parent

# Load backend/.env no matter which directory the server is started from.
load_dotenv(BACKEND_DIR / ".env")


def _env(*names: str) -> Optional[str]:
    """First non-empty env var among ``names``."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
SUPABASE_URL = _env("SUPABASE_URL", "VITE_SUPABASE_URL")
_ANON_KEY = _env("SUPABASE_ANON_KEY", "VITE_SUPABASE_ANON_KEY")
_SERVICE_KEY = _env("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not (_ANON_KEY or _SERVICE_KEY):
    raise RuntimeError(
        "Supabase is not configured. Copy backend/.env.example to backend/.env "
        "and fill in SUPABASE_URL and at least one key."
    )

supabase_admin: Optional[Client] = (
    create_client(SUPABASE_URL, _SERVICE_KEY) if _SERVICE_KEY else None
)
# General-purpose client: service key if available, else anon key.
supabase: Client = supabase_admin or create_client(SUPABASE_URL, _ANON_KEY)

if supabase_admin is None:
    log.warning(
        "SUPABASE_SERVICE_ROLE_KEY not set; using the anon key. Tables with "
        "row-level security may return no rows and reject writes."
    )


def _require_admin() -> Client:
    if supabase_admin is None:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is not set. The case tables are protected "
            "by row-level security and cannot be read or written with the anon key."
        )
    return supabase_admin


# ---------------------------------------------------------------------------
# Generic helpers (every table below is a thin wrapper around these)
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
            f"Upsert into {table} returned no row (row-level security may be hiding it)."
        )
    return data[0]


def _delete(table: str, row_id: str) -> None:
    supabase.table(table).delete().eq("id", row_id).execute()


# ---------------------------------------------------------------------------
# profiles
# ---------------------------------------------------------------------------
def get_profiles() -> List[Dict[str, Any]]:
    return _list("profiles")


def get_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    return _get("profiles", profile_id)


def upsert_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a profile. ``profile`` must contain ``id``."""
    return _upsert("profiles", profile, require_id=True)


def delete_profile(profile_id: str) -> None:
    _delete("profiles", profile_id)


# ---------------------------------------------------------------------------
# residents
# ---------------------------------------------------------------------------
def get_residents() -> List[Dict[str, Any]]:
    return _list("residents")


def get_resident(resident_id: str) -> Optional[Dict[str, Any]]:
    """One resident by text ID, or None if it doesn't exist."""
    return _get("residents", resident_id)


def upsert_resident(resident: Dict[str, Any]) -> Dict[str, Any]:
    return _upsert("residents", resident, require_id=True)


def delete_resident(resident_id: str) -> None:
    _delete("residents", resident_id)


# ---------------------------------------------------------------------------
# care_notes
# ---------------------------------------------------------------------------
def get_care_notes(resident_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """All care notes, or one resident's notes, newest first."""
    q = supabase.table("care_notes").select("*")
    if resident_id:
        q = q.eq("resident_id", resident_id)
    return q.order("recorded_at", desc=True).execute().data


def get_care_note(note_id: str) -> Optional[Dict[str, Any]]:
    return _get("care_notes", note_id)


def upsert_care_note(note: Dict[str, Any]) -> Dict[str, Any]:
    """Insert (no ``id``) or update (with ``id``) a care note."""
    return _upsert("care_notes", note)


def delete_care_note(note_id: str) -> None:
    _delete("care_notes", note_id)


# ---------------------------------------------------------------------------
# observations
# ---------------------------------------------------------------------------
def get_observations(resident_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return _list("observations", resident_id=resident_id) if resident_id else _list("observations")


def get_observation(observation_id: str) -> Optional[Dict[str, Any]]:
    return _get("observations", observation_id)


def upsert_observation(observation: Dict[str, Any]) -> Dict[str, Any]:
    return _upsert("observations", observation)


def delete_observation(observation_id: str) -> None:
    _delete("observations", observation_id)


# ---------------------------------------------------------------------------
# alerts
# ---------------------------------------------------------------------------
def get_alerts() -> List[Dict[str, Any]]:
    return _list("alerts")


def get_alert(alert_id: str) -> Optional[Dict[str, Any]]:
    return _get("alerts", alert_id)


def upsert_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    return _upsert("alerts", alert)


def delete_alert(alert_id: str) -> None:
    _delete("alerts", alert_id)


# ---------------------------------------------------------------------------
# alert_evidence (junction table)
# ---------------------------------------------------------------------------
def get_alert_evidence(alert_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return _list("alert_evidence", alert_id=alert_id) if alert_id else _list("alert_evidence")


def link_alert_evidence(alert_id: str, observation_id: str) -> Dict[str, Any]:
    """Link an observation to an alert. Linking the same pair twice is a no-op."""
    data = supabase.table("alert_evidence").upsert(
        {"alert_id": alert_id, "observation_id": observation_id},
        on_conflict="alert_id,observation_id",
    ).execute().data
    return data[0] if data else {"alert_id": alert_id, "observation_id": observation_id}


def unlink_alert_evidence(alert_id: str, observation_id: str) -> None:
    supabase.table("alert_evidence").delete().eq("alert_id", alert_id).eq(
        "observation_id", observation_id
    ).execute()


# ---------------------------------------------------------------------------
# Similar-case retrieval (historical_cases, case_match_runs, case_matches)
# Those tables have row-level security: signed-in users can read, and only
# the service-role key can read or write from the backend. So everything here
# goes through `_require_admin()`, which fails loudly instead of returning [].
# ---------------------------------------------------------------------------
def _parse_vector(value: Any) -> Optional[List[float]]:
    """pgvector columns come back from the REST API as a string like '[0.1,0.2]'."""
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return list(value)


# --- case library ------------------------------------------------------------
CASE_COLUMNS = (
    "id", "case_summary", "observations", "timeline", "duration_days",
    "documented_outcome", "limitations", "outcome_category", "disposition",
)
DEFAULT_CASES_PATH = REPO_DIR / "test_data" / "cases.json"


def get_historical_cases() -> List[Dict[str, Any]]:
    return _require_admin().table("historical_cases").select(
        ", ".join(CASE_COLUMNS)
    ).execute().data


def seed_historical_cases(cases: List[Dict[str, Any]]) -> int:
    """Upsert the case library. Returns rows written.

    Unknown keys are dropped, so the seed file can carry extra fields.
    """
    rows = [{k: c[k] for k in CASE_COLUMNS if k in c} for c in cases]
    for r in rows:
        r["is_fictional"] = True
    resp = _require_admin().table("historical_cases").upsert(rows, on_conflict="id").execute()
    return len(resp.data)


def seed_historical_cases_from_file(path: str | Path = DEFAULT_CASES_PATH) -> int:
    with open(path, encoding="utf-8") as f:
        return seed_historical_cases(json.load(f))


def set_case_embedding(case_id: str, embedding: List[float], model: str) -> None:
    """Store one case's embedding. Call once per case at seed time."""
    _require_admin().table("historical_cases").update(
        {"embedding": embedding, "embedding_model": model}
    ).eq("id", case_id).execute()


def get_cases_for_matching() -> List[Dict[str, Any]]:
    """Every case with the fields the scorer needs, embeddings parsed to lists."""
    resp = _require_admin().table("historical_cases").select(
        "id, observations, timeline, duration_days, embedding, embedding_model"
    ).execute()
    for row in resp.data:
        row["embedding"] = _parse_vector(row.get("embedding"))
    return resp.data


# --- runs and matches --------------------------------------------------------
def alert_fingerprint(alert_id: str, scorer_version: str) -> str:
    """sha256 of the alert's sorted evidence IDs + scorer version.

    Same fingerprint means same inputs, so an existing run can be reused.
    """
    resp = _require_admin().table("alert_evidence").select("observation_id").eq(
        "alert_id", alert_id
    ).execute()
    ids = sorted(r["observation_id"] for r in resp.data)
    raw = json.dumps({"evidence": ids, "scorer": scorer_version})
    return hashlib.sha256(raw.encode()).hexdigest()


def get_match_run(alert_id: str, fingerprint: str) -> Optional[Dict[str, Any]]:
    """Return the run for this alert and fingerprint, or None if not computed yet."""
    resp = _require_admin().table("case_match_runs").select("*").eq(
        "alert_id", alert_id
    ).eq("alert_fingerprint", fingerprint).limit(1).execute()
    return resp.data[0] if resp.data else None


def save_match_run(run: Dict[str, Any], matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Insert one run and its ranked matches. Returns the run row.

    ``run`` needs: alert_id, alert_fingerprint, query_signals, query_duration_days,
    query_text, scorer_version, weights, candidates_seen (query_embedding optional).
    Each match needs: historical_case_id, rank, structured_score, temporal_score,
    total_score, shared_signals, case_only_signals, resident_only_signals
    (semantic_score and differences optional).

    The REST API has no multi-table transaction, so if the matches fail to insert
    the run is deleted again rather than left empty.
    """
    existing = get_match_run(run["alert_id"], run["alert_fingerprint"])
    if existing:
        return existing  # same inputs already scored

    admin = _require_admin()
    run_row = admin.table("case_match_runs").insert(run).execute().data[0]
    try:
        if matches:
            admin.table("case_matches").insert(
                [{**m, "run_id": run_row["id"]} for m in matches]
            ).execute()
    except Exception:
        admin.table("case_match_runs").delete().eq("id", run_row["id"]).execute()
        raise
    return run_row


def get_latest_case_matches(alert_id: str) -> List[Dict[str, Any]]:
    """Case cards for the similar-cases page, best match first."""
    resp = _require_admin().table("latest_case_matches").select("*").eq(
        "alert_id", alert_id
    ).order("rank").execute()
    return resp.data


def get_outcome_spread(alert_id: str) -> List[Dict[str, Any]]:
    """Outcome counts for the page header, most common first."""
    resp = _require_admin().table("latest_outcome_spread").select(
        "outcome_category, n"
    ).eq("alert_id", alert_id).order("n", desc=True).execute()
    return resp.data


def delete_match_runs(alert_id: str) -> None:
    """Drop all runs (and, by cascade, matches) for an alert, e.g. on demo reset."""
    _require_admin().table("case_match_runs").delete().eq("alert_id", alert_id).execute()


def ping() -> bool:
    """Cheap connectivity check for the /api/health endpoint."""
    supabase.table("residents").select("id").limit(1).execute()
    return True
