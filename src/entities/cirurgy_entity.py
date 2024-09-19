from src.entities.generic_entity import GenericEntity
from src.models import CirurgyModel, TeamModel, RoomModel


class CirurgyEntity(GenericEntity[CirurgyModel]):
    def __init__(self, model: CirurgyModel):
        super().__init__(model=model)

    def set_team(self, team: GenericEntity[TeamModel]):
        team._model.cirurgias_ids.append(self._model.id)
        self._model.equipe_id = team._model.id

    def set_room(self, room: GenericEntity[RoomModel]):
        room._model.cirurgias_ids.append(self._model.id)
        self._model.sala_id = room._model.id
