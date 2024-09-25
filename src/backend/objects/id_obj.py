from typing import Optional

from pydantic import BaseModel, Field


class IdObj(BaseModel):
    value: int = Field(default=0)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return self.__str__()
