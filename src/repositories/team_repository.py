from src.entities import TeamEntity
from src.repositories.generic_repository import GenericRepository


class TeamRepository(GenericRepository[TeamEntity]):
    def __init__(self, entity_list: list[TeamEntity] = None):
        super().__init__(entity_list=entity_list)
