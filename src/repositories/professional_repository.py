from src.entities import ProfessionalEntity
from src.repositories.generic_repository import GenericRepository


class ProfessionalRepository(GenericRepository[ProfessionalEntity]):
    def __init__(self, entity_list: list[ProfessionalEntity] = None):
        super().__init__(entity_list=entity_list)
