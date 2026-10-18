"""Nurse sign-in (mounted at /api/auth)."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from .. import auth
from ..store import get_store

router = APIRouter(prefix="/auth", tags=["auth"])


class SignIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


def _me(request: Request, user: Optional[auth.User]) -> Dict[str, Any]:
    profile = get_store().profile(user.id) if user else None
    demo = auth.mode() == "demo"
    return {
        "signed_in": bool(user),
        "user": {"id": user.id, "email": user.email} if user else None,
        "profile": profile,
        "is_nurse": bool(auth.nurse_profile(request, user)),
        # Shown on the sign-in screen only when running on demo data.
        "demo_login": {"nurses": auth.DEMO_NURSES, "password": auth.DEMO_PASSWORD} if demo else None,
    }


@router.post("/signin")
def signin(body: SignIn, request: Request, response: Response) -> Dict[str, Any]:
    """Sign in with email + password. Sets the session cookies."""
    client = request.client.host if request.client else "unknown"
    session = auth.sign_in(body.email, body.password, client)
    auth.set_session_cookies(response, request, session)
    return _me(request, session["user"])


@router.get("/me")
def me(request: Request, user: Optional[auth.User] = Depends(auth.optional_user)) -> Dict[str, Any]:
    """Who is signed in on this browser. Never 401, so the page can always ask."""
    return _me(request, user)


@router.post("/logout")
def logout(request: Request, response: Response) -> Dict[str, bool]:
    """Sign out: ends the session and clears the cookies."""
    auth.sign_out(auth.token_from(request))
    auth.clear_session_cookies(response)
    return {"signed_in": False}
