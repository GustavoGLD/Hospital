import copy
import json
import os
import sys
import time
from typing import Callable, TypedDict, Union, Any, Type, Generic, TypeVar

import jsbeautifier
import pandas as pd
import streamlit as st

from algoritmo import Equipe, Cirurgia, Sala, Otimizador, Mediador, Algoritmo, Export
from difflib import SequenceMatcher

def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

if __name__ == '__main__':
    st.set_page_config(
        page_title="Agenda Inteligente de Cirurgias",
        page_icon="🏥",
        layout="wide"
    )

from loguru import logger
from streamlit.delta_generator import DeltaGenerator

from gulogger import MyLogger, log_func
from gulogger.logcontext import LogC

if '__defined_loguru_config__' not in st.session_state and __name__ == '__main__':
    logger.add("loguru.log", level="TRACE", serialize=True)
    st.session_state['__defined_loguru_config__'] = True


if __name__ == '__main__':
    with st.expander("Configurações", expanded=False):
        dist, ord = st.tabs(["Distribuição", "Ordenação"])
        with dist:
            st.write("Distribuição das Cirurgias")

            st.slider("1. Número de gerações", min_value=1, max_value=50, value=5, step=1, key="dist_num_generations")
            st.slider("1. Solução por população", min_value=1, max_value=150, value=30, step=1, key="dist_sol_per_pop")
            st.slider("1. Número de pais para cruzamento", min_value=1, max_value=st.session_state["dist_sol_per_pop"], value=5, step=1, key="dist_num_parents_mating")

            with st.container(border=True):
                st.write("Configurações avançadas")
                st.selectbox("1. Tipo de cruzamento", ["uniform", "single_point", "two_points", "scattered"], key="dist_crossover_type")
                st.selectbox("1. Tipo de mutação", ["adaptive", "random"], key="dist_mutation_type")
                st.slider("1. Porcentagem de genes mutados", min_value=1, max_value=100, value=[5, 4], step=1, key="dist_mutation_percent_genes")
                st.selectbox("1. Tipo de seleção de pais", ["sss", "tournament", "rank"], key="dist_parent_selection_type")
                st.slider("1. Número de pais mantidos", min_value=1, max_value=st.session_state['dist_sol_per_pop'], value=5, step=1, key="dist_keep_parents")

        with ord:
            st.write("Ordenação das Cirurgias")

            st.checkbox("Ordem Simples", value=False, key="simple_order")

            st.slider("2. Número de gerações", min_value=1, max_value=500, value=10, step=1, disabled=st.session_state['simple_order'], key="ord_num_generations")
            st.slider("2. Solução por população", min_value=1, max_value=500, value=30, step=1, disabled=st.session_state['simple_order'], key="ord_sol_per_pop")
            st.slider("2. Número de pais para cruzamento", min_value=1, max_value=st.session_state['ord_sol_per_pop'], value=15, step=1, disabled=st.session_state['simple_order'], key="ord_num_parents_mating")

            with st.container(border=True):
                st.write("Configurações avançadas")
                st.selectbox("2. Tipo de cruzamento", ["uniform", "single_point", "two_points", "scattered"], disabled=st.session_state['simple_order'], key="ord_crossover_type")
                st.selectbox("2. Tipo de mutação", ["adaptive", "random"], disabled=st.session_state['simple_order'], key="ord_mutation_type")
                st.slider("2. Porcentagem de genes mutados", min_value=1, max_value=100, value=[5, 4], step=1, disabled=st.session_state['simple_order'], key="ord_mutation_percent_genes")
                st.selectbox("2. Tipo de seleção de pais", ["sss", "tournament", "rank"], disabled=st.session_state['simple_order'], key="ord_parent_selection_type")
                st.slider("2. Número de pais mantidos", min_value=1, max_value=st.session_state['ord_sol_per_pop'], value=5, step=1, disabled=st.session_state['simple_order'], key="ord_keep_parents")

    st.markdown('---')


