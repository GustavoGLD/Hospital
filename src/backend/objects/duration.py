from typing import Optional

from pydantic import BaseModel, Field

from src.backend.objects.generic_obj import GenericObj


class DurationObj(GenericObj):
    hours: Optional[int] = Field(default=None)
    minutes: Optional[int] = Field(default=None)
    seconds: Optional[int] = Field(default=None)

    def to_minutes(self):
        return self.hours * 60 + self.minutes  # + self.seconds / 60

    def __str__(self):
        return f"{self.hours}h {self.minutes}m {self.seconds}s"

    def __repr__(self):
        return self.__str__()
