from fastapi import APIRouter, Depends, HTTPException
from typing import List

from backend.app.schemas import ResidentRead, ResidentCreate
from backend.app.repositories.residents_repository import list_all, get_by_id, upsert as upsert_resident
from backend.app.dependencies import get_supabase

router = APIRouter(prefix="/api/residents", tags=["residents"])

@router.get("/", response_model=List[ResidentRead])
def get_residents(supabase=Depends(get_supabase)):
    """Get all residents."""
    return list_all()

@router.get("/{resident_id}", response_model=ResidentRead)
def get_resident(resident_id: str, supabase=Depends(get_supabase)):
    """Get a resident by ID."""
    resident = get_by_id(resident_id)
    if not resident:
        raise HTTPException(status_code=404, detail="Resident not found")
    return resident

@router.post("/", response_model=ResidentRead)
def create_resident(
    payload: ResidentCreate,
    supabase=Depends(get_supabase)
):
    """Create a new resident."""
    return upsert_resident(payload.dict())