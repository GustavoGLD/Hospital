from typing import Optional

from pydantic import BaseModel, Field


class IdObj(BaseModel):
    value: int = Field(default=0)
