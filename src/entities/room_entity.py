from src.entities.generic_entity import GenericEntity
from src.models import RoomModel


class RoomEntity(GenericEntity[RoomModel]):
    def __init__(self, model: RoomModel):
        super().__init__(model=model)

