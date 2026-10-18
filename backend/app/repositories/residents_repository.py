"""Repository layer for the `residents` table."""

from typing import Any, Dict, List, Optional

from .. import database as _db
from ..utils.error_format import format_supabase_error, log_db_operation

__all__ = ["list_all", "get_by_id", "upsert", "delete"]


def list_all() -> List[Dict[str, Any]]:
    """Return every resident, ordered by ID."""
    log_db_operation("SELECT", "residents")
    return _db.supabase.table("residents").select("*").order("id").execute().data


def get_by_id(resident_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single resident by its text ID (e.g. 2W-014)."""
    try:
        resp = _db.supabase.table("residents").select("*").eq("id", resident_id).maybe_single().execute()
        return resp.data if resp else None
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def upsert(resident: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a resident. The dict must contain ``id``."""
    if not resident.get("id"):
        raise ValueError("residents row must have an 'id' field.")
    log_db_operation("INSERT", "residents", ids=[resident["id"]])
    try:
        data = _db.supabase.table("residents").upsert(resident, on_conflict="id").execute().data
        if not data:
            raise RuntimeError("upsert into residents returned no row (row-level security may be hiding it)")
        return data[0]
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def delete(resident_id: str) -> None:
    """Delete a resident (their notes, observations and alerts cascade)."""
    log_db_operation("DELETE", "residents", ids=[resident_id])
    try:
        _db.supabase.table("residents").delete().eq("id", resident_id).execute()
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e
