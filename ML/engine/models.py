"""The data shapes the engine works with.

These are the "contract" between parts of the system: Gemini's extraction step
must produce Hunch records, the database stores them, and the rules read them.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from engine.shifts import shift_id


class Sign(str, Enum):
    """The fixed vocabulary of changes a PSW can report.

    Aligned with INTERACT Stop and Watch, plus two respiratory/GI signs that
    Ontario's outbreak definitions need. Gemini must map notes onto these codes.
    """

    EATING_LESS = "eating_less"
    NOT_DRINKING = "not_drinking"
    SLEEPIER = "sleepier"
    CONFUSED = "confused"
    UNSTEADY = "unsteady"
    IN_PAIN = "in_pain"
    WITHDRAWN = "withdrawn"
    COUGHING = "coughing"
    BREATHING_DIFFERENT = "breathing_different"
    VOMITING_DIARRHEA = "vomiting_diarrhea"


SIGN_LABELS = {
    Sign.EATING_LESS: "eating less",
    Sign.NOT_DRINKING: "not drinking",
    Sign.SLEEPIER: "sleepier",
    Sign.CONFUSED: "confused",
    Sign.UNSTEADY: "unsteady",
    Sign.IN_PAIN: "in pain",
    Sign.WITHDRAWN: "withdrawn",
    Sign.COUGHING: "coughing",
    Sign.BREATHING_DIFFERENT: "breathing different",
    Sign.VOMITING_DIARRHEA: "vomiting/diarrhea",
}


@dataclass(frozen=True)
class Resident:
    id: str
    name: str
    room: str
    table: str
    flu_shot_this_season: bool
    # Signs that are this resident's normal (e.g. a COPD cough). Reports of these
    # are not counted, so a chronic cough never raises a flag on its own.
    chronic_signs: frozenset[Sign] = field(default_factory=frozenset)


@dataclass(frozen=True)
class Hunch:
    """One confirmed observation: one staff member, one sign, one moment."""

    id: str
    resident_id: str
    staff_id: str
    sign: Sign
    time: datetime  # must be timezone-aware

    @property
    def shift(self) -> str:
        return shift_id(self.time)


@dataclass(frozen=True)
class Reading:
    """One charted measurement.

    kind is one of: "temp_c", "spo2", "fluids_24h" (total mL over the last day).
    """

    id: str
    resident_id: str
    kind: str
    value: float
    time: datetime  # must be timezone-aware
