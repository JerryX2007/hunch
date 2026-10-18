"""Nurse sign-in: individual accounts.

Two back ends, picked like the data store (app/store.py):

* Supabase mode: Supabase Auth, email + password. Accounts are created by whoever
  runs the system (no public sign-up):
      python -m scripts.create_nurse --email dana@example.com --name "Dana Lee"
* Demo mode: the unit's four fictional nurses (test_data/people.json) can sign in
  with password HUNCH_DEMO_PASSWORD (default hunch-demo). Demo sessions are signed
  by this server.

The browser never handles a token: sign-in sets HttpOnly, SameSite=Lax cookies, and
an expired Supabase session is renewed from the refresh cookie. API clients may send
``Authorization: Bearer <access_token>`` instead.

Everyone with an account is a nurse (profile role "nurse"). The nurse screen needs a
signed-in nurse; PSWs log notes on the note screen without signing in.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, Optional

from fastapi import Depends, HTTPException, Request, Response, status

from .store import DATA_DIR, get_store

ACCESS_COOKIE = "hunch_access"
REFRESH_COOKIE = "hunch_refresh"
NURSE_ROLE = "nurse"
DEMO_SESSION_SECONDS = 12 * 60 * 60
REFRESH_SECONDS = 30 * 24 * 60 * 60
MAX_FAILURES = 5          # wrong passwords allowed per address...
FAILURE_WINDOW = 5 * 60   # ...in this many seconds

DEMO_PASSWORD = os.getenv("HUNCH_DEMO_PASSWORD", "hunch-demo")
DEMO_NURSES = [{"name": n["name"], "email": n["email"].lower()}
               for n in json.loads((DATA_DIR / "people.json").read_text(encoding="utf-8"))["nurses"]]


def demo_user_id(email: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"hunch-demo:{email.lower()}"))


DEMO_EMAIL = DEMO_NURSES[0]["email"]          # used in tests
DEMO_USER_ID = demo_user_id(DEMO_EMAIL)


@dataclass
class User:
    id: str
    email: Optional[str]


def mode() -> str:
    return get_store().mode  # "demo" or "supabase"


def _unauthorized(detail: str = "Please sign in.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


# ---------------------------------------------------------------------------
# Supabase Auth
# ---------------------------------------------------------------------------
_shared_auth_client = None


def _supabase(service: bool = False):
    """A new client for calls that keep session state (sign-in, refresh, sign-out), so a
    user's session never ends up on a client someone else uses."""
    from . import database as db
    key = db._SERVICE_KEY if service else (db._ANON_KEY or db._SERVICE_KEY)
    if not key:
        raise HTTPException(status_code=503, detail="SUPABASE_SERVICE_ROLE_KEY is not set.")
    return db._client(key)


def _token_checker():
    """One shared client for get_user(token), which keeps no state: no new connection per request."""
    global _shared_auth_client
    if _shared_auth_client is None:
        _shared_auth_client = _supabase()
    return _shared_auth_client


def _session_dict(session, user) -> Dict[str, Any]:
    return {"access_token": session.access_token, "refresh_token": session.refresh_token,
            "expires_in": session.expires_in or 3600, "user": User(user.id, user.email)}


# ---------------------------------------------------------------------------
# Demo sessions: base64(json) + HMAC. Key from HUNCH_SECRET, else from the demo password,
# so sessions survive a restart and changing the password signs everyone out.
# ---------------------------------------------------------------------------
def _demo_key() -> bytes:
    return hashlib.sha256((os.getenv("HUNCH_SECRET") or f"hunch-demo-session:{DEMO_PASSWORD}").encode()).digest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _demo_token(user: User) -> str:
    body = _b64(json.dumps({"sub": user.id, "email": user.email,
                            "exp": int(time.time()) + DEMO_SESSION_SECONDS}).encode())
    return f"{body}.{hmac.new(_demo_key(), body.encode(), hashlib.sha256).hexdigest()}"


def _demo_verify(token: str) -> User:
    try:
        body, sig = token.rsplit(".", 1)
        if not hmac.compare_digest(sig, hmac.new(_demo_key(), body.encode(), hashlib.sha256).hexdigest()):
            raise ValueError("bad signature")
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if claims["exp"] < time.time():
            raise ValueError("expired")
        return User(claims["sub"], claims.get("email"))
    except Exception as e:  # noqa: BLE001
        raise _unauthorized("Your session has ended. Please sign in again.") from e


# ---------------------------------------------------------------------------
# Throttle wrong passwords per client address
# ---------------------------------------------------------------------------
_failures: Dict[str, Deque[float]] = defaultdict(deque)


def _recent_failures(who: str) -> Deque[float]:
    q = _failures[who]
    while q and q[0] < time.time() - FAILURE_WINDOW:
        q.popleft()
    return q


