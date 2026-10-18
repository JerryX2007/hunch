"""Authentication routes for caregiver login."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional

from backend.app.auth import sign_in, revoke_session
from backend.app.auth import verify_jwt

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Password grant sign‑in (email + password)
# ---------------------------------------------------------------------------
@router.post("/signin", status_code=status.HTTP_200_OK)
async def signin(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate using email/password.
    Returns a JSON containing the access token and basic user data.
    """
    if not form_data.username or not form_data.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Missing email or password")
    # Use the low‑level sign‑in function that talks to Supabase
    result = sign_in(form_data.username, form_data.password)
    # The result contains: access_token, refresh_token, user (incl. user.id)
    return {
        "access_token": result["access_token"],
        "refresh_token": result.get("refresh_token"),
        "user": result["user"],
    }

# ---------------------------------------------------------------------------
# Token verification dependency
# ---------------------------------------------------------------------------
async def get_current_user(token: str = Depends(OAuth2PasswordBearer())) -> str:
    """
    Validate the JWT token and return the user ID.
    Raises 401 if token is missing/invalid/expired.
    """
    # The verify_jwt function lives in backend/app/auth.py
    from backend.app.auth import verify_jwt
    payload = verify_jwt(token)
    return payload["sub"]  # user ID


# ---------------------------------------------------------------------------
# Logout (session revocation)
# ---------------------------------------------------------------------------
@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(session_id: str = Depends(lambda: None)):  # placeholder – actual session_id extraction below
    """
    Revoke a session using the session ID.
    In practice the client will send the session ID obtained from the JWT.
    """
    # Supabase provides a session revocation endpoint.
    # Here we simply forward to the utility function; it returns True on success.
    result = revoke_session(session_id)
    if result:
        return {"detail": "Session revoked"}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Unable to revoke session")