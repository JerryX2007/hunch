from datetime import date
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# Keep in sync with frontend/src/api/types.ts
class Resident(BaseModel):
    id: str
    display_name: str
    baseline_start: Optional[date] = None
    baseline_end: Optional[date] = None
    conditions: List[str] = []


class ResidentCreate(BaseModel):
    # Leave out to get the next free unit ID (e.g. 2W-023).
    id: Optional[str] = Field(default=None, min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    display_name: str = Field(min_length=1, max_length=120)
    baseline_start: Optional[date] = None
    baseline_end: Optional[date] = None
    first_note: Optional[str] = Field(default=None, max_length=2000)  # e.g. an admission note
    # Medical history, e.g. ["COPD", "Type 2 diabetes"] (context for nurses; never used to flag).
    conditions: Optional[List[Annotated[str, Field(min_length=1, max_length=120)]]] = Field(default=None, max_length=20)


class NewNote(BaseModel):
    note_text: str = Field(min_length=3, max_length=2000)
    author_role: str = Field(default="PSW", max_length=40)


class NewVitals(BaseModel):
    """One set of vitals; any measure may be left out, but not all of them."""
    temp_c: Optional[float] = Field(default=None, ge=30, le=43)
    spo2: Optional[int] = Field(default=None, ge=50, le=100)
    pulse: Optional[int] = Field(default=None, ge=25, le=220)
    resp_rate: Optional[int] = Field(default=None, ge=4, le=60)
    bp_systolic: Optional[int] = Field(default=None, ge=50, le=260)
    bp_diastolic: Optional[int] = Field(default=None, ge=20, le=160)

    @model_validator(mode="after")
    def something_measured(self):
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("Enter at least one measurement.")
        if (self.bp_systolic is None) != (self.bp_diastolic is None):
            raise ValueError("Enter both blood pressure numbers (e.g. 128 / 76).")
        return self


class StatusUpdate(BaseModel):
    status: Literal["open", "reviewed", "needs_assessment", "dismissed"]
