from typing import List, Optional

from pydantic import Field

from src.models.generic_model import GenericModel
from src.objects import TimeObj
from src.objects.id_obj import IdObj
from src.objects.punishment_obj import PunishmentObj


class CirurgyModel(GenericModel):
    punicao: PunishmentObj = Field(default=PunishmentObj())
    equipes_ids: list[IdObj] = Field(default=[])
    equipes_possiveis_ids: list[IdObj] = Field(default=[])
    tempo_inicio: Optional[TimeObj] = Field(default=TimeObj())
    sala_id: IdObj = Field(default=IdObj())
