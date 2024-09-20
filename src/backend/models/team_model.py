from pydantic import Field

from src.backend.models.generic_model import GenericModel
from typing import List, Optional

from src.backend.objects import IdObj


class TeamModel(GenericModel):
    profissionais_ids: Optional[List[IdObj]] = Field(default=[])
    medico_responsavel_id: Optional[IdObj] = Field(default=IdObj())
    cirurgias_ids: List[IdObj] = Field(default=[])