def _check_throttle(who: str) -> None:
    q = _recent_failures(who)
    if len(q) >= MAX_FAILURES:
        wait = int(q[0] + FAILURE_WINDOW - time.time()) + 1
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Too many wrong passwords. Try again in {max(wait // 60, 1)} minute(s).")


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------
def sign_in(email: str, password: str, client: str = "unknown") -> Dict[str, Any]:
    """Check email + password. Returns tokens and the user; 401 if wrong, 429 if too many tries."""
    _check_throttle(client)
    email = (email or "").strip().lower()
    try:
        if mode() == "demo":
            nurse = next((n for n in DEMO_NURSES if hmac.compare_digest(email.encode(), n["email"].encode())), None)
            ok = hmac.compare_digest((password or "").encode(), DEMO_PASSWORD.encode())
            if not (nurse and ok):
                raise _unauthorized("That email and password don’t match an account.")
            user = User(demo_user_id(nurse["email"]), nurse["email"])
            if not get_store().profile(user.id):
                get_store().save_profile({"id": user.id, "full_name": nurse["name"], "role": NURSE_ROLE})
            session = {"access_token": _demo_token(user), "refresh_token": None,
                       "expires_in": DEMO_SESSION_SECONDS, "user": user}
        else:
            try:
                res = _supabase().auth.sign_in_with_password({"email": email, "password": password})
            except HTTPException:
                raise
            except Exception as e:  # noqa: BLE001 - gotrue raises AuthApiError for bad credentials
                raise _unauthorized("That email and password don’t match an account.") from e
            if not res.session or not res.user:
                raise _unauthorized("That email and password don’t match an account.")
            session = _session_dict(res.session, res.user)
    except HTTPException as e:
        if e.status_code == 401:
            _failures[client].append(time.time())
        raise
    _failures.pop(client, None)
    return session


def verify(token: str) -> User:
    """The user an access token belongs to. 401 if invalid or expired."""
    if mode() == "demo":
        return _demo_verify(token)
    try:
        res = _token_checker().auth.get_user(token)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise _unauthorized("Your session has ended. Please sign in again.") from e
    if not res or not res.user:
        raise _unauthorized("Your session has ended. Please sign in again.")
    return User(res.user.id, res.user.email)


def refresh(refresh_token: str) -> Optional[Dict[str, Any]]:
    """New tokens from a refresh token (Supabase only). None if it no longer works."""
    if not refresh_token or mode() == "demo":
        return None
    try:
        res = _supabase().auth.refresh_session(refresh_token)
        return _session_dict(res.session, res.user) if res.session and res.user else None
    except Exception:  # noqa: BLE001
        return None


def sign_out(token: Optional[str]) -> None:
    """End the user's Supabase sessions everywhere; demo sessions just lose their cookie."""
    if not token or mode() == "demo":
        return
    try:
        _supabase(service=True).auth.admin.sign_out(token)
    except Exception:  # noqa: BLE001 - clearing the cookie still signs this browser out
        pass


# ---------------------------------------------------------------------------
# Cookies
# ---------------------------------------------------------------------------
def set_session_cookies(response: Response, request: Request, session: Dict[str, Any]) -> None:
    # Behind a host like Vercel the app may see plain http; the proxy says what the browser used.
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip()
    secure = request.url.scheme == "https" or forwarded == "https"
    response.set_cookie(ACCESS_COOKIE, session["access_token"], max_age=int(session["expires_in"]),
                        httponly=True, samesite="lax", secure=secure, path="/")
    if session.get("refresh_token"):
        response.set_cookie(REFRESH_COOKIE, session["refresh_token"], max_age=REFRESH_SECONDS,
                            httponly=True, samesite="lax", secure=secure, path="/")


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path="/")


def token_from(request: Request) -> Optional[str]:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return request.cookies.get(ACCESS_COOKIE)


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------
def optional_user(request: Request, response: Response) -> Optional[User]:
    """The signed-in user, or None. Renews an expired Supabase session from the refresh cookie."""
    token = token_from(request)
    if token:
        try:
            return verify(token)
        except HTTPException:
            pass
    session = refresh(request.cookies.get(REFRESH_COOKIE, ""))
    if session:
        set_session_cookies(response, request, session)
        return session["user"]
    return None


def get_current_user(user: Optional[User] = Depends(optional_user)) -> str:
    """The signed-in user's ID, or 401."""
    if not user:
        raise _unauthorized()
    return user.id


def _internal_caller(request: Request) -> bool:
    """run.py runs the startup check with a per-launch secret instead of a login."""
    expected = os.getenv("HUNCH_INTERNAL_TOKEN", "")
    return bool(expected) and hmac.compare_digest(request.headers.get("x-hunch-internal", "").encode(), expected.encode())


def nurse_profile(request: Request, user: Optional[User]) -> Optional[Dict[str, Any]]:
    """The caller's profile if they may use the nurse screen (signed in, profile set up), else None."""
    if _internal_caller(request):
        return {"id": "system", "full_name": "Hunch", "role": "system"}
    if not user:
        return None
    return get_store().profile(user.id)


def require_nurse(request: Request, user: Optional[User] = Depends(optional_user)) -> Dict[str, Any]:
    """Dependency for the nurse screen's endpoints."""
    profile = nurse_profile(request, user)
    if profile:
        return profile
    if not user:
        raise _unauthorized()
    raise HTTPException(status_code=403, detail="Add your name first.")
