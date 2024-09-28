from typing import Optional

from pydantic import BaseModel, Field

from src.backend.objects.generic_obj import GenericObj


class IdObj(GenericObj):
    value: int = Field(default=0)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return self.__str__()
