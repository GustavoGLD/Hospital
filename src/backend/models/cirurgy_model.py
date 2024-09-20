from typing import Optional

from pydantic import Field

from src.backend.models.generic_model import GenericModel
from src.backend.objects import TimeObj
from src.backend.objects.id_obj import IdObj
from src.backend.objects.punishment_obj import PunishmentObj


class CirurgyModel(GenericModel):
    punicao: PunishmentObj = Field(default=PunishmentObj())
    equipe_id: IdObj = Field(default=IdObj())
    equipes_possiveis_ids: list[IdObj] = Field(default=[])
    tempo_inicio: Optional[TimeObj] = Field(default=TimeObj())
    sala_id: IdObj = Field(default=IdObj())