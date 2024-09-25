from typing import Optional

from pydantic import BaseModel, Field


class DurationObj(BaseModel):
    hours: Optional[int] = Field(default=None)
    minutes: Optional[int] = Field(default=None)
    seconds: Optional[int] = Field(default=None)

    def __str__(self):
        return f"{self.hours}h {self.minutes}m {self.seconds}s"
