from typing import Optional

from src.backend.entities import CirurgyEntity
from src.backend.repositories.generic_repository import GenericRepository


class CirurgyRepository(GenericRepository[CirurgyEntity]):  # type: ignore
    def __init__(self, entity_list: Optional[list[CirurgyEntity]] = None):
        super().__init__(entity_list=entity_list)
