from typing import Optional

from pydantic import BaseModel, Field

from src.backend.objects.generic_obj import GenericObj


class NameObj(GenericObj):
    value: str = Field(default="")

    def __str__(self):
        return self.value
