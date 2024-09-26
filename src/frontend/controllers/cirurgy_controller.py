from collections import defaultdict

from src.backend.entities import CirurgyEntity
from src.backend.services.data_service import DataService
from src.frontend.controllers.generic_controller import GenericController
from src.frontend.views.cirurgy_view import CirurgyView
from src.utils.borg import BorgObj


class CirurgyController(GenericController):
    selected_cirurgy = BorgObj("_selected_cirurgy", CirurgyEntity)
    add_cirurgy = BorgObj("_add_cirurgy", str)

    def __init__(self, data: DataService):
        self.data = data
        self.view = CirurgyView()
        self.start()

    def start(self) -> None:
        self.view.view_add_cirurgy_button(self.view.view_add_cirurgy, self.data.team_repository.get_names_and_ids(),
                                          self.data.room_repository.get_names_and_ids(), self.on_submit_cirurgy)
        self.view.view_selection(self.data.cirurgy_repository.get_names_and_ids(), on_change=self.on_selection)
        self.view.view_edit_name(CirurgyController.selected_cirurgy.value, on_change=self.on_change_name)
        self.view.view_edit_patient(CirurgyController.selected_cirurgy.value,
                                    on_change=self.on_change_patient_name)
        self.view.view_edit_duration(CirurgyController.selected_cirurgy.value, on_change=self.on_change_duration)
        self.view.view_edit_priority(CirurgyController.selected_cirurgy.value, on_change=self.on_change_priority)
        self.view.view_edit_possible_teams(CirurgyController.selected_cirurgy.value,
                                           self.data.team_repository.get_names_and_ids(),
                                           self.data.team_repository.get_id_by_names_with_ids(
                                               CirurgyController.selected_cirurgy.value.model.possible_teams_ids
                                           ) if CirurgyController.selected_cirurgy.value else [],
                                           on_change=self.on_change_possible_teams)
        self.view.view_edit_possible_rooms(CirurgyController.selected_cirurgy.value,
                                           self.data.room_repository.get_names_and_ids(),
                                           self.data.room_repository.get_id_by_names_with_ids(
                                                CirurgyController.selected_cirurgy.value.model.possible_rooms_ids
                                           ) if CirurgyController.selected_cirurgy.value else [],
                                           on_change=self.on_change_possible_rooms)

    def on_change_possible_rooms(self):
        possible_rooms = CirurgyView.change_possible_rooms.value
        CirurgyController.selected_cirurgy.value.model.possible_rooms = [
            room.split(' - ')[-1] for room in possible_rooms
        ]

    def on_change_possible_teams(self):
        possible_teams = CirurgyView.change_possible_teams.value
        CirurgyController.selected_cirurgy.value.model.possible_teams = [
            team.split(' - ')[-1] for team in possible_teams
        ]

    def on_change_duration(self):
        CirurgyController.selected_cirurgy.value.model.duration = CirurgyView.change_duration.value

    def on_change_priority(self):
        CirurgyController.selected_cirurgy.value.model.priority = CirurgyView.change_priority.value

    def on_change_patient_name(self):
        CirurgyController.selected_cirurgy.value.model.patient_name = CirurgyView.change_patient_name.value

    def on_change_name(self):
        CirurgyController.selected_cirurgy.value.model.name = CirurgyView.change_cirugy_name.value

    def on_selection(self):
        if CirurgyView.selected_cirurgy_name.is_declared():
            selected_name = CirurgyView.selected_cirurgy_name.value
            _id = selected_name.split(' - ')[-1]
            CirurgyController.selected_cirurgy.value = self.data.cirurgy_repository.get_by_id(_id)

    def make_list_view_dict(self):
        pass  # Implementar

    def on_submit_cirurgy(self, **kwargs):
        pass  # Implementar
            

