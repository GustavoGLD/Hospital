from typing import Callable

import streamlit as st

from src.models import RoomModel
from src.utils.borg import BorgObj
from src.utils.gulogger.logcontext import MyLogger, LogC


class RoomView:
    selected_room = BorgObj("selected_room", RoomModel)
    _selected_room = BorgObj("_selected_room", str)
    _new_room_name = BorgObj("_new_room_name", str)
    _new_rooms_count = BorgObj("_new_rooms_count", int)
    _multiselected_rooms = BorgObj("_multiselected_rooms", list)

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
    def view_selection(self, rooms: list[str], on_change: Callable, logc: LogC, default=None) -> str:
        disable = True if not rooms else False
        if not disable:
            with self.rooms_selection:
                st.selectbox("Selecione uma sala", rooms, index=default, on_change=on_change,
                             key=RoomView._selected_room.key, disabled=disable, kwargs={"logc": logc})
                return RoomView._selected_room.value
        else:
            with self.rooms_selection:
                st.selectbox("Selecione uma sala", rooms, disabled=disable)
                return ''

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_new_room_name(self, logc: LogC) -> str:
        return self.new_room_name.text_input("Nome da nova sala", label_visibility="collapsed",
                                             key=RoomView._new_room_name.key)

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_new_rooms_count(self, logc: LogC) -> int:
        return self.new_rooms_count.number_input("Quantidade de salas", key=RoomView._new_rooms_count.key, min_value=1, value=1,
                                                 label_visibility="collapsed")

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_add_room_button(self, room_view: "RoomView", on_click: Callable, logc: LogC) -> bool:
        return self.add_room_button.button("Adicionar Sala", on_click=on_click, use_container_width=True,
                                           kwargs={"room_view": room_view, "logc": logc})

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_add_all_rooms_button(self, room_view: "RoomView", on_click: Callable, logc: LogC) -> bool:
        return self.add_all_romms_buttons.button("Adicionar todas as salas", on_click=on_click,
                                                 use_container_width=True,
                                                 kwargs={"room_view": room_view, "logc": logc})

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_add_error_duplicate(self, logc: LogC):
        self.creation_warns.error("Nome de sala já existente.")

    @MyLogger.decorate_function(add_extra=["RoomsView"])
    def view_room_list(self, rooms: list[str], on_change: Callable, logc: LogC):
        self.room_list.multiselect(
            "Selecione as salas",
            rooms,
            key=RoomView._multiselected_rooms.key,
            on_change=on_change,
            kwargs={"logc": logc},
        )