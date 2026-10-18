"""Authentication routes for caregiver login (mounted at /api/auth)."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..auth import oauth2_scheme, revoke_session, sign_in, verify_jwt

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signin", status_code=status.HTTP_200_OK)
def signin(form_data: OAuth2PasswordRequestForm = Depends()) -> Dict[str, Any]:
    """Authenticate with email (form field ``username``) and password.
    Returns the access token, refresh token and basic user data."""
    if not form_data.username or not form_data.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing email or password")
    return sign_in(form_data.username, form_data.password)


@router.get("/me")
def me(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """The signed-in user (send ``Authorization: Bearer <access_token>``)."""
    return verify_jwt(token)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(token: str = Depends(oauth2_scheme)) -> Dict[str, str]:
    """Revoke the user's sessions."""
    if revoke_session(token):
        return {"detail": "Session revoked"}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to revoke session")
