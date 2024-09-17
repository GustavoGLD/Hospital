from src.entities.generic_entity import GenericEntity
from src.models import ProfessionalModel


class ProfessionalEntity(GenericEntity[ProfessionalModel]):
    def __init__(self, model: ProfessionalModel):
        super().__init__(model=model)

