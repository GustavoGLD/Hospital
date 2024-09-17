from typing import Optional

from pydantic import BaseModel, Field


class TimeObj(BaseModel):
    start: Optional[int] = Field(default=None)
