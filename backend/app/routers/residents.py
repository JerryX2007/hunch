"""Residents for the nurse dashboard and PSW page, plus their care notes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from ..history import service
from ..schemas import NewNote, ResidentCreate
from ..store import get_store

router = APIRouter(prefix="/residents", tags=["residents"])


@router.get("")
def list_residents(q: Optional[str] = None) -> List[Dict[str, Any]]:
    """Every resident with today's tier and their latest alert, most concerning first.
    ``q`` filters by ID or name."""
    return service.resident_list(q)


@router.post("", status_code=201)
def create_resident(body: ResidentCreate) -> Dict[str, Any]:
    """Add a resident (e.g. a new admission). 409 if the ID is taken."""
    if get_store().resident(body.id):
        raise HTTPException(status_code=409, detail=f"Resident {body.id} already exists")
    return service.add_resident(body.model_dump())


@router.get("/{resident_id}")
def resident_overview(resident_id: str) -> Dict[str, Any]:
    """Everything the resident page needs: profile, live check with evidence,
    latest alert (with its summary and review status), similar cases, last 10 notes."""
    data = service.overview(resident_id)
    if not data:
        raise HTTPException(status_code=404, detail="Resident not found")
    return data


@router.get("/{resident_id}/notes")
def resident_notes(resident_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    if not get_store().resident(resident_id):
        raise HTTPException(status_code=404, detail="Resident not found")
    return service.timeline(resident_id, max(1, min(limit, 200)))


@router.post("/{resident_id}/notes", status_code=201)
def add_note(resident_id: str, body: NewNote) -> Dict[str, Any]:
    """Log a care note (e.g. from the PSW page), then re-run the check for this resident."""
    if not get_store().resident(resident_id):
        raise HTTPException(status_code=404, detail="Resident not found")
    return service.add_note(resident_id, body.note_text, body.author_role)
