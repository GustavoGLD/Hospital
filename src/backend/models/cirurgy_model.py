from typing import Optional

from pydantic import Field

from src.backend.models.generic_model import GenericModel
from src.backend.models.patient_model import PatientModel
from src.backend.objects import TimeObj, DurationObj
from src.backend.objects.id_obj import IdObj
from src.backend.objects.punishment_obj import PunishmentObj


class CirurgyModel(GenericModel):

    penalty: PunishmentObj = Field()
    duration: DurationObj = Field()
    possible_teams_ids: list[IdObj] = Field()
    possible_rooms_ids: list[IdObj] = Field()

    team_id: IdObj = Field(default=IdObj())
    room_id: IdObj = Field(default=IdObj())
    time: TimeObj = Field(default=TimeObj())
    patient: PatientModel = Field(default=PatientModel())
