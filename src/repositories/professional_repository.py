from src.models import ProfessionalModel
from src.repositories.generic_repository import GenericRepository


class ProfessionalRepository(GenericRepository[ProfessionalModel]):
    def __init__(self, models: list[ProfessionalModel] = None):
        super().__init__(models=models)
