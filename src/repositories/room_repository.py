from src.models import RoomModel
from src.repositories.generic_repository import GenericRepository


class RoomRepository(GenericRepository[RoomModel]):
    def __init__(self, models: list[RoomModel] = None):
        super().__init__(models=models)

