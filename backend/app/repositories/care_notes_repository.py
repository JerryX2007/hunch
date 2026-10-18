"""Repository layer for the `care_notes` table."""

from typing import List, Optional, Dict, Any

from .. import database as _db
from ..utils.error_format import format_supabase_error, log_db_operation

__all__ = ["list_all", "get_by_id", "upsert", "delete"]


def list_all(resident_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all care notes, optionally filtered by resident."""
    log_db_operation("SELECT", "care_notes")
    query = _db.supabase.table("care_notes").select("*")
    if resident_id:
        query = query.eq("resident_id", resident_id)
    return query.order("recorded_at", desc=True).execute().data


def get_by_id(note_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single care note by its primary key."""
    try:
        resp = _db.supabase.table("care_notes").select("*").eq("id", note_id).maybe_single().execute()
        return resp.data if resp else None
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def upsert(note: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a care note."""
    log_db_operation("INSERT", "care_notes", ids=[note.get("id")])
    try:
        data = _db.supabase.table("care_notes").upsert(note, on_conflict="id").execute().data
        if not data:
            raise RuntimeError("upsert into care_notes returned no row (row-level security may be hiding it)")
        return data[0]
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def delete(note_id: str) -> None:
    """Delete a care note by its primary key."""
    log_db_operation("DELETE", "care_notes", ids=[note_id])
    try:
        _db.supabase.table("care_notes").delete().eq("id", note_id).execute()
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e