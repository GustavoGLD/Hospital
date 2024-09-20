from src.backend.entities.generic_entity import GenericEntity
from src.backend.models import ProfessionalModel, TeamModel


class ProfessionalEntity(GenericEntity[ProfessionalModel]):
    def __init__(self, model: ProfessionalModel):
        super().__init__(model=model)

    def add_team(self, team: GenericEntity[TeamModel]):
        team._model.profissionais_ids.append(self._model.id)
        self._model.equipe_id = team._model.id

    def set_responsible(self, team: GenericEntity[TeamModel]):
        team._model.medico_responsavel_id = self._model.id
        self._model.equipe_id = team._model.id
