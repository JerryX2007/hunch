"""Small builders for FICTIONAL test data.

Used by both the tests and demo.py. Values cycle usual-j, usual, usual+j so the
median baseline equals `usual` exactly, which keeps test numbers predictable.
"""

from datetime import datetime, timedelta
from itertools import count

from engine.models import Hunch, Reading, Sign
from engine.shifts import TZ

_ids = count(1)


def new_id(prefix: str) -> str:
    return f"{prefix}{next(_ids)}"


def at(day: int, hour: int, minute: int = 0) -> datetime:
    """A moment in October 2026, Toronto time. at(14, 20) = 14 Oct 2026, 8 pm."""
    return datetime(2026, 10, day, hour, minute, tzinfo=TZ)


def history(resident_id: str, kind: str, usual: float, now: datetime,
            days: int = 16, jitter: float = 0.0) -> list[Reading]:
    """One reading per day for the `days` days before `now`, same clock time."""
    offsets = [-jitter, 0.0, jitter]
    return [
        Reading(new_id("V"), resident_id, kind, round(usual + offsets[d % 3], 2),
                now - timedelta(days=d))
        for d in range(1, days + 1)
    ]


def reading(resident_id: str, kind: str, value: float, time: datetime) -> Reading:
    return Reading(new_id("V"), resident_id, kind, value, time)


def hunch(resident_id: str, staff_id: str, sign: Sign, time: datetime) -> Hunch:
    return Hunch(new_id("H"), resident_id, staff_id, sign, time)
