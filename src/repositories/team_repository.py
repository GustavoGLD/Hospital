from src.models import TeamModel
from src.repositories.generic_repository import GenericRepository


class TeamRepository(GenericRepository[TeamModel]):
    def __init__(self, models: list[TeamModel] = None):
        super().__init__(models=models)
