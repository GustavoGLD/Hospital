#How to start
#1) define function: generate_datatable(). Make sure it returns your table as a 2d array (as shown in line 86-96).
#2) customize function edit_table() and delete_table().
#3) use line133 to instantiate a CRUDTable object, and use CRUDTable.put_crud_table() method to output it to your web app as in line 134.
from abc import ABC, abstractmethod
from typing import TypeVar, Type, Generic, Any

from sqlalchemy import text, inspect
from sqlmodel import SQLModel
from app.models import Surgery, Patient, Team, Room, Schedule
from pywebio_app import *
from pywebio.output import *
from pywebio.input import *
from pywebio.session import *
from pywebio import start_server
from functools import partial


class CRUDTable:
    def __init__(self, forms: "MyPywebioForms"):
        self.forms = forms
        self.model = forms.model
        self.datatable = self.gen_data_func()

    def put_crud_table(self):
        # the CRUD table without the header
        table = []

        for i, table_row in enumerate(self.datatable):
            table_row = [put_text(row_element[1]) for row_element in table_row] + [
                # use i - 1 here so that it counts after the header row.
                put_buttons(["◀️"], onclick=partial(self.handle_edit_delete, custom_func=self.edit_func, i=i)),
                put_buttons(["✖️"], onclick=partial(self.handle_edit_delete, custom_func=self.del_func, i=i))
            ]
            table.append(table_row)

        with use_scope("table_scope", clear=True):
            put_table(table,
                      header=list(self.datatable[0].model_dump().keys()) + ["Edit", "Delete"]
                      )

            put_row([
                put_button("Adicionar novo registro", onclick=partial(self.add_func, table=self.datatable)),
                None,
                put_button("Atualizar tabela", onclick=lambda: run_js('window.location.reload()')),
            ])

    def handle_edit_delete(self, dummy, custom_func, i):
        '''when edit/delete button is pressed, execute the custom edit/delete
        function as well as update CRUD table'''

        # originally had it in the custom functions in step5_filemanager.py,
        # but thought its probably best to have it within the crud_table class to
        # requery all the filepaths and refresh the crud_table

        if custom_func == self.edit_func:
            self.datatable = custom_func(self.datatable, i)
            # refresh table output
            self.put_crud_table()

        # if it's the delete function, ask for confirmation
        if custom_func == self.del_func:

            # melt the data (row becomes key, value)
            datatable_melt = list(zip(self.datatable[0], self.datatable[i]))
            popup(
                '⚠️ Are you sure you want to delete?',
                [
                    put_table(datatable_melt, header=["row", "data"]),
                    put_buttons(['confirm', 'cancel'],
                                onclick = lambda x: self.handle_confirm(i) if x == 'confirm' else close_popup())
                ]
            )

    def handle_confirm(self, i):
        ''' if confirm button pressed in deletion confirmation, delete, and also close popup'''
        self.datatable = self.del_func(self.datatable, i)
        close_popup()
        # refresh table output
        self.put_crud_table()

    def gen_data_func(self):
        with Session(get_engine()) as session:
            return session.query(self.model).all()

    def get_primary_key(self, model) -> str:
        """Retorna o nome da chave primária da tabela do modelo informado."""
        return inspect(model).primary_key[0].name  # Obtém dinamicamente a chave primária

    def edit_func(self, table, i):
        """Edita um registro no banco de dados baseado na entrada do usuário."""
        if i == 0:  # Evita editar o cabeçalho da tabela
            return table

        primary_key = self.get_primary_key(self.model)
        record = table[i]  # Obtém o registro da linha selecionada
        record_dict = record.model_dump()  # Converte para dicionário

        # Pergunta qual campo editar
        field_to_edit = select("Selecione o campo para editar:", record_dict.keys())
        if not field_to_edit:
            return table  # Se o usuário cancelar, não faz nada

        new_value = input(f'Novo valor para {field_to_edit}:', value=str(record_dict[field_to_edit]))

        # Atualiza o banco de dados
        with Session(get_engine()) as session:
            obj = session.get(self.model, record_dict[primary_key])
            setattr(obj, field_to_edit, new_value)  # Atualiza o campo
            session.commit()

        # Atualiza a tabela na interface
        table[i] = session.get(self.model, record_dict[primary_key])
        return table

    def del_func(self, table, i):
        table.pop(i)
        return table

    def add_func(self, table):
        """Adiciona um novo registro ao banco de dados."""
        new_record = self.forms.generate_pywebio_forms()

        with Session(get_engine()) as session:
            session.add(new_record)
            session.commit()

        table.append(new_record)
        return table


def get_rows(model: Type[SQLModel]) -> list[SQLModel]:
    with Session(get_engine()) as session:
        return session.query(model).all()


T = TypeVar("T", bound=Type[SQLModel])


class MyPywebioForms(ABC, Generic[T]):
    def __init__(self, model):
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


DATABASE_URL = "sqlite:///database.db"

from sqlmodel import SQLModel, Session, create_engine


def get_engine():
    engine = create_engine(DATABASE_URL, echo=True)
    try:
        SQLModel.metadata.create_all(engine)
    except Exception:
        pass
    return engine


def index():
    put_link('Go cirurgia', app='cirurgias')
    put_link('Go paciente', app='pacientes')
    put_link('Go equipe', app='equipes')
    put_link('Go sala', app='salas')
    put_link('Go agendamento', app='agendamentos')


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