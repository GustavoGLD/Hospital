from pydantic import BaseModel
from typing import List


class TeamModel(BaseModel):
    id: int
    nome: str
    profissionais: List["ProfessionalModel"]
    medico_responsavel: "ProfessionalModel"


