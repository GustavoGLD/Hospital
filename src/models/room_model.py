from pydantic import Field

from src.models.generic_model import GenericModel
from typing import List

from src.objects import IdObj


class RoomModel(GenericModel):
    cirurgias_ids: List[IdObj] = Field(default=[])
