from fastapi import APIRouter, HTTPException

from ..schemas import Resident

router = APIRouter(prefix="/residents", tags=["residents"])

# Placeholder data until the database is wired up.
_RESIDENTS = [
    Resident(id="r1", first_name="Example", last_name="Resident", age=84, room="201"),
]


@router.get("", response_model=list[Resident])
def list_residents() -> list[Resident]:
    return _RESIDENTS


@router.get("/{resident_id}", response_model=Resident)
def get_resident(resident_id: str) -> Resident:
    for r in _RESIDENTS:
        if r.id == resident_id:
            return r
    raise HTTPException(status_code=404, detail="Resident not found")
