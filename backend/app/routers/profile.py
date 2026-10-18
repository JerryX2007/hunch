"""The signed-in staff member's own profile (mounted at /api/profile). Needs Supabase."""

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    role: Literal["PSW", "RPN", "RN", "NP", "other"]


def _repo():
    # Imported on use, so the API still starts in demo mode (no Supabase settings).
    from ..repositories import profiles_repository
    return profiles_repository


@router.get("/me")
def my_profile(user_id: str = Depends(get_current_user)) -> Dict[str, Any]:
    """Your profile. 404 until you've created it with PUT /api/profile/me."""
    row = _repo().get_by_id(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="No profile yet: create it with PUT /api/profile/me")
    return row


@router.put("/me")
def save_my_profile(body: ProfileUpdate, user_id: str = Depends(get_current_user)) -> Dict[str, Any]:
    """Create or update your profile (name and role)."""
    return _repo().upsert({"id": user_id, **body.model_dump()})
