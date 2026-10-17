from pydantic import BaseModel


# Keep in sync with frontend/src/api/types.ts
class Resident(BaseModel):
    id: str
    first_name: str
    last_name: str
    age: int
    room: str
