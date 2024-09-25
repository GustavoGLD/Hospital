from src.backend.entities.generic_entity import GenericEntity
from src.backend.models import ProfessionalModel, TeamModel


class ProfessionalEntity(GenericEntity[ProfessionalModel]):
    def __init__(self, model: ProfessionalModel):
        super().__init__(model=model)

    def add_team(self, team: GenericEntity[TeamModel]):
        team.model.profissionais_ids.append(self.model.id)
        self.model.equipe_id = team.model.id

    def set_responsible(self, team: GenericEntity[TeamModel]):
        team.model.medico_responsavel_id = self.model.id
        self.model.equipe_id = team.model.id
