from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Type, TypeVar, Any, Annotated, List, get_type_hints, get_origin, get_args, Callable, Optional

import numpy as np
import pandas as pd
import streamlit as st
from loguru import logger
from sqlalchemy import Table, MetaData, select, create_engine, Row, inspect
from sqlalchemy.orm import Session
from sqlalchemy.sql._typing import _TP
from sqlmodel import SQLModel
from streamlit.delta_generator import DeltaGenerator
from streamlit_pydantic_form import StaticForm, widget
from pydantic import BaseModel

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Surgery(Base):
    __tablename__ = 'surgery'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    duration = Column(Integer, nullable=False)
    priority = Column(Integer, nullable=False)
    patient_id = Column(Integer, ForeignKey('patient.id'), nullable=True)


class Room(Base):
    __tablename__ = 'room'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    schedules = relationship("Schedule", back_populates="room")


class Team(Base):
    __tablename__ = 'team'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    professionals = relationship("Professional", back_populates="team")
    possible_surgeries = relationship("SurgeryPossibleTeams", back_populates="team")
    schedules = relationship("Schedule", back_populates="team")


#from app.models import Room, Surgery, Team

# Conexão com o banco de dados SQLite em memória
DATABASE_URL = "sqlite:///database.db"

T = TypeVar("T", bound=SQLModel)


def get_table(model: Type[Table]) -> list[Table]:
    return Session(get_engine()).query(Table(model.__qualname__.lower(), Base.metadata)).all()


@st.cache_resource
def get_engine():
    engine = create_engine(DATABASE_URL, echo=True)
    try:
        Base.metadata.create_all(engine)
    except Exception:
        pass
    return engine


class ModelWidget(widget.WidgetBuilder):

    def __init__(self, model: Type[T], name: str):
        self.model = model
        self.name = name
        self.attr = {}

    def build(
            self,
            form: DeltaGenerator | None = None,
            *,
            randomize_key: bool = False,
            value: "PointWidget | None" = None,
            kwargs: dict[str, Any] | None = None,
    ) -> T:
        form = form.container(border=True) if form else st.container(border=True)

        if form.checkbox(f"Create a new {self.model.__name__}.{self.name}"):
            self.attr = self.render_form(form)
            return self.model(**self.attr)
        else:
            cache = get_table(self.model)
            if not cache:
                raise ValueError(f"No {self.model.__name__} found in the database")
            selected = form.selectbox(f"Select a {self.model.__name__}.{self.name}", cache)
            return self.model(**selected.dict())

    def render_form(self, form: DeltaGenerator) -> dict[str, Any]:
        hints = get_type_hints(self.model, include_extras=True)
        attrs = {}
        for attr, annotation in hints.items():
            if get_origin(annotation) is Annotated:
                tipo_base, *metadados = get_args(annotation)

                for meta in metadados:
                    if isinstance(meta, widget.WidgetBuilder):
                        attrs[str(attr)] = meta.build(form, randomize_key=True, value=None, kwargs=None)
        return attrs


class ListModelWidget(widget.WidgetBuilder):

    def __init__(self, model: Type[T], name: str, description: str = "", value: Optional[list[T]] = None):
        self.model = model
        self.name = name
        self.description = description
        self.attr = {}
        self.value = value

    def build(
            self,
            form: DeltaGenerator | None = None,
            *,
            randomize_key: bool = False,
            value: "PointWidget | None" = None,
            kwargs: dict[str, Any] | None = None,
    ) -> list[T]:
        form = form.container(border=True) if form else st.container(border=True)

        cache = get_table(self.model)
        if not cache:
            raise ValueError(f"No {self.model.__name__} found in the database")

        selecteds = form.multiselect(self.description, cache, key=f"{self.model.__name__}_{self.name}", default=self.value)
        logger.info(f"{self.model} {[selected._mapping for selected in selecteds]}")
        return [self.model(**selected._mapping) for selected in selecteds]


class RoomForm(BaseModel):
    name: Annotated[str, widget.TextInput("Nome")]


class TeamForm(BaseModel):
    name: Annotated[str, widget.TextInput("Nome")]


