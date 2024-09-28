from typing import Optional

from pydantic import BaseModel, Field

from src.backend.objects.generic_obj import GenericObj


class TimeObj(GenericObj):
    start: Optional[int] = Field(default=None)

    def __str__(self):
        return str(self.start)

    def __repr__(self):
        return self.__str__()