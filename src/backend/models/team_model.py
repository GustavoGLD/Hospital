from pydantic import Field

from src.backend.models.generic_model import GenericModel
from typing import List, Optional

from src.backend.objects import IdObj


class TeamModel(GenericModel):
    professionals_ids: Optional[List[IdObj]] = Field(default=[])
    responsible_professional_id: Optional[IdObj] = Field(default=IdObj())
    cirurgias_ids: List[IdObj] = Field(default=[])
