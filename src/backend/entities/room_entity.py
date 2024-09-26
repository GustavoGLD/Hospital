from src.backend.entities.generic_entity import GenericEntity
from src.backend.models import RoomModel, CirurgyModel


class RoomEntity(GenericEntity[RoomModel]):
    def __init__(self, model: RoomModel):
        super().__init__(model=model)

    def add_cirurgy(self, cirurgy: GenericEntity[CirurgyModel]):
        cirurgy.model.room_id = self.model.id
        self.model.cirurgias_ids.append(cirurgy.model.id)
