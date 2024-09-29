from typing import Optional

from src.backend.entities import TeamEntity
from src.backend.repositories.generic_repository import GenericRepository


class TeamRepository(GenericRepository[TeamEntity]):
    def __init__(self, entity_list: Optional[list[TeamEntity]] = None):
        super().__init__(entity_list=entity_list)
