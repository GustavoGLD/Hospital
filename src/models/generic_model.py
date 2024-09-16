from typing import Optional

from pydantic import BaseModel, Field


class GenericModel(BaseModel):
    id: Optional[int] = Field(default=None)
    nome: str
