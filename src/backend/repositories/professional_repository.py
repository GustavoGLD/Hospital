from typing import Optional

from src.backend.entities import ProfessionalEntity
from src.backend.repositories.generic_repository import GenericRepository


class ProfessionalRepository(GenericRepository[ProfessionalEntity]):
    def __init__(self, entity_list: Optional[list[ProfessionalEntity]] = None):
        super().__init__(entity_list=entity_list)
