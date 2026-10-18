"""The signed-in staff member's own profile (mounted at /api/profile)."""

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..store import get_store

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    role: Literal["RN", "RPN", "NP", "PSW", "other"]


@router.get("/me")
def my_profile(user_id: str = Depends(get_current_user)) -> Dict[str, Any]:
    """Your profile. 404 until you've added your name and role."""
    row = get_store().profile(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Add your name and role first.")
    return row


@router.put("/me")
def save_my_profile(body: ProfileUpdate, user_id: str = Depends(get_current_user)) -> Dict[str, Any]:
    """Create or update your profile (name and role)."""
    return get_store().save_profile({"id": user_id, **body.model_dump()})
