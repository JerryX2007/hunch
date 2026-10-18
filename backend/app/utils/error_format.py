"""Utility functions for formatting Supabase errors and logging."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def format_supabase_error(error: Any) -> str:
    """Convert a Supabase API error into a concise plain‑text message.

    The function handles the two most common cases:
    1. ``postgrest.APIError`` with a ``msg`` attribute.
    2. Any other exception – its string representation is returned.

    The returned string is suitable for logging or for presenting to end‑users.
    """
    if hasattr(error, "msg"):
        # type: ignore[attr-defined]
        return f"Supabase error: {error.msg}"
    # fallback – return whatever we have
    return f"Supabase error: {error}"


def log_db_operation(operation: str, table: str, ids: list | None = None) -> None:
    """Log a database operation at INFO level.

    Parameters
    ----------
    operation: str
        One of "SELECT", "INSERT", "UPDATE", "DELETE".
    table: str
        Name of the table involved.
    ids: list | None
        Optional list of record IDs affected. If provided, they are logged.
    """
    msg = f"DB {operation} on table '{table}'"
    if ids:
        msg += f" (ids={ids})"
    logger.info(msg)