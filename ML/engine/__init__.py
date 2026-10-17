"""Hunch scoring engine: pure Python, no database, no AI.

Everything in this package is a plain function over plain data, so it can be
tested in milliseconds and reused by the API, the simulator and the replay.
"""

from engine.models import Hunch, Reading, Resident, Sign, SIGN_LABELS
from engine.scoring import Assessment, score_resident, score_unit

__all__ = [
    "Assessment",
    "Hunch",
    "Reading",
    "Resident",
    "SIGN_LABELS",
    "Sign",
    "score_resident",
    "score_unit",
]
