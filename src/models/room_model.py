from src.models.generic_model import GenericModel
from typing import List


class RoomModel(GenericModel):
    cirurgias: List['CirurgyModel']