class ProfessionalView:
    def __init__(self, cntr=st):
        cntr.write("Profissionais 👨‍⚕️")

        col1, col2 = cntr.columns(2, gap="small")

        with col1.container(border=True):
            self.professionals_selection = st.container()
            st.divider()
            st.write("Novo Profissional")

            col1_1, col1_2 = st.columns([2, 1])

            with col1_1:
                self.new_professional_name = st.container()
            with col1_2:
                self.add_professional_button = st.container()

            self.creation_warns = st.empty()

        with col2.container(border=True):
            self.professional_teams = st.container()

    @log_func
    @MyLogger.decorate_function(add_extra=["ProfessionalView"])
    def view_selection(self, professionals: list[str], on_change: Callable, logc: LogC, default=0) -> str:
        disable = True if not professionals else False
        if not disable:
            with self.professionals_selection:
                st.selectbox("Selecione um profissional", professionals, index=default, on_change=on_change, key="_selected_professional", disabled=disable, kwargs={"logc": logc})
        else:
            with self.professionals_selection:
                st.selectbox("Selecione um profissional", professionals, disabled=disable)
        return st.session_state['_selected_professional']

    @log_func
    @MyLogger.decorate_function(add_extra=["ProfessionalView"])
    def view_new_professional_name(self, logc: LogC) -> str:
        return self.new_professional_name.text_input("Nome do novo profissional", label_visibility="collapsed",
                                                     key="_new_professional_name")

    @log_func
    @MyLogger.decorate_function(add_extra=["ProfessionalView"])
    def view_add_professional_button(self, professional_view: "ProfessionalView", on_click: Callable, logc: LogC) -> bool:
        return self.add_professional_button.button(
            "Adicionar Profissional",
            on_click=on_click,
            use_container_width=True,
            kwargs={"professional_view": professional_view, "logc": logc}
        )

    @MyLogger.decorate_function(add_extra=["ProfessionalView"])
    def view_add_error_duplicate(self, logc: LogC):
        self.creation_warns.error("Nome de profissional já existente.")

    @MyLogger.decorate_function(add_extra=["ProfessionalView"])
    def view_professional_teams(self, all_teams: list[str], teams_default: list[str], on_change: Callable, logc: LogC):
        disable = True if not st.session_state['selected_professional'] else False
        #logger.debug(f"{teams_default=}")
        self.professional_teams.write("Equipes")
        self.professional_teams.multiselect(
            f"Selecione as equipes",
            options=all_teams,
            default=teams_default,
            key="_multiselected_teams",
            disabled=disable,
            on_change=on_change,
            kwargs={"logc": logc}
        )


if 'selected_team_index' not in st.session_state:
    st.session_state['selected_team_index'] = 0

if 'doctor_responsible_default' not in st.session_state:
    st.session_state['doctor_responsible_default'] = ""

if 'professional_id_counter' not in st.session_state:
    st.session_state['professional_id_counter'] = [0]

if 'teams_multiselector_default' not in st.session_state:
    st.session_state['teams_multiselector_default'] = []

if 'professionals' not in st.session_state:
    st.session_state['professionals'] = []

if 'team_id_counter' not in st.session_state:
    st.session_state['team_id_counter'] = [0]

if 'teams' not in st.session_state:
    st.session_state['teams'] = []


class ProfessionalModel:
    id_counter = st.session_state['professional_id_counter']
    professionals = st.session_state['professionals']

    def __init__(self, name, **kwargs):
        self.name = name
        self.id = ProfessionalModel.id_counter[0]
        self.teams = []
        self.responsible_teams = []

        if self.is_valid():
            ProfessionalModel.id_counter[0] += 1
            ProfessionalModel.professionals.append(self)
        else:
            raise ValueError(f"Professional {name} is not valid")

    @property
    def vteams(self) -> list["TeamModel"]:
        return self.teams

    @vteams.setter
    def vteams(self, teams: list["TeamModel"]):
        self.clear_teams()
        for team in teams:
            self.add_team(team)

    def add_team(self, team: "TeamModel"):
        if team not in self.teams:
            self.teams.append(team)
        if self not in team.vprofessionals:
            team.add_professional(self)

    def remove_team(self, team: "TeamModel"):
        if team in self.teams:
            self.teams.remove(team)
        if self in team.vprofessionals:
            team.remove_professional(self)

    def clear_teams(self):
        logger.debug(f"Clearing teams: {self.teams}")
        for team in copy.copy(self.vteams):
            self.remove_team(team)

    def is_valid(self) -> bool:
        if self.name == "":
            return False
        if self.name in [p.name for p in ProfessionalModel.professionals]:
            return False
        return True

    @staticmethod
    def get_names() -> list[str]:
        return [professional.name for professional in ProfessionalModel.professionals]

    @staticmethod
    def get_names_with_id() -> list[str]:
        return [f"{professional.name} - {professional.id}" for professional in ProfessionalModel.professionals]

    @staticmethod
    def get_by_id(_id: int) -> "ProfessionalModel":
        for professional in ProfessionalModel.professionals:
            if professional.id == _id:
                return professional
        raise ValueError(f"Professional '{_id}' not found: {ProfessionalModel.professionals}")

    @staticmethod
    def get_teams_remaining() -> list[str]:
        return [team.name for team in TeamModel.teams if team not in st.session_state['selected_professional'].vteams]

    def __repr__(self):
        return f"{self.id}"

    def get_dict(self) -> dict:
        return self.__dict__


if 'default_selected_professional_index' not in st.session_state:
    st.session_state['default_selected_professional_index'] = 0

if 'default_selected_team_index' not in st.session_state:
    st.session_state['default_selected_team_index'] = 0


