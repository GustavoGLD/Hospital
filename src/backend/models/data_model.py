import json
from pathlib import Path
from pydantic import BaseModel
from typing import List

from src.backend.models import CirurgyModel, RoomModel, TeamModel, ProfessionalModel


class DataModel(BaseModel):
    cirurgies: List[CirurgyModel]
    rooms: List[RoomModel]
    teams: List[TeamModel]
    professionals: List[ProfessionalModel]

    @classmethod
    def from_json(cls, file_path: str):
        with open(file_path, "r") as f:
            data = json.load(f)
        return cls.parse_obj(data)
