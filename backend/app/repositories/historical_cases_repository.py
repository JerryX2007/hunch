"""Repository layer for the `historical_cases` table."""

from typing import List, Dict, Any, Optional

from backend.app.database import supabase, _require_admin
from backend.app.utils.error_format import format_supabase_error, log_db_operation
import json

__all__ = [
    "get_all",
    "seed_from_file",
    "seed_from_json",
    "set_embedding",
    "get_cases_for_matching",
    "save_match_run",
    "get_latest_case_matches",
    "get_outcome_spread",
    "delete_match_runs",
    "ping",
]


def get_all() -> List[Dict[str, Any]]:
    """Return every historical case."""
    log_db_operation("SELECT", "historical_cases")
    resp = supabase.table("historical_cases").select("*").execute()
    return resp.data


def seed_from_file(path: str) -> int:
    """Upsert the case library from a JSON file. Returns rows written."""
    with open(path, encoding="utf-8") as f:
        cases = json.load(f)
    return seed_from_json(cases)


def seed_from_json(cases: List[Dict[str, Any]]) -> int:
    """Upsert a list of case dicts. Returns rows written."""
    # When running without the service key, we simply return 0.
    if not supabase:
        return 0
    try:
        rows = [
            {k: c[k] for k in ("id", "case_summary", "observations", "timeline", "duration_days", "documented_outcome", "limitations", "outcome_category", "disposition") if k in c}
            for c in cases
        ]
        admin = _require_admin()
        resp = admin.table("historical_cases").upsert(rows, on_conflict="id").execute()
        return len(resp.data)
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def set_embedding(case_id: str, embedding: List[float], model: str) -> None:
    """Store an embedding for a case."""
    admin = _require_admin()
    admin.table("historical_cases").update(
        {"embedding": embedding, "embedding_model": model}
    ).eq("id", case_id).execute()


def get_cases_for_matching() -> List[Dict[str, Any]]:
    """Return every case with the fields needed for matching, embedding parsed."""
    admin = _require_admin()
    resp = admin.table("historical_cases").select(
        "id, observations, timeline, duration_days, embedding, embedding_model"
    ).execute()
    for row in resp.data:
        row["embedding"] = json.loads(row.get("embedding", "[]"))
    return resp.data


def save_match_run(run: Dict[str, Any], matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Insert a new run and its ranked matches."""
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
    """Return case cards ordered by rank."""
    admin = _require_admin()
    resp = admin.table("latest_case_matches").select("*").eq("alert_id", alert_id).order("rank").execute()
    return resp.data


def get_outcome_spread(alert_id: str) -> List[Dict[str, Any]]:
    """Return outcome counts for the header, most common first."""
    admin = _require_admin()
    resp = admin.table("latest_outcome_spread").select(
        "outcome_category, n"
    ).eq("alert_id", alert_id).order("n", desc=True).execute()
    return resp.data


def delete_match_runs(alert_id: str) -> None:
    """Drop all runs (and, by cascade, matches) for an alert."""
    admin = _require_admin()
    admin.table("case_match_runs").delete().eq("alert_id", alert_id).execute()


def ping() -> bool:
    """Cheap connectivity check – just selects one resident."""
    supabase.table("residents").select("id").limit(1).execute()
    return True