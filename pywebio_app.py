#How to start
#1) define function: generate_datatable(). Make sure it returns your table as a 2d array (as shown in line 86-96).
#2) customize function edit_table() and delete_table().
#3) use line133 to instantiate a CRUDTable object, and use CRUDTable.put_crud_table() method to output it to your web app as in line 134.
import contextlib
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import TypeVar, Type, Generic, Any

import pandas as pd
from loguru import logger
from sqlalchemy import text, inspect
from sqlmodel import SQLModel
from app.models import Surgery, Patient, Team, Room, Schedule
from app.services.cache.cache_in_dict import CacheInDict
from app.services.logic.schedule_builders.algorithm import Algorithm
from app.services.logic.schedule_builders.features.fixed_schedules import FixedSchedules
from app.services.logic.schedule_builders.features.room_limiter import RoomLimiter
from app.services.logic.schedule_builders.functions.apply_features import apply_features
from app.services.logic.schedule_optimizers.optimizer import Optimizer
from app.services.logic.schedule_optimizers.solver import Solver
from main import main, get_engine
from pywebio_app import *
from pywebio.output import *
from pywebio.input import *
from pywebio.session import *
from pywebio import start_server
from functools import partial

from tests import TestAlgorithmExecuteWithMoreData
from sqlmodel import select as slc


class FeaturesAlg:
    selecteds = []

    feature = {
        "Restringir salas": RoomLimiter,
        "Pré-agendamentos": FixedSchedules
    }

    @staticmethod
    def get_options():
        return [{"label": key, "value": key} for i, key in enumerate(FeaturesAlg.feature.keys())]

    @staticmethod
    def get_features() -> list:
        return [FeaturesAlg.feature[key] for key in FeaturesAlg.selecteds]


class CRUDTable:
    def __init__(self, forms: "MyPywebioForms"):
        self.forms = forms
        self.model = forms.model
        self.datatable: list

    def put_crud_table(self):
        self.datatable = self.gen_data_func()

        """Exibe a tabela CRUD atualizada na interface do PyWebIO."""
        table = []

        # Garante que a tabela tenha dados antes de acessar a chave
        if not self.datatable:
            put_text("Nenhum dado encontrado.")
            return

        model_columns = list(self.datatable[0].keys())  # Agora estamos lidando com dicionários
        print(f'{model_columns=}')
        print(f'{self.datatable=}')

        for i, row in enumerate(self.datatable):
            table_row = [put_text(str(row[col])) for col in model_columns] + [
                put_buttons(["✏️"], onclick=partial(self.handle_edit_delete, custom_func=self.edit_func, i=i)),
                put_buttons(["❌"], onclick=partial(self.handle_edit_delete, custom_func=self.del_func, i=i))
            ]
            table.append(table_row)

        with use_scope("table_scope", clear=True):
            put_table(table, header=model_columns + ["Editar", "Excluir"])

            put_row([
                put_button("Adicionar novo registro", onclick=partial(self.add_func, table=self.datatable)),
                None,
                put_button("Atualizar tabela", onclick=lambda: run_js('window.location.reload()')),
            ])

    def handle_edit_delete(self, dummy, custom_func, i):
        """Gerencia a edição ou exclusão de um registro."""
        if custom_func == self.edit_func:
            self.datatable = custom_func(self.datatable, i)
            self.put_crud_table()  # Atualiza a interface

        if custom_func == self.del_func:
            datatable_melt = list(self.datatable[i].items())
            popup(
                '⚠️ Tem certeza que deseja excluir?',
                [
                    put_table(datatable_melt, header=["Campo", "Valor"]),
                    put_buttons(['Confirmar', 'Cancelar'],
                                onclick=lambda x: self.handle_confirm(i) if x == 'Confirmar' else close_popup())
                ]
            )

    def handle_confirm(self, i):
        """Confirma e executa a exclusão de um registro."""
        self.datatable = self.del_func(self.datatable, i)
        close_popup()
        self.put_crud_table()  # Atualiza a tabela na interface

    def gen_data_func(self):
        """Busca os dados do banco de dados e os retorna como dicionários."""
        with Session(get_engine()) as session:
            r = [record.model_dump() for record in session.exec(slc(self.model)).all()]
            print(f'{r=}')
            return r

    def get_primary_key(self):
        """Retorna o nome da chave primária do modelo."""
        return inspect(self.model).primary_key[0].name

    def edit_func(self, table, i):
        """Edita um registro do banco de dados e atualiza a interface."""
        if i < 0 or i >= len(table):  # Validação do índice
            return table

        primary_key = self.get_primary_key()
        record = table[i]  # Agora é um dicionário
        record_id = record[primary_key]

        field_to_edit = select("Selecione o campo para editar:", list(record.keys()))
        if not field_to_edit:
            return table

        new_value = input(f'Novo valor para {field_to_edit}:', value=str(record[field_to_edit]))

        with Session(get_engine()) as session:
            obj = session.get(self.model, record_id)
            if obj:
                setattr(obj, field_to_edit, new_value)
                session.commit()

        # Atualiza o dicionário localmente para refletir a mudança na interface
        table[i][field_to_edit] = new_value
        return table

    def del_func(self, table, i):
        """Remove um registro do banco de dados e atualiza a interface."""
        primary_key = self.get_primary_key()
        record_id = table[i][primary_key]

        with Session(get_engine()) as session:
            obj = session.get(self.model, record_id)
            if obj:
                session.delete(obj)
                session.commit()

        table.pop(i)  # Remove da lista local
        self.put_crud_table()
        return table

    def add_func(self, table):
        """Adiciona um novo registro ao banco de dados e atualiza a tabela."""
        new_record = self.forms.generate_pywebio_forms()
        if not new_record:
            raise ValueError("Erro ao criar novo registro.")

        with Session(get_engine()) as session:
            session.add(new_record)
            session.commit()
            session.refresh(new_record)  # Garante que o ID seja atualizado

        table.append(new_record.model_dump())  # Adiciona o novo registro como dicionário
        self.put_crud_table()
        return table


