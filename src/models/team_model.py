from pydantic import Field

from src.models.generic_model import GenericModel
from typing import List, Optional

from src.objects import IdObj


class TeamModel(GenericModel):
    profissionais_ids: Optional[List[IdObj]] = Field(default=[])
    medico_responsavel_id: Optional[IdObj] = Field(default=IdObj())
