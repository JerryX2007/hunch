from typing import Any, Dict

from fastapi import APIRouter

from ..history.narrative import llm_enabled
from ..store import get_store

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> Dict[str, Any]:
    """Is the API up, which data store is in use, and can it be reached?"""
    out: Dict[str, Any] = {"status": "ok", "llm": llm_enabled()}
    try:
        store = get_store()
        out["mode"] = store.mode
        store.ping()
        out["database"] = "ok"
    except Exception as e:  # noqa: BLE001 - report, don't crash the health check
        out["database"] = f"error: {type(e).__name__}: {str(e)[:200]}"
    return out