def get_rows(model: Type[SQLModel]) -> list[SQLModel]:
    with Session(get_engine()) as session:
        return session.query(model).all()


T = TypeVar("T", bound=Type[SQLModel])


class MyPywebioForms(ABC, Generic[T]):
    def __init__(self, model: Type[SQLModel]):
        self.model = model

    @staticmethod
    @abstractmethod
    def generate_pywebio_forms() -> T:
        pass


class SurgeryForms(MyPywebioForms[Surgery]):
    def __init__(self):
        super().__init__(Surgery)

    @staticmethod
    def generate_pywebio_forms() -> object:
        return Surgery(
            name=input("Nome da cirurgia:", required=True),
            duration=input("Duração da cirurgia:", type=NUMBER, required=True),
            priority=input("Prioridade da cirurgia:", type=NUMBER, required=True),
            patient_id=select("Paciente:", options=[
                {"label": patient.name, "value": patient.id} for patient in get_rows(Patient)
            ], required=True)
        )


class PatientForms(MyPywebioForms[Patient]):
    def __init__(self):
        super().__init__(Patient)

    @staticmethod
    def generate_pywebio_forms() -> object:
        return Patient(
            name=input("Nome do paciente:", required=True)
        )


class TeamForms(MyPywebioForms[Team]):
    def __init__(self):
        super().__init__(Team)

    @staticmethod
    def generate_pywebio_forms() -> object:
        return Team(
            name=input("Nome da equipe:", required=True)
        )


class RoomForms(MyPywebioForms[Room]):
    def __init__(self):
        super().__init__(Room)

    @staticmethod
    def generate_pywebio_forms() -> object:
        return Room(
            name=input("Nome da sala:", required=True)
        )


class ScheduleForms(MyPywebioForms[Schedule]):
    def __init__(self):
        super().__init__(Schedule)

    @staticmethod
    def generate_pywebio_forms() -> object:
        return Schedule(
            start_time=input("Data da cirurgia:", type=DATETIME, required=True),
            fixed=radio("Tipo de cirurgia", options=[
                {"label": "Eletiva (agendada)", "value": True},
                {"label": "Emergencia/Urgencia (a agendar)", "value": False}
            ], required=True),
            surgery_id=select("Cirurgia:", options=[
                {"label": surgery.name, "value": surgery.id} for surgery in get_rows(Surgery)
            ], required=True),
            room_id=select("Sala:", options=[
                {"label": room.name, "value": room.id} for room in get_rows(Room)
            ], required=True),
            team_id=select("Equipe:", options=[
                {"label": team.name, "value": team.id} for team in get_rows(Team)
            ], required=True)
        )


