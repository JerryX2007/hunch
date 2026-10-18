"""Auth related utilities for Supabase authentication.

Provides:
- password-based sign-in (email/password)
- token verification
- session expiration check
- logout (session revocation)
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from backend.app.database import supabase

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# Use the same URL/key that backend.database uses
SUPABASE_URL = supabase.url
SUPABASE_SERVICE_KEY = supabase.service_role_key if supabase.service_role_key else supabase.service_role_key  # noqa: E701

# 24‑hour session lifetime (in seconds)
SESSION_TTL = 24 * 60 * 60

# ---------------------------------------------------------------------------
# Utility: verify JWT token from Supabase public JWKs
# ---------------------------------------------------------------------------
def verify_jwt(token: str) -> dict:
    """Validate Supabase JWT and return payload.
    Raises HTTPException(401) on failure.
    """
    # Supabase publishes its public JWKs at: https://<PROJECT>.supabase.co/public/v1/token/jwks
    PUBLIC_JWKS_URL = f"{SUPABASE_URL}/token/jwks"
    response = httpx.get(PUBLIC_JWKS_URL, timeout=5.0)
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Unable to fetch JWKS from Supabase")
    jwks = response.json()

    try:
        payload = jwt.decode(token, jwks, algorithms=["RS256"], audience="client")
        # `exp` is a datetime; check expiration
        exp: datetime = datetime.fromtimestamp(payload["exp"])
        if datetime.utcnow() > exp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Token expired")
        return payload
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or expired authentication token")

# ---------------------------------------------------------------------------
# Password grant sign‑in (email/password) – wrapper around Supabase's /token endpoint
# ---------------------------------------------------------------------------
def sign_in(email: str, password: str) -> dict:
    """Perform password grant type request to Supabase Auth API.
    Returns the JSON response (access_token, refresh_token, userdata)."""
    async def _internal() -> dict:
        async with httpx.AsyncClient() as client:
            payload = {
                "grant_type": "password",
                "client_id": SUPABASE_SERVICE_KEY or "dummy",
                "client_secret": SUPABASE_SERVICE_KEY or "dummy",
                "username": email,
                "password": password,
            }
            resp = await client.post(
                f"{SUPABASE_URL}/auth/v1/token",
                data=payload,
                headers={"appliesTo": "API-client"},
            )
            resp.raise_for_status()
            return resp.json()
    # Run async function synchronously (FastAPI will call it async)
    return asyncio.run(_internal())

# ---------------------------------------------------------------------------
# Dependency for FastAPI that extracts and validates the JWT token
# ---------------------------------------------------------------------------
def get_current_user(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/token")),
) -> str:
    """
    Extract and validate the JWT token, returning the user ID.
    Raises HTTPException(401) if the token is missing, malformed, or expired.
    """
    payload = verify_jwt(token)
    return payload["sub"]  # `sub` is the user ID in Supabase

# ---------------------------------------------------------------------------
# Session revocation helper
# ---------------------------------------------------------------------------
async def revoke_session(session_id: str) -> bool:
    """Revoke a session using the Supabase Admin API.
    Returns True if a row was deleted, else False."""
    # The session ID is stored in the JWT's `session_id` claim.
    payload = verify_jwt(token)  # reuse verification
    session_id = payload.get("session_id")
    if not session_id:
        return False
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{SUPABASE_URL}/session/v1/session/{session_id}",
            headers={"apikey": SUPABASE_SERVICE_KEY},
        )
        return resp.status_code == 204

# ---------------------------------------------------------------------------
# Password‑based sign‑in endpoint (optional FastAPI route)
# ---------------------------------------------------------------------------
async def sign_in(email: str, password: str) -> dict:
    """Wrapper around Supabase's password‑grant sign‑in."""
    # The inner function `sign_in` is defined async; we call it sync‑style
    result = asyncio.run(_internal_sign_in(email, password))
    return result

async def _internal_sign_in(email: str, password: str) -> dict:
    """Actual async request to Supabase auth token endpoint."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/auth/v1/token",
            data={"grant_type": "password",
                  "client_id": SUPABASE_SERVICE_KEY or "dummy",
                  "client_secret": SUPABASE_SERVICE_KEY or "dummy",
                  "username": email,
                  "password": password},
                headers={"appliesTo": "API-client"},
            )
        resp.raise_for_status()
        return resp.json()