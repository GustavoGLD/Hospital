from pydantic import BaseModel
from typing import List


class ProfessionalModel(BaseModel):
    id: int
    nome: str
    times: List["TeamModel"]
    times_responsavel: List["TeamModel"]


