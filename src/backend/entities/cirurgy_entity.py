from src.backend.entities.generic_entity import GenericEntity
from src.backend.models import CirurgyModel, TeamModel, RoomModel


class CirurgyEntity(GenericEntity[CirurgyModel]):
    def __init__(self, model: CirurgyModel):
        super().__init__(model=model)

    def set_team(self, team: GenericEntity[TeamModel]):
        team.model.cirurgias_ids.append(self.model.id)
        self.model.team_id = team.model.id

    def set_room(self, room: GenericEntity[RoomModel]):
        room.model.cirurgias_ids.append(self.model.id)
        self.model.room_id = room.model.id
