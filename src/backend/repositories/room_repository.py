from typing import Optional

from src.backend.entities import RoomEntity
from src.backend.repositories.generic_repository import GenericRepository


class RoomRepository(GenericRepository[RoomEntity]):
    def __init__(self, entity_list: Optional[list[RoomEntity]] = None):
        super().__init__(entity_list=entity_list)

