from pydantic import Field

from src.models.generic_model import GenericModel
from typing import List

from src.objects import IdObj


class ProfessionalModel(GenericModel):
    equipes_ids: List[IdObj] = Field(default=[])
    equipes_responsaveis_ids: List[IdObj] = Field(default=[])