from sqlmodel import SQLModel, Session, create_engine


def clear_all_tables(engine):
    with contextlib.closing(engine.connect()) as con:
        trans = con.begin()
        for table in reversed(SQLModel.metadata.sorted_tables):
            con.execute(table.delete())
        trans.commit()


def index():
    put_markdown('# Agendamento de Cirurgias - SISCOF')
    put_success('Bem-vindo ao sistema de agendamento de cirurgias!')
    put_text('Selecione uma tabela para configurar as dados:')
    put_grid([
        [
            put_button('Cirurgias', partial(go_app, 'cirurgias')),
            put_button('Pacientes', partial(go_app, 'pacientes')),
            put_button('Equipes', partial(go_app, 'equipes')),
            put_button('Salas', partial(go_app, 'salas')),
            put_button('Agendamentos', partial(go_app, 'agendamentos')),
        ]
    ])
    put_markdown('---')

    def execute_algorithm():
        with use_scope("teste", clear=True):
            put_warning("Executando...")

        with Session(get_engine()) as session:
            cache = CacheInDict(session=session)
            cache.load_all_data(session)

        algorithm_base = apply_features(Algorithm, *FeaturesAlg.get_features())
        optimizer = Optimizer(cache=cache, algorithm_base=algorithm_base)
        solution = optimizer.run()

        algorithm = Algorithm(optimizer.solver.mobile_surgeries, cache, datetime.now())
        algorithm.execute(solution)

        with use_scope("teste", clear=True):
            put_success("Concluído!")
            put_text("Resultado:")
            df = pd.DataFrame(algorithm.rooms_according_to_time)
            put_datatable(df.applymap(str).to_dict(orient='records'))

    def add_minimal_test():
        clear_all_tables(get_engine())

        teams = []
        patients = []
        surgeries = []
        surgery_possible_teams = []
        rooms = []

        TestAlgorithmExecuteWithMoreData.setting_up(teams, patients, surgeries, surgery_possible_teams, rooms)

        with Session(get_engine()) as session:
            session.add_all(teams)
            session.add_all(patients)
            session.add_all(surgeries)
            session.add_all(surgery_possible_teams)
            session.add_all(rooms)
            session.commit()

        run_js('window.location.reload()')

    def add_limiteroom_test():
        clear_all_tables(get_engine())

        teams = []
        patients = []
        surgeries = []
        surgery_possible_teams = []
        rooms = []

        TestAlgorithmExecuteWithMoreData.setting_up(teams, patients, surgeries, surgery_possible_teams, rooms)

        with Session(get_engine()) as session:
            session.add_all(teams)
            session.add_all(patients)
            session.add_all(surgeries)
            session.add_all(surgery_possible_teams)
            session.add_all(rooms)
            session.commit()

        run_js('window.location.reload()')

    def view_select_features():
        print(FeaturesAlg.selecteds)
        selecteds = select('`CTRL`+CLICK para selecionar múltiplas Features', options=FeaturesAlg.get_options(),
                           value=FeaturesAlg.selecteds, multiple=True)
        FeaturesAlg.selecteds = selecteds

    put_button('Selecionar features', onclick=view_select_features)
    put_button('Dados de teste - Algoritmo Mínimo', onclick=add_minimal_test)
    put_button('Executar algoritmo de agendamento', onclick=execute_algorithm)


tasks = {
    'index': index,
    'cirurgias': CRUDTable(SurgeryForms()).put_crud_table,
    'pacientes': CRUDTable(PatientForms()).put_crud_table,
    'equipes': CRUDTable(TeamForms()).put_crud_table,
    'salas': CRUDTable(RoomForms()).put_crud_table,
    'agendamentos': CRUDTable(ScheduleForms()).put_crud_table,
}


if __name__ == '__main__':
    start_server(tasks, debug=True, port=9999)
