from pydantic import Field

from src.backend.models.generic_model import GenericModel
from typing import List

from src.backend.objects import IdObj


class ProfessionalModel(GenericModel):
    equipes_ids: List[IdObj] = Field(default=[])
    equipes_responsaveis_ids: List[IdObj] = Field(default=[])
