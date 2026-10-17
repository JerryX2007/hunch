
from typing import Literal

from pydantic import BaseModel, model_validator


Category = Literal[
    "nutrition",
    "fluids",
    "energy",
    "mobility",
    "confusion",
    "pain",
    "sleep",
    "social",
    "toileting",
]

Subcategory = Literal["urine", "bowel"]
Change = Literal["increased", "decreased"]


class Observation(BaseModel):
    category: Category
    direction: Literal["worsening", "improving"]
    note: str
    event_date: str | None
    source_text: str

    # These fields apply only to toileting observations.
    subcategory: Subcategory | None = None
    change: Change | None = None

    @model_validator(mode="after")
    def validate_toileting_fields(self):
        if self.category == "toileting":
            if self.subcategory is None or self.change is None:
                raise ValueError(
                    "Toileting observations require subcategory and change."
                )
        elif self.subcategory is not None or self.change is not None:
            raise ValueError(
                "subcategory and change are only allowed for toileting."
            )

        return self


class ObservationResponse(BaseModel):
    observations: list[Observation]
