"""Repository layer for the `care_notes` table."""

from typing import List, Optional, Dict, Any

from backend.app.database import supabase
from backend.app.utils.error_format import format_supabase_error, log_db_operation

__all__ = ["list_all", "get_by_id", "upsert", "delete"]


def list_all(resident_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all care notes, optionally filtered by resident."""
    log_db_operation("SELECT", "care_notes")
    query = supabase.table("care_notes").select("*")
    if resident_id:
        query = query.eq("resident_id", resident_id)
    return query.order("recorded_at", desc=True).execute().data


def get_by_id(note_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single care note by its primary key."""
    try:
        resp = supabase.table("care_notes").select("*").eq("id", note_id).maybe_single().execute()
        return resp.data if resp else None
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def upsert(note: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a care note."""
    log_db_operation("INSERT", "care_notes", ids=[note.get("id")])
    try:
        return supabase.table("care_notes").upsert(note).select("*").single().execute().data
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def delete(note_id: str) -> None:
    """Delete a care note by its primary key."""
    log_db_operation("DELETE", "care_notes", ids=[note_id])
    try:
        supabase.table("care_notes").delete().eq("id", note_id).execute()
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e