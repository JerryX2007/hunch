"""Each resident's own normal.

The baseline is the median of a 14-day window that ENDS 48 hours ago, so an
illness that started yesterday can't drag "normal" toward itself.
"""

from datetime import datetime, timedelta
from statistics import median

from engine.models import Reading


def of_kind(readings: list[Reading], kind: str) -> list[Reading]:
    return [r for r in readings if r.kind == kind]


def baseline(
    readings: list[Reading],
    kind: str,
    now: datetime,
    days: int = 14,
    skip_hours: int = 48,
    min_points: int = 5,
) -> float | None:
    """Median value of `kind` in the window [now - skip - days, now - skip).

    Returns None when there are too few readings to trust; rules then fall back
    to absolute thresholds only.
    """
    end = now - timedelta(hours=skip_hours)
    start = end - timedelta(days=days)
    values = [r.value for r in of_kind(readings, kind) if start <= r.time < end]
    if len(values) < min_points:
        return None
    return median(values)


def latest(
    readings: list[Reading], kind: str, now: datetime, within_hours: int = 24
) -> Reading | None:
    """The most recent reading of `kind` in the last `within_hours`, if any."""
    since = now - timedelta(hours=within_hours)
    recent = [r for r in of_kind(readings, kind) if since < r.time <= now]
    return max(recent, key=lambda r: r.time) if recent else None
