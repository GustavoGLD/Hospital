from datetime import datetime

from sqlmodel import SQLModel, Field, Relationship


class Schedule(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}

    start_time: datetime
    fixed: bool = Field(default=False)

    surgery_id: int = Field(foreign_key="surgery.id", primary_key=True)
    room_id: int = Field(foreign_key="room.id")
    team_id: int = Field(foreign_key="team.id")

    surgery: "Surgery" = Relationship(back_populates="schedule")
    room: "Room" = Relationship(back_populates="schedules")
    team: "Team" = Relationship(back_populates="schedules")
