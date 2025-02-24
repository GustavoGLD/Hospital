from datetime import datetime, timedelta
from typing import Optional

from pydantic import computed_field
from sqlmodel import SQLModel, Field


class EmptySchedule(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    room_id: int = Field(foreign_key="room.id")
    start_time: datetime
    duration: int

    @computed_field
    def end_time(self) -> datetime:
        return self.start_time + timedelta(minutes=self.duration)
