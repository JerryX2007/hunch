"""Staff sign-in with Supabase Auth (email + password).

    sign_in(email, password) -> {access_token, refresh_token, expires_at, user}
    verify_jwt(token)        -> {"sub": user_id, "email": ...}   (401 if invalid/expired)
    get_current_user         -> FastAPI dependency returning the user ID
    revoke_session(token)    -> sign the user out everywhere (needs the service key)

Each call uses its own short-lived Supabase client, so a user's session never
replaces the backend's service-role client used by the rest of the app.
Needs Supabase; in demo mode these return 503.
"""

from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/signin")

# 24-hour session lifetime (in seconds); Supabase's JWT expiry is set in the dashboard.
SESSION_TTL = 24 * 60 * 60


def _database():
    try:
        from . import database
    except RuntimeError as e:  # backend/.env has no Supabase URL/key
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail=f"Sign-in needs Supabase: {e}") from e
    return database


def _client(service: bool = False):
    from supabase import create_client
    db = _database()
    key = db._SERVICE_KEY if service else (db._ANON_KEY or db._SERVICE_KEY)
    if not key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="SUPABASE_SERVICE_ROLE_KEY is not set.")
    return create_client(db.SUPABASE_URL, key)


def sign_in(email: str, password: str) -> Dict[str, Any]:
    """Password sign-in. Returns the tokens and basic user data."""
    try:
        res = _client().auth.sign_in_with_password({"email": email, "password": password})
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001 - gotrue raises AuthApiError for bad credentials
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid email or password") from e
    if not res.session or not res.user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign-in failed")
    return {
        "access_token": res.session.access_token,
        "refresh_token": res.session.refresh_token,
        "expires_at": res.session.expires_at,
        "user": {"id": res.user.id, "email": res.user.email},
    }


def verify_jwt(token: str) -> Dict[str, Any]:
    """Ask Supabase whether the access token is valid (also rejects expired tokens)."""
    try:
        res = _client().auth.get_user(token)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired authentication token") from e
    if not res or not res.user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired authentication token")
    return {"sub": res.user.id, "email": res.user.email}


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """FastAPI dependency: the signed-in user's ID, or 401."""
    return verify_jwt(token)["sub"]


def revoke_session(token: str) -> bool:
    """Sign the token's user out of every session. True on success."""
    verify_jwt(token)
    try:
        _client(service=True).auth.admin.sign_out(token)
        return True
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        return False