class ProfessionalControl:
    def __init__(self, logc: LogC):
        self.professional_view = ProfessionalView(st.container(border=True))

        st.session_state['selected_professional'] = self.select_professional(logc=logc)
        logger.debug(st.session_state['selected_professional'])

        self.professional_view.view_professional_teams(
            all_teams=Data.get_teams_names(),
            teams_default=st.session_state['teams_multiselector_default'],
            on_change=self.on_change_teams,
            logc=logc
        )

    @MyLogger.decorate_function(add_extra=["ProfessionalControl"])
    def select_professional(self, logc: LogC = None) -> Union[ProfessionalModel, None]:
        self.professional_view.view_new_professional_name(logc=logc)
        self.professional_view.view_add_professional_button(
            on_click=self.on_click_add_professional,
            professional_view=self.professional_view,
            logc=logc
        )

        selected_name = self.professional_view.view_selection(
            ProfessionalModel.get_names_with_id(),
            on_change=self.on_change_professional,
            default=st.session_state['default_selected_professional_index'],
            logc=logc
        )

        if selected_name:
            return ProfessionalModel.get_by_id(int(selected_name.split(" - ")[1]))
        else:
            logger.opt(depth=0).warning(f'No professional named "{selected_name}"', **logc)
            return None

    @staticmethod
    @MyLogger.decorate_function(add_extra=["ProfessionalControl"])
    def on_click_add_professional(professional_view: ProfessionalView, logc: LogC):
        selected_name: str = st.session_state['_new_professional_name']
        assert selected_name is not None and isinstance(selected_name, str)

        if selected_name in ProfessionalModel.professionals:
            professional_view.view_add_error_duplicate(logc=logc)
        else:
            st.session_state['default_selected_professional_index'] = len(
                list(Data.get_dict()['professionals'].keys())
            )
            ProfessionalModel(name=selected_name)

    @staticmethod
    @MyLogger.decorate_function(add_extra=["ProfessionalControl"])
    def on_change_professional(logc: LogC):
        id = int(st.session_state['_selected_professional'].split(" - ")[1])
        st.session_state['selected_professional'] = ProfessionalModel.get_by_id(id)
        logger.debug(f"{st.session_state['selected_professional'].name=}", **logc)

        st.session_state['teams_multiselector_default'] = [
            team.name for team in st.session_state['selected_professional'].vteams
        ]

    @staticmethod
    @MyLogger.decorate_function(add_extra=["ProfessionalControl"])
    def on_change_teams(logc: LogC):
        teams_str: list[str] = st.session_state['_multiselected_teams']

        teams = [TeamModel.get_by_name(team) for team in teams_str]
        #logger.debug(f"{teams=}")
        st.session_state['selected_professional'].vteams = teams


class TeamView:
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

    @log_func
    @MyLogger.decorate_function(add_extra=["TeamsView"])
    def view_scheduling(self, scheduling: dict[str, list], logc: LogC):
        self.scheduling.write("Agendamento")
        self.scheduling.dataframe(scheduling, use_container_width=True)

    @log_func
    @MyLogger.decorate_function(add_extra=["TeamsView"])
    def view_selection(self, teams: list[str], on_change: Callable, logc: LogC, default=0) -> str:
        disable = True if not teams else False
        if not disable:
            with self.teams_selection:
                st.selectbox("Selecione uma equipe", teams, index=default, on_change=on_change, key="_selected_team", disabled=disable)
                return st.session_state['_selected_team']
        else:
            with self.teams_selection:
                st.selectbox("Selecione uma equipe", teams, disabled=disable)
                return ''

    @log_func
    @MyLogger.decorate_function(add_extra=["TeamsView"])
    def view_new_team_name(self, logc: LogC) -> str:
        return self.new_team_name.text_input("Nome da nova equipe", label_visibility="collapsed", key="_new_team_name")

    @log_func
    @MyLogger.decorate_function(add_extra=["TeamsView"])
    def view_add_team_button(self, team_view: "TeamView", on_click: Callable, logc: LogC) -> bool:
        return self.add_team_button.button("Adicionar Equipe", on_click=on_click, use_container_width=True,
                                           kwargs={"team_view": team_view, "logc": logc})

    @MyLogger.decorate_function(add_extra=["TeamsView"])
    def view_add_error_duplicate(self, logc: LogC):
        self.creation_warns.error("Nome de equipe já existente.")

    @MyLogger.decorate_function(add_extra=["TeamsView"])
    def view_doctor_responsible(self, on_change: Callable, doctor: "ProfessionalModel", team: "TeamModel", logc: LogC) -> None:
        disable = True if not st.session_state['selected_team'] else False
        options = [f"{prof.name} - {prof.id}" for prof in team] if team else []
        #logger.debug(f"{doctor.name if doctor else None}", **logc)
        if not disable:
            self.doctor_responsible.selectbox(
                "Médico responsável",
                options=options,
                index=options.index(f"{doctor.name} - {doctor.id}") if doctor else 0,
                key="_doctor_responsible",
                on_change=on_change,
                disabled=disable,
                kwargs={"logc": logc},
            )
        else:
            self.doctor_responsible.selectbox(
                "Médico responsável",
                options=options,
                disabled=True
            )

    @MyLogger.decorate_function(add_extra=["TeamsView"])
    def view_profissionals(self, selecteds: list[str], options: list, on_change: Callable, logc: LogC):
        disable = True if not st.session_state['selected_team'] else False
        self.profissionals.multiselect(
            "Selecione os profissionais",
            options,
            selecteds,
            key="_profissionals",
            disabled=disable,
            on_change=on_change,
            kwargs={"logc": logc},
        )


