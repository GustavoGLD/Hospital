from typing import Callable, Union

import streamlit as st

from src.models import CirurgyModel
from src.utils.borg import BorgObj
from src.utils.gulogger.log_func import log_func
from src.utils.gulogger.logcontext import MyLogger, LogC


class CirurgyView:
    _change_possible_rooms = BorgObj("_change_possible_rooms", list)
    _change_possible_teams = BorgObj("_change_possible_teams", list)
    _change_duration = BorgObj("_change_duration", int)
    _change_priority = BorgObj("_change_priority", int)
    _change_patient_name = BorgObj("_change_patient_name", str)
    _change_cirugy_name = BorgObj("_change_cirugy_name", str)
    _selected_cirurgy_name = BorgObj("_selected_cirurgy_name", str)


    def __init__(self, cntr=st):
        cntr.write("Cirurgias 💉")

        self.col1, self.col2 = cntr.columns(2, gap="small")

        with self.col1:
            self.list_cirurgies = st.container()
            self.add_cirurgy_button = st.container()
            self.select_cirurgy = st.container()

        with self.col2:
            self.edit_name = st.container()
            self.edit_patient = st.container()
            self.edit_duration = st.container()
            self.edit_priority = st.container()
            self.edit_possible_teams = st.container()
            self.edit_possible_rooms = st.container()

    def view_edit_possible_rooms(self, cirurgy: CirurgyModel, get_teams_names_with_id: list,
                                 rooms_ids_to_rooms_with_name_and_id: list, on_change: Callable, logc: LogC):
        if cirurgy:
            self.edit_possible_rooms.multiselect("Salas possíveis",
                                                 get_teams_names_with_id,
                                                 key=CirurgyView._change_possible_rooms.key,
                                                 default=rooms_ids_to_rooms_with_name_and_id,
                                                 on_change=on_change, kwargs={"logc": logc})
        else:
            self.edit_possible_rooms.multiselect("Salas possíveis", get_teams_names_with_id, disabled=True)

    def view_edit_possible_teams(self, cirurgy: CirurgyModel, get_teams_names_with_id: list,
                                 teams_ids_to_teams_with_name_and_id: list, on_change: Callable, logc: LogC):
        if cirurgy:
            self.edit_possible_teams.multiselect("Equipes possíveis",
                                                 get_teams_names_with_id,
                                                 key=CirurgyView._change_possible_teams.key,
                                                 default=teams_ids_to_teams_with_name_and_id,
                                                 on_change=on_change, kwargs={"logc": logc})
        else:
            self.edit_possible_teams.multiselect("Equipes possíveis", get_teams_names_with_id, disabled=True)

    def view_edit_duration(self, cirurgy: CirurgyModel, on_change: Callable, logc: LogC):
        if cirurgy:
            self.edit_duration.number_input("Duração (min)", key=CirurgyView._change_duration.key,
                                        value=cirurgy.duration, on_change=on_change, kwargs={"logc": logc})
        else:
            self.edit_duration.number_input("Duração (min)", disabled=True)

    def view_edit_priority(self, cirurgy: CirurgyModel, on_change: Callable, logc: LogC):
        if cirurgy:
            self.edit_priority.number_input("Prioridade", key=CirurgyView._change_priority.key,
                                        value=cirurgy.priority, on_change=on_change, kwargs={"logc": logc})
        else:
            self.edit_priority.number_input("Prioridade", disabled=True)

    def view_edit_patient(self, cirurgy: "CirurgyModel", on_change: Callable, logc: LogC):
        if cirurgy:
            self.edit_patient.text_input("Nome do paciente", key=CirurgyView._change_patient_name.key,
                                      value=cirurgy.patient_name, on_change=on_change, kwargs={"logc": logc})
        else:
            self.edit_patient.text_input("Nome do paciente", disabled=True)

    def view_edit_name(self, cirurgy: CirurgyModel, on_change: Callable, logc: LogC):
        if cirurgy:
            self.edit_name.text_input("Nome da cirurgia", key=CirurgyView._change_cirugy_name.key,
                                      value=cirurgy.cirurgy_name, on_change=on_change, kwargs={"logc": logc})
        else:
            self.edit_name.text_input("Nome da cirurgia", disabled=True)

    def view_selection(self, cirurgies: list[str], on_change: Callable, logc: LogC, default=None):
        if cirurgies:
            with self.select_cirurgy:
                self.select_cirurgy.selectbox("Selecione uma cirurgia", cirurgies, index=default, on_change=on_change,
                             key=CirurgyView._selected_cirurgy_name.key,
                             disabled=False, kwargs={"logc": logc})
        else:
            with self.select_cirurgy:
                self.select_cirurgy.selectbox("Selecione uma cirurgia", cirurgies, disabled=True)

    def view_list_cirurgies(self, cirurgies: dict[str, Union[str, int, list]]):
        column_config = {
            'cirurgy_name': st.column_config.TextColumn(label="Nome do Procedimento", required=True),
            'patient_name': st.column_config.TextColumn(label="Nome do Paciente", required=True),
            'duration': st.column_config.NumberColumn(label="Duração (min)", required=True),
            'priority': st.column_config.NumberColumn(label="Prioridade", required=True),
            'possible_teams': st.column_config.ListColumn(label="Equipes possíveis"),
            'possible_rooms': st.column_config.ListColumn(label="Salas possíveis"),
        }

        if cirurgies:
            self.list_cirurgies.dataframe(cirurgies, column_config=column_config)
        else:
            self.list_cirurgies.dataframe(cirurgies, column_config=column_config, use_container_width=True)

    @st.dialog("Adicionar Cirurgia", width="large")
    def view_add_cirurgy(self, get_teams_names_with_id: list, get_rooms_names_with_id: list, on_submit: Callable,
                         logc: LogC):
        cirurgy_name = st.data_editor({'cirurgy_name': ['']}, use_container_width=True, column_config={
            'cirurgy_name': st.column_config.TextColumn(label="Nome do Procedimento", required=True)})['cirurgy_name'][
            0]
        patient_name = st.data_editor({'patient_name': ['']}, use_container_width=True, column_config={
            'patient_name': st.column_config.TextColumn(label="Nome do Paciente", required=True)})['patient_name'][0]
        duration = st.data_editor({'duration': [0]}, use_container_width=True, column_config={
            'duration': st.column_config.NumberColumn(label="Duração (min)", required=True)})['duration'][0]
        priority = st.data_editor({'priority': [0]}, use_container_width=True, column_config={
            'priority': st.column_config.NumberColumn(label="Prioridade", required=True)})['priority'][0]

        possible_teams = [x.split(' - ')[-1] for x in
                          st.multiselect("Equipes possíveis", get_teams_names_with_id)]
        possible_rooms = st.multiselect("Salas possíveis", get_rooms_names_with_id, disabled=True)

        submit = st.button("Adicionar Cirurgia", use_container_width=True)

        if submit and cirurgy_name and patient_name and duration and priority:
            on_submit(
                cirurgy_name=cirurgy_name, patient_name=patient_name, duration=duration,
                priority=priority, possible_teams=possible_teams, possible_rooms=possible_rooms,
                logc=logc
            )
            st.rerun()

    @MyLogger.decorate_function(add_extra=["CirurgyView"])
    def view_cirurgy_list(self, cirurgies: list, logc: LogC):
        self.col2.write(f'{len(cirurgies)} cirurgias')
        self.col2.data_editor([cirurgy.get_dict() for cirurgy in cirurgies], use_container_width=True)