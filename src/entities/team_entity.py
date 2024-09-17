from src.entities.generic_entity import GenericEntity
from src.models import TeamModel


class TeamEntity(GenericEntity[TeamModel]):
    def __init__(self, model: TeamModel):
        super().__init__(model=model)

