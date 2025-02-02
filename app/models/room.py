from typing import List, Annotated

from sqlmodel import SQLModel, Field, Relationship
from streamlit_pydantic_form import widget, StaticForm


class Room(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}

    id: int = Field(default=None, primary_key=True, index=True)
    name: Annotated[str, int]

    schedules: List["Schedule"] = Relationship(back_populates="room")
