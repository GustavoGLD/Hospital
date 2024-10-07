from typing import Callable

import streamlit as st

from src.backend.entities import ProfessionalEntity, TeamEntity
from src.backend.repositories import TeamRepository, ProfessionalRepository
from src.backend.services.data_service import DataService
from src.utils.borg import BorgObj
from src.utils.gulogger.log_func import log_func
from src.utils.gulogger.logcontext import MyLogger, LogC


class TeamView:
    _selected_team = BorgObj("_selected_team", str)
    _new_team_name = BorgObj("_new_team_name", str)
    _profissionals = BorgObj("_profissionals", list)
    _doctor_responsible = BorgObj("_doctor_responsible", str)
    _add_team_button = BorgObj("add_team_button", bool)

    def __init__(self, cntr=st):
        cntr.write("Equipes 👥")

        col1, col2 = cntr.columns(2, gap="small")

        with col1.container(border=True):
            self.selecion_warns = st.empty()

            self.teams_selection = st.container()
            st.divider()
            st.write("Nova Equipe")

            col1_1, col1_2 = st.columns([2, 1])

            with col1_1:
                self.new_team_name = st.container()
            with col1_2:
                self.add_team_button = st.container()

            self.creation_warns = st.empty()

        with col2.container(border=True):
            self.doctor_responsible = st.container()
            self.profissionals = st.container()
            with st.container(border=True):
                self.scheduling = st.container()

    def view_scheduling(self, scheduling: dict[str, list]):
        self.scheduling.write("Agendamento")
        self.scheduling.dataframe(scheduling, use_container_width=True)

    def view_selection(self, teams: TeamRepository, on_change: Callable, default=None) -> str:
        disable = True if not teams.get_all() else False
        if not disable:
            with self.teams_selection:
                st.selectbox("Selecione uma equipe", teams.get_names_and_ids(), index=default, on_change=on_change,
                             key=TeamView._selected_team.key, disabled=disable)
                return TeamView._selected_team.value
        else:
            with self.teams_selection:
                st.selectbox("Selecione uma equipe", teams, disabled=disable)  # type: ignore
                return ''

    def view_new_team_name(self) -> str:
        return self.new_team_name.text_input("Nome da nova equipe", label_visibility="collapsed", key=TeamView._new_team_name.key)

    def view_add_team_button(self, team_view: "TeamView", on_click: Callable) -> bool:
        return self.add_team_button.button("Adicionar Equipe", on_click=on_click, use_container_width=True,
                                           kwargs={"team_view": team_view}, key=TeamView._add_team_button.key)

    def view_add_error_duplicate(self):
        self.creation_warns.error("Nome de equipe já existente.")

    def view_doctor_responsible(self, on_change: Callable, doctor: ProfessionalEntity, team: TeamEntity,
                                prof_data: ProfessionalRepository, selected_team: BorgObj) -> None:
        disable = True if not selected_team.is_declared() or not selected_team.value else False
        options = [prof_data.extract_names_with_ids([prof_data.get_by_id(prof.value)])[0] for prof in team.model.professionals_ids] if team else []
        # logger.debug(f"{doctor.name if doctor else None}", **logc)
        if not disable:
            self.doctor_responsible.selectbox(
                "Médico responsável",
                options=options,
                index=options.index(f"{doctor.model.name} - {doctor.model.id}") if doctor else 0,
                key=TeamView._doctor_responsible.key,
                on_change=on_change,
                disabled=disable,
                # kwargs={"logc": logc},
            )
        else:
            self.doctor_responsible.selectbox(
                "Médico responsável",
                options=options,
                disabled=True
            )

    def view_profissionals(self, selecteds: list[str], options: list, on_change: Callable):
        disable = True if not st.session_state['selected_team'] else False
        self.profissionals.multiselect(
            "Selecione os profissionais",
            options,
            selecteds,
            key=TeamView._profissionals.key,
            disabled=disable,
            on_change=on_change,
            # kwargs={"logc": logc},
        )