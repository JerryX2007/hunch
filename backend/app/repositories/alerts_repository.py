"""Repository layer for the `alerts` table."""

from typing import Any, Dict, List, Optional

from backend.app.database import supabase
from backend.app.utils.error_format import format_supabase_error, log_db_operation

__all__ = ["get_all", "get_by_id", "upsert", "delete"]


def get_all() -> List[Dict[str, Any]]:
    """Return every alert."""
    log_db_operation("SELECT", "alerts")
    return supabase.table("alerts").select("*").execute().data


def get_by_id(alert_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single alert by its primary key."""
    try:
        resp = supabase.table("alerts").select("*").eq("id", alert_id).maybe_single().execute()
        return resp.data if resp else None
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def upsert(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update an alert."""
    log_db_operation("INSERT", "alerts", ids=[alert.get("id")])
    try:
        return supabase.table("alerts").upsert(alert, on_conflict="id").select("*").single().execute().data
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def delete(alert_id: str) -> None:
    """Delete an alert by its primary key."""
    log_db_operation("DELETE", "alerts", ids=[alert_id])
    try:
        supabase.table("alerts").delete().eq("id", alert_id).execute()
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e