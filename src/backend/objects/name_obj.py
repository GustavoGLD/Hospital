from typing import Optional

from pydantic import BaseModel, Field


class NameObj(BaseModel):
    value: str = Field(default="")

    def __str__(self):
        return self.value
