from typing import Optional

from pydantic import BaseModel, Field

from src.objects import IdObj
from src.objects.name_obj import NameObj


class GenericModel(BaseModel):
    id: Optional[IdObj] = Field(default=IdObj())
    nome: NameObj = Field(default=NameObj())