def make_surgery_form_model(values: Optional[dict] = None):
    values = values if values else defaultdict(lambda: None)
    logger.info(f"{values=}")

    class SurgeryForm(BaseModel):
        name: Annotated[str, widget.TextInput("Nome")] = values["name"] or ""
        duration: Annotated[int, widget.NumberInput("Duração", step=1)] = values["duration"] or 0
        priority: Annotated[int, widget.NumberInput("Prioridade", step=1)] = values["priority"] or 0
        #rooms: Annotated[list[Room], ListModelWidget(Room, "PossibleForm.rooms", "Salas adequadas", value=values["rooms"])]
        #teams: Annotated[list[Team], ListModelWidget(Room, "PossibleForm.teams", "Equipes adequadas", value=values["teams"])]

    return SurgeryForm


class SurgeryView:
    tab_name = "💉 Cirurgias"
    name = "cirurgia"

    def __init__(self, container=st.container(border=True)):
        self.cnt_dataframe = container.dataframe()
        self.cnt_add_btt, self.cnt_edit_btt, self.cnt_del_btt, self.cnt_updt_btt = container.columns(4)

    def render_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(self.cnt_dataframe.dataframe(
            df, selection_mode="single-row", on_select="rerun", use_container_width=True, hide_index=True,
            key=self.render_dataframe.__qualname__
        ))

    def render_add_btt(self, on_click: Callable) -> None:
        self.cnt_add_btt.button("➕ Adicionar", use_container_width=True, on_click=self._render_add_form,
                                kwargs={"on_click": on_click})

    @st.dialog(f"Adicionar {name}")
    def _render_add_form(self, on_click: Callable) -> None:
        with StaticForm(f"form_{self.name}_add", model=make_surgery_form_model()) as form:
            val = form.input_widgets()
            submitted = st.form_submit_button("Submit")
            if submitted:
                on_click(val)

    def render_edit_btt(self, on_click: Optional[Callable], values: dict, disabled: bool) -> None:
        on_click = on_click or (lambda x: x)
        self.cnt_edit_btt.button("✏️ Editar", use_container_width=True, on_click=self.render_edit_form,
                                 disabled=disabled, kwargs={"on_click": on_click, "values": values})

    @st.dialog(f"Editar {name}")
    def render_edit_form(self, on_click: Callable, values: dict) -> None:
        with StaticForm(f"form_{self.name}_edit", model=make_surgery_form_model(values)) as form:
            val = form.input_widgets()
            submitted = st.form_submit_button("Submit")
            if submitted:
                on_click(val)

    def render_del_btt(self, on_click: Callable, values: dict, disabled: bool) -> None:
        self.cnt_del_btt.button("❌ Excluir", use_container_width=True, on_click=self.render_del_form, disabled=disabled,
                                kwargs={"on_click": on_click, "values": values})

    @st.dialog(f"Excluir {name}")
    def render_del_form(self, on_click: Callable, values: dict) -> None:
        st.text(f"Deseja realmente excluir este item?\n'{values}'")
        col_left, col_right = st.columns(2)
        if col_left.button("Sim", use_container_width=True):
            on_click()
        elif col_right.button("Não", use_container_width=True):
            pass

    def render_updt_btt(self, on_click: Callable, disabled: bool) -> None:
        self.cnt_updt_btt.button("🔄 Atualizar", use_container_width=True, on_click=None, disabled=disabled)


class CrudType(ABC):
    def __init__(self, model: Type[Base], view: SurgeryView):
        self.selected_row: Optional[dict] = None
        self.view = view
        self.model = model

    @abstractmethod
    def render(self, selected_row: dict[str, Any] = None):
        raise NotImplementedError

    def add(self, val: BaseModel):
        with Session(get_engine()) as session:
            table = Table(Surgery.__name__, Base.metadata, autoload_with=get_engine())
            session.execute(table.insert().values(**val.dict()))
            session.commit()
            st.rerun()

    @abstractmethod
    def edit(self, val: BaseModel):
        raise NotImplementedError

    @abstractmethod
    def delete(self):
        raise NotImplementedError

    def update(self):
        st.rerun()


