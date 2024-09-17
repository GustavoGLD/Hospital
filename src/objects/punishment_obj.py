from typing import List, Optional

from pydantic import Field, BaseModel


class PunishmentObj(BaseModel):
    value: int = Field(default=0)
