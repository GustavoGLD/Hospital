from src.backend.entities.generic_entity import GenericEntity
from src.backend.models import TeamModel, ProfessionalModel


class TeamEntity(GenericEntity[TeamModel]):
    def __init__(self, model: TeamModel):
        super().__init__(model=model)

    def add_professional(self, professional: GenericEntity[ProfessionalModel]):
        professional.model.equipes_ids.append(self.model.id)
        self.model.profissionais_ids.append(professional.model.id)

    def set_responsible(self, professional: GenericEntity[ProfessionalModel]):
        if professional.model.id not in self.model.profissionais_ids:
            raise ValueError("The professional is not in the team")

        professional.model.equipes_responsaveis_ids.append(self.model.id)
        self.model.medico_responsavel_id = professional.model.id
