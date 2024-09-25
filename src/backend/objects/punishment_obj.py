from typing import List, Optional

from pydantic import Field, BaseModel


class PunishmentObj(BaseModel):
    value: int = Field(default=0)

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return self.__str__()