class TeamModel(Equipe):
    id_counter: list[int] = st.session_state['team_id_counter']
    teams: list["TeamModel"] = st.session_state['teams']

    def __init__(self, name, professionals: list[ProfessionalModel] = None, doctor_responsible=None, **kwargs):
        super().__init__(nome=name)
        self.name = name
        self.professionals = []
        self.doctor_responsible = None

        self.id = TeamModel.id_counter[0]
        TeamModel.id_counter[0] += 1

        if professionals:
            try:
                professionals = [int(professional) for professional in professionals]
            except Exception:
                pass

        if professionals:
            self.add_professionals(professionals)

        if doctor_responsible:
            try:
                doctor_responsible = int(doctor_responsible)
            except Exception:
                pass

        if doctor_responsible:
            self.set_doctor_responsible(doctor_responsible)
        TeamModel.teams.append(self)

    def __iter__(self):
        return iter(self.vprofessionals)

    @property
    def vprofessionals(self) -> list[ProfessionalModel]:
        return self.professionals

    @vprofessionals.setter
    def vprofessionals(self, professionals: Union[list[ProfessionalModel], list[int]]):
        self.clear_professionals()
        for professional in copy.copy(professionals):
            self.add_professional(professional)

    def clear_professionals(self):
        for professional in copy.copy(self.vprofessionals):
            self.remove_professional(professional)

    def add_professional(self, professional: Union[ProfessionalModel, int]):
        if isinstance(professional, int):
            professional = ProfessionalModel.professionals[professional]

        if professional not in self.vprofessionals:
            self.vprofessionals.append(professional)
            logger.debug(f"Adding {professional.name} to {self.name}")
        else:
            logger.debug(f"Professional {professional.name} already in {self.name}")
        if self not in professional.vteams:
            professional.add_team(self)

    def add_professionals(self, professionals: Union[list[ProfessionalModel], list[int]]):
        for professional in professionals:
            if isinstance(professional, int):
                professional = ProfessionalModel.professionals[professional]

            self.add_professional(professional)

    def remove_professional(self, professional: Union[ProfessionalModel, int]):
        if isinstance(professional, int):
            professional = ProfessionalModel.professionals[professional]

        if professional in self.vprofessionals:
            self.vprofessionals.remove(professional)
            logger.debug(f"Removing {professional.name} from {self.name}")
        else:
            logger.debug(f"Professional {professional.name} not in {self.name}")
        if self in professional.vteams:
            professional.remove_team(self)

    def set_doctor_responsible(self, professional: Union[ProfessionalModel, int]):
        if professional is None:
            return
        if isinstance(professional, int):
            professional = ProfessionalModel.professionals[professional]
        self.doctor_responsible = professional
        professional.responsible_teams.append(self)

    def get_professionals_names(self) -> list[str]:
        return [professional.name for professional in self.vprofessionals]

    def get_professionals_names_with_id(self) -> list[str]:
        return [f"{professional.name} - {professional.id}" for professional in self.vprofessionals]

    @staticmethod
    def get_names() -> list[str]:
        return [team.name for team in TeamModel.teams]

    @staticmethod
    def get_by_name(name: str) -> "TeamModel":
        for team in TeamModel.teams:
            if team.name == name:
                return team
        raise ValueError(f"Team {name} not found: {TeamModel.teams}")

    @staticmethod
    def get_by_id(_id: int) -> "TeamModel":
        for team in TeamModel.teams:
            if team.id == int(_id):
                return team
        raise ValueError(f"Team '{_id}' not found: {TeamModel.teams}")

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return str(self)

    def get_dict(self) -> dict:
        return {
            "name": self.name,
            "professionals": [professional.get_dict() for professional in self.vprofessionals],
            "doctor_responsible": self.doctor_responsible.get_dict() if self.doctor_responsible else None,
            "id": self.id
        }


