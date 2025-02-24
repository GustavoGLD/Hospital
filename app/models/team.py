from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship

from app.models.surgery_possible_teams import SurgeryPossibleTeams
from app.models.schedule import Schedule
from app.models.professional import Professional


class Team(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str

    professionals: List["Professional"] = Relationship(back_populates="team")
    possible_surgeries: List["SurgeryPossibleTeams"] = Relationship(back_populates="team")
    schedules: List["Schedule"] = Relationship(back_populates="team")
