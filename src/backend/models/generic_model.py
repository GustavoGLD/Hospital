from typing import Optional

from pydantic import BaseModel, Field

from src.backend.objects import IdObj
from src.backend.objects.name_obj import NameObj


class GenericModel(BaseModel):
    id: Optional[IdObj] = Field(default=IdObj())
    name: NameObj = Field(default=NameObj())
