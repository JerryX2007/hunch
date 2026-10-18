"""Repository layer for the `observations` table."""

from typing import List, Optional, Dict, Any

from .. import database as _db
from ..utils.error_format import format_supabase_error, log_db_operation

__all__ = ["get_all", "get_by_id", "upsert", "delete"]


def get_all(resident_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all observations, optionally filtered by resident."""
    log_db_operation("SELECT", "observations")
    query = _db.supabase.table("observations").select("*")
    if resident_id:
        query = query.eq("resident_id", resident_id)
    return query.execute().data


def get_by_id(observation_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single observation by its primary key."""
    try:
        resp = _db.supabase.table("observations").select("*").eq("id", observation_id).maybe_single().execute()
        return resp.data if resp else None
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def upsert(observation: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update an observation."""
    log_db_operation("INSERT", "observations", ids=[observation.get("id")])
    try:
        data = _db.supabase.table("observations").upsert(observation, on_conflict="id").execute().data
        if not data:
            raise RuntimeError("upsert into observations returned no row (row-level security may be hiding it)")
        return data[0]
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def delete(observation_id: str) -> None:
    """Delete an observation by its primary key."""
    log_db_operation("DELETE", "observations", ids=[observation_id])
    try:
        _db.supabase.table("observations").delete().eq("id", observation_id).execute()
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e