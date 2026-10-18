"""History check, alerts and similar historical cases."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_nurse
from ..history import service
from ..schemas import StatusUpdate

router = APIRouter(tags=["history"], dependencies=[Depends(require_nurse)])  # nurse sign-in


@router.get("/history/check")
def check(resident_id: Optional[str] = None, evidence: bool = False) -> List[Dict[str, Any]]:
    """Compute the check live. Writes nothing. Most concerning residents first."""
    results = service.preview(resident_id)
    if resident_id and not results:
        raise HTTPException(status_code=404, detail="Resident not found")
    return [service.to_dict(c, include_evidence=evidence) for c in results]


@router.post("/history/run")
def run(resident_id: Optional[str] = None) -> Dict[str, Any]:
    """Compute and save: alerts, their evidence, summaries and similar historical cases."""
    return service.run(resident_id)


@router.get("/alerts")
def list_alerts(status: Optional[str] = "open") -> List[Dict[str, Any]]:
    """Alerts, urgent first then newest. Pass status= (empty) for every status."""
    return service.alerts(status or None)


@router.get("/alerts/{alert_id}")
def get_alert(alert_id: str) -> Dict[str, Any]:
    alert = service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/alerts/{alert_id}/status")
def set_status(alert_id: str, body: StatusUpdate) -> Dict[str, Any]:
    """Nurse review: reviewed / needs_assessment / dismissed (not useful) / open.
    A review status records what the nurse did; it is not a diagnosis."""
    alert = service.set_alert_status(alert_id, body.status)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/alerts/{alert_id}/similar-cases")
def similar_cases(alert_id: str) -> Dict[str, Any]:
    return service.similar_cases(alert_id)
