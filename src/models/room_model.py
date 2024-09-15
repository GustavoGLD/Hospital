from pydantic import BaseModel
from typing import List


class RoomModel(BaseModel):
    nome: str
    cirurgias: List['CirurgyModel']

