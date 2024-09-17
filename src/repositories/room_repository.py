from src.entities import RoomEntity
from src.repositories.generic_repository import GenericRepository


class RoomRepository(GenericRepository[RoomEntity]):
    def __init__(self, entity_list: list[RoomEntity] = None):
        super().__init__(entity_list=entity_list)