class TeamControl:
    def __init__(self, logc: LogC = None):
        self.team_view = TeamView(st.container(border=True))

        st.session_state['selected_team']: TeamModel = self.select_team(logc=logc)
        logger.debug(st.session_state['selected_team'])

        selected_team: TeamModel = st.session_state['selected_team']

        self.team_view.view_profissionals(
            selected_team.get_professionals_names_with_id() if selected_team else [],
            ProfessionalModel.get_names_with_id(),
            on_change=self.on_change_professionals,
            logc=logc,
        )

        #logger.debug(f"{st.session_state['doctor_responsible_default']=}")
        self.team_view.view_doctor_responsible(
            on_change=self.on_change_responsible,
            doctor=st.session_state['doctor_responsible_default'],
            team=st.session_state['selected_team'],
            logc=logc
        )

        self.make_scheduling(logc=logc)

    @MyLogger.decorate_function(add_extra=["TeamsControl"])
    def make_scheduling(self, logc: LogC):
        team = st.session_state['selected_team']
        if not team:
            return
        scheduling = {"horarios": [], "sala": [], "cirurgia": [], "duracao": [], "paciente": []}
        for surgery in team.cirurgias:
            scheduling["horarios"].append(surgery.tempo_inicio)
            scheduling["sala"].append(surgery.sala)
            scheduling["cirurgia"].append(surgery.nome)
            scheduling["duracao"].append(surgery.duracao)
            scheduling["paciente"].append(surgery.patient_name)
        self.team_view.view_scheduling(scheduling, logc=logc)

    @staticmethod
    @MyLogger.decorate_function(add_extra=["TeamsControl"])
    def on_change_responsible(logc: LogC):
        id = int(st.session_state['_doctor_responsible'].split(" - ")[1])
        st.session_state['selected_team'].set_doctor_responsible(id)
        st.session_state['doctor_responsible_default'] = ProfessionalModel.get_by_id(id)
        #logger.debug(f"{st.session_state['doctor_responsible_default'].name=}", **logc)

    @staticmethod
    def on_change_team():
        st.session_state['doctor_responsible_default'] = \
            Data.get_team_by_name(st.session_state['_selected_team']).doctor_responsible

    @staticmethod
    @MyLogger.decorate_function(add_extra=["TeamsControl"])
    def on_change_professionals(logc: LogC):
        professionals_str: list[str] = st.session_state['_profissionals']
        professionals = [ProfessionalModel.get_by_id(int(professional.split(" - ")[1])) for professional in professionals_str]
        st.session_state['selected_team'].vprofessionals = professionals

    @staticmethod
    @MyLogger.decorate_function(add_extra=["TeamsControl"])
    def on_click_add_team(team_view: TeamView, logc: LogC):
        selected_name: str = st.session_state['_new_team_name']
        assert selected_name is not None and isinstance(selected_name, str)

        if selected_name in Data.get_teams_names():
            team_view.view_add_error_duplicate(logc=logc)
        else:
            st.session_state['default_selected_team_index'] = len(
                list(Data.get_dict()['teams'].keys())
            )
            TeamModel(name=selected_name, professionals=[], doctor_responsible=None)
            st.session_state['doctor_responsible_default'] = None

    @MyLogger.decorate_function(add_extra=["TeamsControl"])
    def select_team(self, logc: LogC = None) -> Union[TeamModel, None]:
        self.team_view.view_new_team_name(logc=logc)
        self.team_view.view_add_team_button(team_view=self.team_view, on_click=self.on_click_add_team, logc=logc)

        selected_name = self.team_view.view_selection(Data.get_teams_names(),
                                                      self.on_change_team,
                                                      default=st.session_state['default_selected_team_index'],
                                                      logc=logc)
        logger.debug(selected_name)
        if selected_name:
            return Data.get_team_by_name(selected_name)
        else:
            logger.opt(depth=0).warning(f'No team named "{selected_name}"', **logc)
            return None

    def load_teams(self):
        self.teams = pd.read_csv("teams.csv")

    def save_teams(self):
        self.teams.to_csv("teams.csv", index=False)


if 'room_id_counter' not in st.session_state:
    st.session_state['room_id_counter'] = [0]

if 'rooms' not in st.session_state:
    st.session_state['rooms'] = []

if 'selected_room' not in st.session_state:
    st.session_state['selected_room'] = None

if 'default_selected_room_index' not in st.session_state:
    st.session_state['default_selected_room_index'] = 0


class RoomView:
    def __init__(self, cntr=st):
        cntr.write("Salas 🏥")

        col1, col2 = cntr.columns(2, gap="small")

        with col1.container(border=True):
            self.rooms_selection = st.container()
            st.divider()
            st.write("Adicionar uma nova sala")

            col1_1, col1_2 = st.columns([2, 1])

            with col1_1:
                self.new_room_name = st.container()
            with col1_2:
                self.add_room_button = st.container()

            st.write("Adicionar várias novas salas")
            col2_1, col2_2 = st.columns([2, 1])
            with col2_1:
                self.new_rooms_count = st.container()
            with col2_2:
                self.add_all_romms_buttons = st.container()

            self.creation_warns = st.empty()

        with col2.container(border=True):
            self.room_list = st.container()

            with st.container(border=True):
                self.scheduling = st.container()

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_scheduling(self, scheduling: dict[str, list], logc: LogC):
        self.scheduling.write("Agendamento")
        self.scheduling.dataframe(scheduling, use_container_width=True)

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_selection(self, rooms: list[str], on_change: Callable, logc: LogC, default=0) -> str:
        disable = True if not rooms else False
        if not disable:
            with self.rooms_selection:
                st.selectbox("Selecione uma sala", rooms, index=default, on_change=on_change, key="_selected_room", disabled=disable, kwargs={"logc": logc})
                return st.session_state['_selected_room']
        else:
            with self.rooms_selection:
                st.selectbox("Selecione uma sala", rooms, disabled=disable)
                return ''

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_new_room_name(self, logc: LogC) -> str:
        return self.new_room_name.text_input("Nome da nova sala", label_visibility="collapsed", key="_new_room_name")

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_new_rooms_count(self, logc: LogC) -> int:
        return self.new_rooms_count.number_input("Quantidade de salas", key="_new_rooms_count", min_value=1, value=1,
                                                 label_visibility="collapsed")

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_add_room_button(self, room_view: "RoomView", on_click: Callable, logc: LogC) -> bool:
        return self.add_room_button.button("Adicionar Sala", on_click=on_click, use_container_width=True,
                                           kwargs={"room_view": room_view, "logc": logc})

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_add_all_rooms_button(self, room_view: "RoomView", on_click: Callable, logc: LogC) -> bool:
        return self.add_all_romms_buttons.button("Adicionar todas as salas", on_click=on_click, use_container_width=True,
                                           kwargs={"room_view": room_view, "logc": logc})

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_add_error_duplicate(self, logc: LogC):
        self.creation_warns.error("Nome de sala já existente.")

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_room_list(self, rooms: list[str], on_change: Callable, logc: LogC):
        self.room_list.multiselect(
            "Selecione as salas",
            rooms,
            key="_multiselected_rooms",
            on_change=on_change,
            kwargs={"logc": logc},
        )


