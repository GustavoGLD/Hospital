from typing import List, Optional

from src.models.generic_model import GenericModel


class CirurgyModel(GenericModel):
    punicao: Optional[str] = None
    equipe: "TeamModel"
    equipes_possiveis: List["TeamModel"]
    tempo_inicio: str
    sala: "RoomModel"


