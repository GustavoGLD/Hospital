from typing import List, Optional

from pydantic import Field, BaseModel

from src.backend.objects.generic_obj import GenericObj


class PunishmentObj(GenericObj):
    value: int = Field(default=0)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return self.__str__()