class RoomModel(Sala):
    id_counter: list[int] = st.session_state['room_id_counter']
    rooms: list["RoomModel"] = st.session_state['rooms']

    def __init__(self, name, **kwargs):
        super().__init__(name)
        self.name = name
        self.id = RoomModel.id_counter[0]
        RoomModel.id_counter[0] += 1
        RoomModel.rooms.append(self)

    @staticmethod
    def get_names() -> list[str]:
        return [room.name for room in RoomModel.rooms]

    @staticmethod
    def get_by_name(name: str) -> "RoomModel":
        for room in RoomModel.rooms:
            if room.name == name:
                return room
        raise ValueError(f"Room {name} not found: {[r.name for r in RoomModel.rooms]}")

    @staticmethod
    def get_by_id(_id: int) -> "RoomModel":
        for room in RoomModel.rooms:
            if room.id == int(_id):
                return room
        raise ValueError(f"Room '{_id}' not found: {RoomModel.rooms}")

    def __str__(self):
        return f"{self.id}"

    def __repr__(self):
        return str(self)

    def get_dict(self) -> dict:
        return self.__dict__


class RoomControl:
    def __init__(self, logc: LogC = None):
        self.room_view = RoomView(st.container(border=True))

        st.session_state['selected_room']: RoomModel = self.select_room(logc=logc)
        logger.debug(st.session_state['selected_room'])

        selected_room: RoomModel = st.session_state['selected_room']

        self.room_view.view_new_rooms_count(logc=logc)
        self.room_view.view_add_all_rooms_button(room_view=self.room_view, on_click=self.on_click_add_all_rooms,
                                                 logc=logc)
        # self.room_view.view_room_list(Data.get_rooms_names(), self.on_change_rooms, logc=logc)

        self.make_scheduling(logc=logc)

    @MyLogger.decorate_function(add_extra=["RoomsControl"])
    def make_scheduling(self, logc: LogC):
        room = st.session_state['selected_room']
        if not room:
            return
        scheduling = {"horarios": [], "equipe": [], "cirurgia": [], "duracao": [], "paciente": []}
        for surgery in room.cirurgias:
            scheduling["horarios"].append(surgery.tempo_inicio)
            scheduling["equipe"].append(surgery.equipe.nome)
            scheduling["cirurgia"].append(surgery.nome)
            scheduling["duracao"].append(surgery.duracao)
            scheduling["paciente"].append(surgery.patient_name)
        self.room_view.view_scheduling(scheduling, logc=logc)

    @staticmethod
    @MyLogger.decorate_function(add_extra=["RoomsControl"])
    def on_click_add_all_rooms(room_view: RoomView, logc: LogC):
        for i in range(st.session_state['_new_rooms_count']):
            selected_name: str = f'Sala{len(Data.get_rooms_names())}'
            if selected_name in Data.get_rooms_names():
                selected_name = f'{selected_name}_{i}'
            RoomModel(name=selected_name)

    @staticmethod
    @MyLogger.decorate_function(add_extra=["RoomsControl"])
    def on_change_rooms(logc: LogC):
        rooms_str: str = st.session_state['_selected_room']
        st.session_state['selected_room'] = RoomModel.get_by_name(rooms_str)

    @staticmethod
    @MyLogger.decorate_function(add_extra=["RoomsControl"])
    def on_click_add_room(room_view: RoomView, logc: LogC):
        selected_name: str = st.session_state['_new_room_name']
        assert selected_name is not None and isinstance(selected_name, str)

        if selected_name in RoomModel.get_names():
            room_view.view_add_error_duplicate(logc=logc)
        else:
            st.session_state['default_selected_room_index'] = len(
                list(Data.get_dict()['rooms'].keys())
            )
            RoomModel(name=selected_name)

    @MyLogger.decorate_function(add_extra=["RoomsControl"])
    def select_room(self, logc: LogC = None) -> Union[RoomModel, None]:
        self.room_view.view_new_room_name(logc=logc)
        self.room_view.view_add_room_button(room_view=self.room_view, on_click=self.on_click_add_room, logc=logc)

        selected_name = self.room_view.view_selection(RoomModel.get_names(),
                                                      self.on_change_rooms,
                                                      default=st.session_state['default_selected_room_index'],
                                                      logc=logc)
        logger.debug(selected_name)
        if selected_name:
            return RoomModel.get_by_name(selected_name)
        else:
            logger.opt(depth=0).warning(f'No room named "{selected_name}"', **logc)
            return None


