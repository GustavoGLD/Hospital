from pydantic import BaseModel
from typing import List, Optional


class CirurgyModel(BaseModel):
    nome: str
    duracao: int
    punicao: Optional[str] = None
    equipe: "TeamModel"
    equipes_possiveis: List["TeamModel"]
    tempo_inicio: str
    sala: "RoomModel"


