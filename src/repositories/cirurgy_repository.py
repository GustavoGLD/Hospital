from src.entities import CirurgyEntity
from src.repositories.generic_repository import GenericRepository


class CirurgyRepository(GenericRepository[CirurgyEntity]):
    def __init__(self, entity_list: list[CirurgyEntity] = None):
        super().__init__(entity_list=entity_list)
