"""Backend database connection and table helpers for Supabase.

This module centralizes the Supabase client creation and provides
high‑level, type‑annotated helpers for each table used in the project:

- profiles
- residents
- care_notes
- observations
- alerts
- historical_cases
- alert_evidence

The module is deliberately small and mock‑test friendly, making it easy
to unit‑test against a local Supabase emulator or a mocked client.
"""

import os
from typing import Any, Dict, List, Optional, Literal
from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------------------------
# The .env.example file defines VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.
# These are exported with the VITE_ prefix for front‑end usage, but the
# backend can read them directly. If the variables are not found, we fall
# back to the conventional names without the prefix.
load_dotenv()


def _get_env(var_with_prefix: str) -> Optional[str]:
    """Retrieve an env var that may be prefixed with ``VITE_``."""
    value = os.getenv(var_with_prefix)
    if value:
        return value
    # fallback to name without the prefix
    fallback = var_with_prefix.replace("VITE_", "")
    return os.getenv(fallback)


# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------
SUPABASE_URL = _get_env("VITE_SUPABASE_URL") or os.getenv("SUPABASE_URL")
SUPABASE_KEY = _get_env("VITE_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Supabase URL or anon key not found. "
        "Check .env.example and ensure the variables are exported."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------------------------------------------------------
# Table‑specific helpers
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# profiles
# ---------------------------------------------------------------------------
def get_profiles() -> List[Dict[str, Any]]:
    """Return all rows from the `profiles` table."""
    resp = supabase.table("profiles").select("*").execute()
    resp.raise_for_status()
    return resp.data


def upsert_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a profile. ``profile`` must contain ``id``."""
    pid = profile.get("id")
    if not pid:
        raise ValueError("Profile must have an 'id' field.")
    resp = supabase.table("profiles").upsert(profile).select("*").single()
    resp.raise_for_status()
    return resp.data


def delete_profile(profile_id: str) -> None:
    """Delete a profile by its primary key."""
    resp = supabase.table("profiles").delete().eq("id", profile_id).execute()
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# residents
# ---------------------------------------------------------------------------
def get_residents() -> List[Dict[str, Any]]:
    """Return all rows from the `residents` table."""
    resp = supabase.table("residents").select("*").execute()
    resp.raise_for_status()
    return resp.data


def get_resident(resident_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single resident by its text ID."""
    resp = supabase.table("residents").select("*").eq("id", resident_id).single().execute()
    resp.raise_for_status()
    return resp.data


def upsert_resident(resident: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a resident."""
    rid = resident.get("id")
    if not rid:
        raise ValueError("Resident must have an 'id' field.")
    resp = supabase.table("residents").upsert(resident).select("*").single()
    resp.raise_for_status()
    return resp.data


def delete_resident(resident_id: str) -> None:
    """Delete a resident."""
    resp = supabase.table("residents").delete().eq("id", resident_id).execute()
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# care_notes
# ---------------------------------------------------------------------------
def get_care_notes() -> List[Dict[str, Any]]:
    """Return all care notes."""
    resp = supabase.table("care_notes").select("*").execute()
    resp.raise_for_status()
    return resp.data


def get_care_note(note_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single care note by its UUID."""
    resp = supabase.table("care_notes").select("*").eq("id", note_id).single().execute()
    resp.raise_for_status()
    return resp.data


def upsert_care_note(note: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a care note."""
    resp = supabase.table("care_notes").upsert(note).select("*").single()
    resp.raise_for_status()
    return resp.data


def delete_care_note(note_id: str) -> None:
    """Delete a care note."""
    resp = supabase.table("care_notes").delete().eq("id", note_id).execute()
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# observations
# ---------------------------------------------------------------------------
def get_observations() -> List[Dict[str, Any]]:
    """Return all observations."""
    resp = supabase.table("observations").select("*").execute()
    resp.raise_for_status()
    return resp.data


def get_observation(observation_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single observation by its UUID."""
    resp = supabase.table("observations").select("*").eq("id", observation_id).single().execute()
    resp.raise_for_status()
    return resp.data


def upsert_observation(observation: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update an observation."""
    resp = supabase.table("observations").upsert(observation).select("*").single()
    resp.raise_for_status()
    return resp.data


def delete_observation(observation_id: str) -> None:
    """Delete an observation."""
    resp = supabase.table("observations").delete().eq("id", observation_id).execute()
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# alerts
# ---------------------------------------------------------------------------
def get_alerts() -> List[Dict[str, Any]]:
    """Return all alerts."""
    resp = supabase.table("alerts").select("*").execute()
    resp.raise_for_status()
    return resp.data


def upsert_alert(alert: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update an alert."""
    resp = supabase.table("alerts").upsert(alert).select("*").single()
    resp.raise_for_status()
    return resp.data


def delete_alert(alert_id: str) -> None:
    """Delete an alert."""
    resp = supabase.table("alerts").delete().eq("id", alert_id).execute()
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# historical_cases
# ---------------------------------------------------------------------------
def get_historical_cases() -> List[Dict[str, Any]]:
    """Return all historical cases."""
    resp = supabase.table("historical_cases").select("*").execute()
    resp.raise_for_status()
    return resp.data


def upsert_historical_case(case: Dict[str, Any]) -> Dict[str, Any]:
    """Insert or update a historical case."""
    resp = supabase.table("historical_cases").upsert(case).select("*").single()
    resp.raise_for_status()
    return resp.data


def delete_historical_case(case_id: str) -> None:
    """Delete a historical case."""
    resp = supabase.table("historical_cases").delete().eq("id", case_id).execute()
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# alert_evidence (junction table)
# ---------------------------------------------------------------------------
def get_alert_evidence() -> List[Dict[str, Any]]:
    """Return all alert‑evidence links."""
    resp = supabase.table("alert_evidence").select("*").execute()
    resp.raise_for_status()
    return resp.data


def link_alert_evidence(alert_id: str, observation_id: str) -> Dict[str, Any]:
    """Create a link between an alert and an observation."""
    resp = supabase.table("alert_evidence").insert(
        {"alert_id": alert_id, "observation_id": observation_id}
    ).execute()
    resp.raise_for_status()
    return resp.data


def unlink_alert_evidence(alert_id: str, observation_id: str) -> None:
    """Remove the link between an alert and an observation."""
    resp = supabase.table("alert_evidence").delete().eq("alert_id", alert_id).eq(
        "observation_id", observation_id
    ).execute()
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Mock‑testing utilities (optional)
# ---------------------------------------------------------------------------
if os.getenv("RUN_MOCKS", "false").lower() == "true":
    # When this script is executed directly, run a tiny sanity‑check.
    async def _run_mock_tests() -> None:
        """Placeholder for async pytest‑style mock tests."""
        # Example:
        # from unittest.mock import Mock
        # mock_client = Mock()
        # mock_client.table.return_value.select.return_value.execute.return_value = Mock(data=[{ "id": "test" }])
        # supabase = mock_client
        # assert get_profiles() == [{"id": "test"}]
        # print("✅ Mock tests passed.")
        pass

    # Allow `python -m backend.database` to run the mock suite.
    import asyncio

    asyncio.run(_run_mock_tests())