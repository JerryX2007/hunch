"""Which shift a moment belongs to.

Homes differ (8-hour 07/15/23 shifts, 12-hour shifts, a 2 pm change...), so the
boundaries live in one list you can edit instead of being scattered in code.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Toronto")

# (shift name, local start hour). Edit this to match the home.
SHIFT_STARTS: list[tuple[str, int]] = [("day", 7), ("evening", 15), ("night", 23)]


def shift_id(t: datetime) -> str:
    """Return a label like "2026-10-14-night".

    A night shift that crosses midnight belongs to the date it started on,
    so 02:00 on the 15th is part of the 14th's night shift.
    """
    if t.tzinfo is None:
        raise ValueError("Use timezone-aware datetimes, e.g. datetime(..., tzinfo=TZ)")
    local = t.astimezone(TZ)
    starts = sorted(SHIFT_STARTS, key=lambda s: s[1])
    started_today = [name for name, hour in starts if hour <= local.hour]
    if started_today:
        return f"{local.date().isoformat()}-{started_today[-1]}"
    # Before the first shift of the day: still in yesterday's last shift.
    yesterday = local.date() - timedelta(days=1)
    return f"{yesterday.isoformat()}-{starts[-1][0]}"
