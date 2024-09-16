from src.models.generic_model import GenericModel
from typing import List


class TeamModel(GenericModel):
    profissionais: List["ProfessionalModel"]
    medico_responsavel: "ProfessionalModel"


