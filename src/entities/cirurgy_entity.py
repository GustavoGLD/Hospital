from src.entities.generic_entity import GenericEntity
from src.models import CirurgyModel


class CirurgyEntity(GenericEntity[CirurgyModel]):
    def __init__(self, model: CirurgyModel):
        super().__init__(model=model)

