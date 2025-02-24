from typing import Optional, List

from sqlmodel import SQLModel, Field, Relationship


class Surgery(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str
    duration: int
    priority: int
    patient_id: Optional[int] = Field(default=None, foreign_key="patient.id")

    patient: Optional["Patient"] = Relationship()
    schedule: Optional["Schedule"] = Relationship(back_populates="surgery")
    possible_teams: List["SurgeryPossibleTeams"] = Relationship(back_populates="surgery")
