from src.backend.entities import ProfessionalEntity, TeamEntity
from src.backend.services.data_service import DataService
from src.frontend.controllers.generic_controller import GenericController
from src.frontend.views.team_view import TeamView
from src.utils.borg import BorgObj


class TeamController(GenericController):
    doctor_responsible_default = BorgObj("doctor_responsible_default", ProfessionalEntity)
    selected_team = BorgObj("selected_team", TeamEntity)

    def __init__(self, data: DataService):
        self.data = data
        self.view = TeamView()
        self.start()

    def start(self) -> None:
        self.view.view_selection(self.data.get_team_repository(), self.on_change_team)
        self.view.view_doctor_responsible(on_change=self.on_change_doctor_responsible,
                                          doctor=TeamController.doctor_responsible_default.value,
                                          team=TeamController.selected_team.value,
                                          prof_data=self.data.get_professional_repository(),
                                          selected_team=TeamController.selected_team)

    def on_change_team(self):
        pass

    def on_change_doctor_responsible(self):
        pass
