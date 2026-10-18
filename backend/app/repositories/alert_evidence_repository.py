"""Repository layer for the `alert_evidence` table."""

from typing import Any, Dict, List, Optional

from backend.app.database import supabase
from backend.app.utils.error_format import format_supabase_error, log_db_operation

__all__ = ["get_all", "link", "unlink"]


def get_all(alert_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return all links, optionally filtered by alert."""
    log_db_operation("SELECT", "alert_evidence")
    query = supabase.table("alert_evidence")
    if alert_id:
        query = query.eq("alert_id", alert_id)
    return query.execute().data


def link(alert_id: str, observation_id: str) -> Dict[str, Any]:
    """Create a link between an alert and an observation."""
    log_db_operation("INSERT", "alert_evidence", ids=[alert_id, observation_id])
    try:
        data = supabase.table("alert_evidence").upsert(
            {"alert_id": alert_id, "observation_id": observation_id},
            on_conflict=["alert_id", "observation_id"],
        ).execute().data
        return data[0] if data else {"alert_id": alert_id, "observation_id": observation_id}
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e


def unlink(alert_id: str, observation_id: str) -> None:
    """Remove the link between an alert and an observation."""
    log_db_operation("DELETE", "alert_evidence", ids=[alert_id, observation_id])
    try:
        supabase.table("alert_evidence").delete().eq("alert_id", alert_id).eq(
            "observation_id", observation_id
        ).execute()
    except Exception as e:
        raise RuntimeError(format_supabase_error(e)) from e