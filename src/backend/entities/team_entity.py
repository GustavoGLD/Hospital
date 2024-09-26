from src.backend.entities.generic_entity import GenericEntity
from src.backend.models import TeamModel, ProfessionalModel


class TeamEntity(GenericEntity[TeamModel]):
    def __init__(self, model: TeamModel):
        super().__init__(model=model)

    def add_professional(self, professional: GenericEntity[ProfessionalModel]):
        professional.model.teams_ids.append(self.model.id)
        self.model.professionals_ids.append(professional.model.id)

    def set_responsible(self, professional: GenericEntity[ProfessionalModel]):
        if professional.model.id not in self.model.professionals_ids:
            raise ValueError("The professional is not in the team")

        professional.model.responsibles_teams_ids.append(self.model.id)
        self.model.responsible_professional_id = professional.model.id
