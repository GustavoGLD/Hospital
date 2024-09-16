from src.models.generic_model import GenericModel
from typing import List


class ProfessionalModel(GenericModel):
    times: List["TeamModel"]
    times_responsavel: List["TeamModel"]


