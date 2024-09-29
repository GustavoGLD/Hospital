from typing import Optional

from pydantic import BaseModel, Field

from src.backend.objects import IdObj
from src.backend.objects.name_obj import NameObj


class GenericModel(BaseModel):
    id: IdObj = Field(default=IdObj())
    name: NameObj = Field(default=NameObj())

    class Config:
        validate_assignment = True
