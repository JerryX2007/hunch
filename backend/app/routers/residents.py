"""Residents for the nurse dashboard and PSW page, plus their care notes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import User, nurse_profile, optional_user, require_nurse
from ..history import service
from ..schemas import NewNote, NewVitals, ResidentCreate
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
def create_resident(body: ResidentCreate, request: Request,
                    user: Optional[User] = Depends(optional_user)) -> Dict[str, Any]:
    """Add a resident (a new admission). Without ``id`` the next free unit ID is used.
    ``first_note`` is saved as their first care note, under the signed-in nurse's name.
    409 if the ID is taken."""
    name = body.display_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Enter the resident's name.")
    rid = (body.id or service.next_resident_id()).strip().upper()
    if get_store().resident(rid):
        raise HTTPException(status_code=409, detail=f"{rid} is already used by another resident. Pick another ID.")
    row = {"id": rid, "display_name": name, "baseline_start": body.baseline_start, "baseline_end": body.baseline_end}
    conditions = [c.strip() for c in (body.conditions or []) if c.strip()]
    if conditions:
        row["conditions"] = conditions
    resident = service.add_resident(row)
    if body.first_note and body.first_note.strip():
        nurse = nurse_profile(request, user)
        service.add_note(rid, body.first_note, "Nurse",
                         author_name=nurse.get("full_name") if nurse and user else None,
                         author_id=user.id if nurse and user else None)
    return resident


@router.get("/next-id", dependencies=[Depends(require_nurse)])
def next_id() -> Dict[str, str]:
    """The ID a new resident gets by default (e.g. 2W-023)."""
    return {"id": service.next_resident_id()}


@router.get("/{resident_id}", dependencies=[Depends(require_nurse)])
def resident_overview(resident_id: str) -> Dict[str, Any]:
    """Everything the resident page needs: profile, live check with evidence,
    latest alert (with its summary and review status), similar cases, last 10 notes."""
    data = service.overview(resident_id)
    if not data:
        raise HTTPException(status_code=404, detail="Resident not found")
    return data


@router.get("/{resident_id}/vitals", dependencies=[Depends(require_nurse)])
def resident_vitals(resident_id: str, limit: int = 10) -> Dict[str, Any]:
    """Recent vitals, each out-of-line value marked with why, and the resident's usual."""
    if not get_store().resident(resident_id):
        raise HTTPException(status_code=404, detail="Resident not found")
    check = service.preview(resident_id)
    return service.vitals_table(resident_id, check[0].vitals_usual if check else {}, max(1, min(limit, 200)))


@router.post("/{resident_id}/vitals", status_code=201)
def add_vitals(resident_id: str, body: NewVitals, request: Request,
               nurse: Dict[str, Any] = Depends(require_nurse),
               user: Optional[User] = Depends(optional_user)) -> Dict[str, Any]:
    """Chart a set of vitals (signed-in nurse), then re-run the check for this resident."""
    if not get_store().resident(resident_id):
        raise HTTPException(status_code=404, detail="Resident not found")
    try:
        return service.add_vitals(resident_id, body.model_dump(), author_name=nurse.get("full_name"),
                                  author_id=user.id if user else None)
    except RuntimeError as e:  # vitals table missing on Supabase
        raise HTTPException(status_code=503, detail=str(e)) from e


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
    if nurse and user:  # signed-in nurse: the note carries her name
        out = service.add_note(resident_id, body.note_text, "Nurse",
                               author_name=nurse.get("full_name"), author_id=user.id)
    else:
        out = service.add_note(resident_id, body.note_text, body.author_role)
    if not nurse and out.get("result"):
        r = out["result"]
        out["result"] = {"resident_id": r["resident_id"], "tier": r["tier"], "title": r.get("title")}
    return out
