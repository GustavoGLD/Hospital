from src.models import CirurgyModel
from src.repositories.generic_repository import GenericRepository


class CirurgyRepository(GenericRepository[CirurgyModel]):
    def __init__(self, models: list[CirurgyModel] = None):
        super().__init__(models=models)
