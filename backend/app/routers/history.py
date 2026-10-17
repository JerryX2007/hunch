"""History check: compare residents with their own past notes, and with past cases."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from ..history import service

router = APIRouter(tags=["history"])


@router.get("/history/check")
def check(resident_id: Optional[str] = None, evidence: bool = False) -> List[Dict[str, Any]]:
    """Compute the check live. Writes nothing. Most concerning residents first."""
    results = service.preview(resident_id)
    if resident_id and not results:
        raise HTTPException(status_code=404, detail="Resident not found")
    return [service.to_dict(c, include_evidence=evidence) for c in results]


@router.post("/history/run")
def run() -> Dict[str, Any]:
    """Compute and save: alerts, their evidence, and similar historical cases."""
    return service.run()


@router.get("/alerts")
def list_alerts(status: Optional[str] = "open") -> List[Dict[str, Any]]:
    db = service._db()
    q = db.supabase.table("alerts").select("id, resident_id, title, summary, status, urgent, created_at")
    if status:
        q = q.eq("status", status)
    rows = q.order("created_at", desc=True).execute().data
    return sorted(rows, key=lambda a: not a["urgent"])  # urgent first, then newest


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str) -> Dict[str, Any]:
    alert = service._db().get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/alerts/{alert_id}/similar-cases")
def similar_cases(alert_id: str) -> Dict[str, Any]:
    db = service._db()
    return {
        "alert_id": alert_id,
        "note": "Fictional case library. Shows what happened in similar past cases; not a diagnosis.",
        "outcomes": db.get_outcome_spread(alert_id),
        "cases": db.get_latest_case_matches(alert_id),
    }
