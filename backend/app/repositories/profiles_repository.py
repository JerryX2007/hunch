"""Repository layer for the `profiles` table."""

from typing import Any, Dict, List, Optional

from .. import database as _db
from ..utils.error_format import format_supabase_error, log_db_operation

__all__ = ["list_all", "get_by_id", "upsert", "delete"]


def list_all() -> List[Dict[str, Any]]:
    """Return every profile."""
    log_db_operation("SELECT", "profiles")
    return _db.supabase.table("profiles").select("*").execute().data


def get_by_id(profile_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single profile by its primary key."""
    try:
        resp = _db.supabase.table("profiles").select("*").eq("id", profile_id).maybe_single().execute()
        return resp.data if resp else None
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def upsert(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a profile. The dict must contain an ``id`` field."""
    log_db_operation("INSERT", "profiles", ids=[profile.get("id")])
    try:
        data = _db.supabase.table("profiles").upsert(profile, on_conflict="id").execute().data
        if not data:
            raise RuntimeError("upsert into profiles returned no row (row-level security may be hiding it)")
        return data[0]
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def delete(profile_id: str) -> None:
    """Delete a profile by its primary key."""
    log_db_operation("DELETE", "profiles", ids=[profile_id])
    try:
        _db.supabase.table("profiles").delete().eq("id", profile_id).execute()
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e