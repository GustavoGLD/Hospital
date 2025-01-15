from typing import List

from sqlmodel import SQLModel, Field, Relationship


class Room(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True, index=True)
    name: str

    schedules: List["Schedule"] = Relationship(back_populates="room")
