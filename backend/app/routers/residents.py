"""Residents for the nurse dashboard and PSW page, plus their care notes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import User, nurse_profile, optional_user, require_nurse
from ..history import service
from ..schemas import NewNote, ResidentCreate
from ..store import get_store

router = APIRouter(prefix="/residents", tags=["residents"])


@router.get("")
def list_residents(request: Request, q: Optional[str] = None,
                   user: Optional[User] = Depends(optional_user)) -> List[Dict[str, Any]]:
    """Every resident with today's tier and their latest alert, most concerning first
    (signed-in nurses). Without sign-in, only IDs and names (for the PSW note screen).
    ``q`` filters by ID or name."""
    rows = service.resident_list(q)
    if nurse_profile(request, user):
        return rows
    return sorted(({"id": r["id"], "display_name": r["display_name"]} for r in rows), key=lambda r: r["display_name"])


@router.post("", status_code=201, dependencies=[Depends(require_nurse)])
def create_resident(body: ResidentCreate) -> Dict[str, Any]:
    """Add a resident (e.g. a new admission). 409 if the ID is taken."""
    if get_store().resident(body.id):
        raise HTTPException(status_code=409, detail=f"Resident {body.id} already exists")
    return service.add_resident(body.model_dump())


@router.get("/{resident_id}", dependencies=[Depends(require_nurse)])
def resident_overview(resident_id: str) -> Dict[str, Any]:
    """Everything the resident page needs: profile, live check with evidence,
    latest alert (with its summary and review status), similar cases, last 10 notes."""
    data = service.overview(resident_id)
    if not data:
        raise HTTPException(status_code=404, detail="Resident not found")
    return data


@router.get("/{resident_id}/notes", dependencies=[Depends(require_nurse)])
def resident_notes(resident_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    if not get_store().resident(resident_id):
        raise HTTPException(status_code=404, detail="Resident not found")
    return service.timeline(resident_id, max(1, min(limit, 200)))


@router.post("/{resident_id}/notes", status_code=201)
def add_note(resident_id: str, body: NewNote, request: Request,
             user: Optional[User] = Depends(optional_user)) -> Dict[str, Any]:
    """Log a care note (no sign-in needed: PSWs use this), then re-run the check for this
    resident. Without sign-in the reply says only whether the resident is flagged."""
    if not get_store().resident(resident_id):
        raise HTTPException(status_code=404, detail="Resident not found")
    nurse = nurse_profile(request, user)
    role = "Nurse" if nurse else body.author_role
    out = service.add_note(resident_id, body.note_text, role)
    if not nurse and out.get("result"):
        r = out["result"]
        out["result"] = {"resident_id": r["resident_id"], "tier": r["tier"], "title": r.get("title")}
    return out
