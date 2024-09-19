from src.entities.generic_entity import GenericEntity
from src.models import RoomModel, CirurgyModel


class RoomEntity(GenericEntity[RoomModel]):
    def __init__(self, model: RoomModel):
        super().__init__(model=model)

    def add_cirurgy(self, cirurgy: GenericEntity[CirurgyModel]):
        cirurgy._model.sala_id = self._model.id
        self._model.cirurgias_ids.append(cirurgy._model.id)
