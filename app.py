import copy
import json
import sys
from typing import Callable, TypedDict, Union, Any, Type, Generic, TypeVar

import jsbeautifier
import pandas as pd
import streamlit as st
from loguru import logger
from streamlit.delta_generator import DeltaGenerator

from mylogger import MyLogger, log_func
from mylogger.logcontext import LogC

st.set_page_config(
    page_title="Agenda Inteligente de Cirurgias",
    page_icon="🏥",
    layout="wide"
)

if '__defined_loguru_config__' not in st.session_state:
    logger.add("loguru.log", level="TRACE", serialize=True)
    st.session_state['__defined_loguru_config__'] = True


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

    @log_func
    @MyLogger.decorate_function(add_extra=["TeamsView"])
    def view_selection(self, teams: list[str], on_change: Callable, logc: LogC, default=0) -> str:
        disable = True if not teams else False
        if not disable:
            with self.teams_selection:
                st.selectbox("Selecione uma equipe", teams, index=default, on_change=on_change, key="_selected_team", disabled=disable)
        else:
            with self.teams_selection:
                st.selectbox("Selecione uma equipe", teams, disabled=disable)
        return st.session_state['_selected_team']

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


class TeamModel:
    id_counter: list[int] = st.session_state['team_id_counter']
    teams: list["TeamModel"] = st.session_state['teams']

    def __init__(self, name, professionals: list[ProfessionalModel] = None, doctor_responsible=None, **kwargs):
        self.name = name
        self.professionals = []
        self.doctor_responsible = None

        self.id = TeamModel.id_counter[0]
        TeamModel.id_counter[0] += 1

        self.add_professionals(professionals) if professionals else None
        self.set_doctor_responsible(doctor_responsible) if doctor_responsible else None
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

    def set_doctor_responsible(self, professional: ProfessionalModel):
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
        return f"{self.id}"

    def __repr__(self):
        return str(self)

    def get_dict(self) -> dict:
        return self.__dict__


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


class Data:
    @staticmethod
    def load_json(file='data.json'):
        datadict = json.load(open(file))
        for professional in datadict['professionals'].values():
            ProfessionalModel(**professional)
        for team in datadict['teams'].values():
            TeamModel(**team)

    @staticmethod
    def get_dict() -> dict:
        return {
            "professionals": {i: professional.get_dict() for i, professional in enumerate(ProfessionalModel.professionals)},
            "teams": {i: team.get_dict() for i, team in enumerate(TeamModel.teams)}
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
        for team in TeamModel.teams:
            if team.name == name:
                return team
        raise ValueError(f"Team {name} not found")


if st.button("Load JSON"):
    Data.load_json()


with MyLogger(add_tags=['program']) as logc:
    tab_profs, tab_teams = st.tabs(["Profissionais 👨‍⚕️", "Equipes 👥"])
    with tab_profs:
        professional_control = ProfessionalControl(logc=logc)
    with tab_teams:
        teams_control = TeamControl(logc=logc)
    st.json(Data.get_dict())
