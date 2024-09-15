from pydantic import BaseModel


class Room(BaseModel):
    id: int
    name: str
    cirurgies: str
