from typing import Optional

from pydantic import BaseModel, Field


class TimeObj(BaseModel):
    start: Optional[int] = Field(default=None)

    def __str__(self):
        return str(self.start)

    def __repr__(self):
        return self.__str__()