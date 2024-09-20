from pydantic import Field

from src.backend.models.generic_model import GenericModel
from typing import List

from src.backend.objects import IdObj


class RoomModel(GenericModel):
    cirurgias_ids: List[IdObj] = Field(default=[])
