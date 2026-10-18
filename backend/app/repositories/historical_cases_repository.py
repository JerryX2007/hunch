"""Repository layer for the `historical_cases` table and similar-case results.

Thin wrappers over app/database.py, which holds the tested implementations
(embedding parsing, run re-use by fingerprint, rollback on failed inserts).
"""

from typing import Any, Dict, List

from .. import database as _db
from ..utils.error_format import format_supabase_error, log_db_operation

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
    return _db.get_historical_cases()


def seed_from_file(path: str) -> int:
    """Upsert the case library from a JSON file. Returns rows written."""
    return _db.seed_historical_cases_from_file(path)


def seed_from_json(cases: List[Dict[str, Any]]) -> int:
    """Upsert a list of case dicts. Returns rows written."""
    log_db_operation("INSERT", "historical_cases", ids=[c.get("id") for c in cases])
    try:
        return _db.seed_historical_cases(cases)
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def set_embedding(case_id: str, embedding: List[float], model: str) -> None:
    """Store an embedding for a case."""
    _db.set_case_embedding(case_id, embedding, model)


def get_cases_for_matching() -> List[Dict[str, Any]]:
    """Every case with the fields needed for matching, embeddings parsed to lists."""
    return _db.get_cases_for_matching()


def save_match_run(run: Dict[str, Any], matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Insert a new run and its ranked matches (re-uses a run with the same fingerprint)."""
    return _db.save_match_run(run, matches)


def get_latest_case_matches(alert_id: str) -> List[Dict[str, Any]]:
    """Return case cards ordered by rank."""
    return _db.get_latest_case_matches(alert_id)


def get_outcome_spread(alert_id: str) -> List[Dict[str, Any]]:
    """Return outcome counts for the header, most common first."""
    return _db.get_outcome_spread(alert_id)


def delete_match_runs(alert_id: str) -> None:
    """Drop all runs (and, by cascade, matches) for an alert."""
    _db.delete_match_runs(alert_id)


def ping() -> bool:
    """Cheap connectivity check."""
    return _db.ping()