class CirurgyView:
    def __init__(self, cntr=st):
        cntr.write("Cirurgias 💉")

        self.col1, self.col2 = cntr.columns(2, gap="small")

    @MyLogger.decorate_function(add_extra=["CirurgyView"])
    def view_add_cirurgy(self, on_submit: Callable, logc: LogC):
        with self.col1.container():
            with st.form("Adicionar Cirurgia", clear_on_submit=True):
                cirurgy_name = st.data_editor({'cirurgy_name': ['']}, use_container_width=True, column_config={'cirurgy_name': st.column_config.TextColumn(label="Nome do Procedimento", required=True)})['cirurgy_name'][0]
                patient_name = st.data_editor({'patient_name': ['']}, use_container_width=True, column_config={'patient_name': st.column_config.TextColumn(label="Nome do Paciente", required=True)})['patient_name'][0]
                duration = st.data_editor({'duration': [0]}, use_container_width=True, column_config={'duration': st.column_config.NumberColumn(label="Duração (min)", required=True)})['duration'][0]
                priority = st.data_editor({'priority': [0]}, use_container_width=True, column_config={'priority': st.column_config.NumberColumn(label="Prioridade", required=True)})['priority'][0]

                possible_teams = [x.split(' - ')[-1] for x in st.multiselect("Equipes possíveis", Data.get_teams_names_with_id())]
                possible_rooms = st.multiselect("Salas possíveis", Data.get_rooms_names_with_id(), disabled=True)

                submit = st.form_submit_button("Adicionar Cirurgia", use_container_width=True)

                if submit and cirurgy_name and patient_name and duration and priority:
                    on_submit(
                        cirurgy_name=cirurgy_name, patient_name=patient_name, duration=duration,
                        priority=priority, possible_teams=possible_teams, possible_rooms=possible_rooms,
                        logc=logc
                    )

    @MyLogger.decorate_function(add_extra=["CirurgyView"])
    def view_cirurgy_list(self, cirurgies: list, logc: LogC):
        self.col2.write(f'{len(cirurgies)} cirurgias')
        self.col2.data_editor([cirurgy.get_dict() for cirurgy in cirurgies], use_container_width=True)


if 'selected_cirurgy' not in st.session_state:
    st.session_state['selected_cirurgy'] = None


if 'cirurgies' not in st.session_state:
    st.session_state['cirurgies'] = []

if 'cirurgy_id_counter' not in st.session_state:
    st.session_state['cirurgy_id_counter'] = [0]


class CirurgyModel(Cirurgia):
    id_counter: list[int] = st.session_state['cirurgy_id_counter']
    rooms: list["CirurgyModel"] = st.session_state['cirurgies']

    def __init__(self, cirurgy_name: str, patient_name: str, duration: int, priority: int,
                 possible_teams: list[str], possible_rooms: list[RoomModel], **kwargs):
        super().__init__(cirurgy_name, duration, priority, possible_teams)
        self._possible_teams = []

        self.cirurgy_name = cirurgy_name
        self.patient_name = patient_name
        self.duration = duration
        self.priority = priority
        self.possible_teams = possible_teams
        self.possible_rooms = possible_rooms

        self.id = CirurgyModel.id_counter[0]
        CirurgyModel.id_counter[0] += 1
        CirurgyModel.rooms.append(self)

    @property
    def possible_teams(self) -> list[TeamModel]:
        return self._possible_teams

    @possible_teams.setter
    def possible_teams(self, teams):
        for team in teams:
            Data.get_team_by_id(int(team)).possible_cirurgies.append(self)
        self._possible_teams = teams

    def get_dict(self) -> dict:
        return self.__dict__

    def __repr__(self):
        try:
            return f'Cirurgia({self.cirurgy_name})' #f'Cirurgia({self.cirurgy_name}, {self.equipe.nome}, {self.duration})'
        except (ValueError, TypeError):
            return f'Cirurgia({self.cirurgy_name}, {self.duration})'


class CirurgyControl:
    def __init__(self, logc: LogC = None):
        self.cirurgy_view = CirurgyView(st.container(border=True))
        self.cirurgy_view.view_add_cirurgy(on_submit=self.on_submit, logc=logc)

        self.cirurgy_view.view_cirurgy_list(CirurgyModel.rooms, logc=logc)

    @MyLogger.decorate_function(add_extra=["CirurgyControl"])
    def on_submit(self, **kwargs):
        CirurgyModel(**kwargs)


