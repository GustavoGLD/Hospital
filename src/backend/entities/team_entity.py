from src.backend.entities.generic_entity import GenericEntity
from src.backend.models import TeamModel, ProfessionalModel


class TeamEntity(GenericEntity[TeamModel]):
    def __init__(self, model: TeamModel):
        super().__init__(model=model)

    def add_professional(self, professional: GenericEntity[ProfessionalModel]):
        professional._model.equipes_ids.append(self._model.id)
        self._model.profissionais_ids.append(professional._model.id)

    def set_responsible(self, professional: GenericEntity[ProfessionalModel]):
        if professional._model.id not in self._model.profissionais_ids:
            raise ValueError("The professional is not in the team")

        professional._model.equipes_responsaveis_ids.append(self._model.id)
        self._model.medico_responsavel_id = professional._model.id
