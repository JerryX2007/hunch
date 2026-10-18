from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


# Keep in sync with frontend/src/api/types.ts
class Resident(BaseModel):
    id: str
    display_name: str
    baseline_start: Optional[date] = None
    baseline_end: Optional[date] = None


class NewNote(BaseModel):
    note_text: str = Field(min_length=3, max_length=2000)
    author_role: str = Field(default="PSW", max_length=40)


class StatusUpdate(BaseModel):
    status: Literal["open", "reviewed", "needs_assessment", "dismissed"]