class Data:
    @staticmethod
    def load_json(filepath="data/data_teste_2.json"):
        if 'data_json' in st.session_state:
            filepath = f'data/{st.session_state["data_json"]}'
        datadict = jsbeautifier.beautify_file(filepath)
        null = None
        datadict = eval(datadict)

        Data.clear_data()

        for professional in datadict['professionals'].values():
            ProfessionalModel(**professional)
        for team in datadict['teams'].values():
            TeamModel(**team)
        for room in datadict['rooms'].values():
            RoomModel(**room)
        for cirurgy in datadict['cirurgies'].values():
            CirurgyModel(**cirurgy)

    @staticmethod
    def get_dict() -> dict:
        return {
            "professionals": {i: professional.get_dict() for i, professional in enumerate(ProfessionalModel.professionals)},
            "teams": {i: team.get_dict() for i, team in enumerate(TeamModel.teams)},
            "rooms": {i: room.get_dict() for i, room in enumerate(RoomModel.rooms)},
            "cirurgies": {i: cirurgy.get_dict() for i, cirurgy in enumerate(CirurgyModel.rooms)}
        }

    @staticmethod
    def to_json_file(file='data.json'):
        data = eval(str(Data.get_dict()))
        data_json = jsbeautifier.beautify(json.dumps(data))
        with open(file, "w") as file:
            file.write(data_json)

    @staticmethod
    def get_teams_names() -> list[str]:
        return [team.name for team in TeamModel.teams]

    @staticmethod
    def get_team_by_name(name: str) -> TeamModel:
        assert isinstance(name, str), f"{type(name)=}"
        for team in TeamModel.teams:
            if str(team.name) == name:
                return team
        raise ValueError(f'Team "{name}" not found. {TeamModel.teams=}')

    @staticmethod
    def get_professionals_names() -> list[str]:
        return [professional.name for professional in ProfessionalModel.professionals]

    @staticmethod
    def get_professional_by_name(name: str) -> ProfessionalModel:
        for professional in ProfessionalModel.professionals:
            if professional.name == name:
                return professional
        raise ValueError(f"Professional {name} not found")

    @staticmethod
    def get_rooms_names() -> list[str]:
        return [room.name for room in RoomModel.rooms]

    @staticmethod
    def get_room_by_name(name: str) -> RoomModel:
        for room in RoomModel.rooms:
            if room.name == name:
                return room
        raise ValueError(f"Room {name} not found")

    @staticmethod
    def get_room_by_id(_id: int) -> RoomModel:
        for room in RoomModel.rooms:
            if room.id == _id:
                return room
        raise ValueError(f"Room {_id} not found")

    @staticmethod
    def get_team_by_id(_id: int) -> TeamModel:
        assert isinstance(_id, int) or isinstance(_id, str), f"{_id=}"
        for team in TeamModel.teams:
            if team.id == int(_id):
                return team
        raise ValueError(f"Team {_id} not found")

    @staticmethod
    def get_professional_by_id(_id: int) -> ProfessionalModel:
        for professional in ProfessionalModel.professionals:
            if professional.id == _id:
                return professional
        raise ValueError(f"Professional {_id} not found")

    @staticmethod
    def get_professionals_names_with_id() -> list[str]:
        return [f"{professional.name} - {professional.id}" for professional in ProfessionalModel.professionals]

    @staticmethod
    def get_teams_names_with_id() -> list[str]:
        return [f"{team.name} - {team.id}" for team in TeamModel.teams]

    @staticmethod
    def get_rooms_names_with_id() -> list[str]:
        return [f"{room.name} - {room.id}" for room in RoomModel.rooms]

    @staticmethod
    def get_cirurgies() -> list[CirurgyModel]:
        print(CirurgyModel.rooms)
        return CirurgyModel.rooms

    @staticmethod
    def get_rooms() -> list[RoomModel]:
        return RoomModel.rooms

    @staticmethod
    def get_teams() -> list[TeamModel]:
        return TeamModel.teams

    @staticmethod
    def clear_data():
        st.session_state['professionals'].clear()
        st.session_state['teams'].clear()
        st.session_state['rooms'].clear()
        st.session_state['cirurgies'].clear()


class Exclusions:
    @staticmethod
    def validate(data: dict[list, Any]) -> bool:
        return True


if __name__ == '__main__':
    st.selectbox("Selecione um arquivo JSON da pasta 'data/' para carregar os dados",
                 os.listdir('data'), index=None, key='data_json', on_change=Data.load_json)

    with MyLogger(add_tags=['program']) as logc:
        tab_cirgs, tab_profs, tab_teams, tab_control = st.tabs(["💉 Cirurgias", "👨‍⚕️ Profissionais", "👥 Equipes", "🏥 Salas"])
        with tab_profs:
            professional_control = ProfessionalControl(logc=logc)
        with tab_teams:
            teams_control = TeamControl(logc=logc)
        with tab_control:
            rooms_control = RoomControl(logc=logc)
        with tab_cirgs:
            cirurgy_control = CirurgyControl(logc=logc)

        if 'counter_gen_container' not in st.session_state:
            st.session_state['counter_gen_container'] = st.empty()
            st.write("Counter_gen_container criado")

        if 'counter_gen' not in st.session_state:
            st.session_state['counter_gen'] = 0

        if 'agendado' not in st.session_state:
            st.session_state['agendado'] = False

        if st.button("Fazer agendamento!", use_container_width=True):
            st.session_state['agendado'] = True
            inicio = time.time()
            logger.critical(f"{Data.get_rooms()}, {Data.get_cirurgies()}")
            with st.spinner("Organizando salas..."):
                mediador = Mediador()
                mediador.equipes = Data.get_teams()
                mediador.salas = Data.get_rooms()
                otimizador = Otimizador(mediador, Data.get_cirurgies())
                solucao, punicao = otimizador.otimizar_punicao()

            st.write(f"Tempo de execução: {time.time() - inicio:.2f}s")
            logger.critical(f"Tempo de execução: {time.time() - inicio:.2f}s")
            st.write("Organização das salas:")

            st.write(f"{solucao=} {punicao=}")
            logger.success(f"{solucao=}")
            algoritmo = Algoritmo(mediador, Data.get_cirurgies())
            algoritmo.executar(solucao)
            st.dataframe(algoritmo.dados_tabela)