class CrudEntity(CrudType):
    def render(self, selected_row: dict[str, Any] = None):
        self.view.render_add_btt(self.add)
        self.view.render_edit_btt(self.edit, disabled=selected_row is None, values=selected_row)
        self.view.render_del_btt(self.delete, disabled=selected_row is None, values=selected_row)
        self.view.render_updt_btt(self.update, disabled=False)

    def edit(self, val: BaseModel):
        with Session(get_engine()) as session:
            table = Table(Surgery.__name__, Base.metadata, autoload_with=get_engine())
            session.execute(table.update().values(**val.dict()).where(table.c.id == self.selected_row["id"]))
            session.commit()
            st.rerun()

    def delete(self):
        with Session(get_engine()) as session:
            table = Table(Surgery.__name__, Base.metadata, autoload_with=get_engine())
            session.execute(table.delete().where(table.c.id == self.selected_row["id"]))
            session.commit()
            st.rerun()


class CrudObjectValue(CrudType):
    def render(self, selected_row: dict[str, Any] = None):
        self.view.render_add_btt(self.add)
        self.view.render_edit_btt(self.edit, disabled=True, values=selected_row)
        self.view.render_del_btt(self.delete, disabled=selected_row is None, values=selected_row)
        self.view.render_updt_btt(self.update, disabled=False)

    def get_primary_key(self) -> str:
        primary_keys = inspect(Surgery).primary_key
        assert primary_keys, f"Primary key not found in {Surgery.__name__}"
        assert len(primary_keys) == 1, f"Multiple primary keys found in {Surgery.__name__}"

        return primary_keys[0].name

    def delete(self):
        pk = self.get_primary_key()
        with Session(get_engine()) as session:
            table = Table(Surgery.__name__, Base.metadata, autoload_with=get_engine())
            session.execute(table.delete().where(table.c[pk] == self.selected_row[pk]))
            session.commit()
            st.rerun()


class SurgeryController:
    def __init__(self, container=st.container(border=True)):
        self.selected_row: Optional[dict] = None
        self.view = SurgeryView(container)
        self.crud = CrudEntity(self.view)

    def render(self):
        self.selected_row = self.getting_selected_row()
        self.view.render_add_btt(self.add)
        self.view.render_edit_btt(self.edit, disabled=self.selected_row is None, values=self.selected_row)
        self.view.render_del_btt(self.delete, disabled=self.selected_row is None, values=self.selected_row)
        self.view.render_updt_btt(self.update, disabled=False)

    def getting_selected_row(self) -> dict[str, Any]:
        surgeries = get_table(Surgery)
        df = pd.DataFrame(surgeries)
        event = self.view.render_dataframe(df)
        return df.iloc[event["selection"]["rows"][0]].to_dict() if event["selection"]["rows"] else None

    def get_primary_key(self) -> str:
        primary_keys = inspect(Surgery).primary_key
        assert primary_keys, f"Primary key not found in {Surgery.__name__}"
        assert len(primary_keys) == 1, f"Multiple primary keys found in {Surgery.__name__}"

        return primary_keys[0].name

    def add(self, val: BaseModel):
        with Session(get_engine()) as session:
            table = Table(Surgery.__name__, Base.metadata, autoload_with=get_engine())
            session.execute(table.insert().values(**val.dict()))
            session.commit()
            st.rerun()

    def edit(self, val: BaseModel):
        with Session(get_engine()) as session:
            table = Table(Surgery.__name__, Base.metadata, autoload_with=get_engine())
            session.execute(table.update().values(**val.dict()).where(table.c.id == self.selected_row["id"]))
            session.commit()
            st.rerun()

    def delete(self):
        with Session(get_engine()) as session:
            table = Table(Surgery.__name__, Base.metadata, autoload_with=get_engine())
            session.execute(table.delete().where(table.c.id == self.selected_row["id"]))
            session.commit()
            st.rerun()

    def update(self):
        st.rerun()

surg_tab, room_tab, team_tab = st.tabs(["💉 Cirurgias", "🏥 Salas", "👨‍⚕️ Equipes"])
SurgeryController(surg_tab).render()