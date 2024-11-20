import os
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Optional, List, TypeVar, Type, Sequence, Tuple
from unittest.mock import MagicMock

import pandas as pd
from loguru import logger
from sqlmodel import Field, SQLModel, Relationship
from tabulate import tabulate

from moonlogger import MoonLogger
from dotenv import load_dotenv

load_dotenv()

T = TypeVar("T")
M = TypeVar("M", bound=SQLModel)


class LogConfig:
    algorithm_details: bool = False


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str

    professionals: List["Professional"] = Relationship(back_populates="team")
    possible_surgeries: List["SurgeryPossibleTeams"] = Relationship(back_populates="team")
    schedules: List["Schedule"] = Relationship(back_populates="team")


class Professional(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str
    team_id: Optional[int] = Field(default=None, foreign_key="team.id")

    team: Optional[Team] = Relationship(back_populates="professionals")


class Room(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str

    schedules: List["Schedule"] = Relationship(back_populates="room")


class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str


class Surgery(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str
    duration: int
    priority: int
    patient_id: Optional[int] = Field(default=None, foreign_key="patient.id")

    patient: Optional[Patient] = Relationship()
    schedule: Optional["Schedule"] = Relationship(back_populates="surgery")
    possible_teams: List["SurgeryPossibleTeams"] = Relationship(back_populates="surgery")


class Schedule(SQLModel, table=True):
    start_time: datetime

    surgery_id: int = Field(foreign_key="surgery.id", primary_key=True)
    room_id: int = Field(foreign_key="room.id")
    team_id: int = Field(foreign_key="team.id")

    surgery: Surgery = Relationship(back_populates="schedule")
    room: Room = Relationship(back_populates="schedules")
    team: Team = Relationship(back_populates="schedules")


class SurgeryPossibleTeams(SQLModel, table=True):
    __tablename__ = "surgery_possible_teams"
    surgery_id: int = Field(foreign_key="surgery.id", primary_key=True)
    team_id: int = Field(foreign_key="team.id", primary_key=True)

    surgery: Surgery = Relationship(back_populates="possible_teams")
    team: Team = Relationship(back_populates="possible_surgeries")


from datetime import datetime
from sqlmodel import Session, select


class InMemoryCache:
    def __init__(self, session: Optional[Session] = None):
        """Inicializa o cache e carrega os dados em memória de forma dinâmica."""
        if not hasattr(self, 'data'):
            self.data = {cls.__tablename__: [] for cls in self.get_table_classes()}
            if session:
                self.load_all_data(session)

    @staticmethod
    def get_table_classes() -> List[Type[SQLModel]]:
        """Retorna uma lista de classes de tabelas que devem ser carregadas no cache."""
        return [Team, Professional, Patient, Schedule, Surgery, SurgeryPossibleTeams, Room]

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def load_all_data(self, session: Session):
        """Carrega dinamicamente todas as tabelas definidas no cache."""
        for model in self.get_table_classes():
            table_name = model.__tablename__
            self.data[table_name] = self.load_table(session, model)

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_by_id(self, table: Type[M], _id: int) -> M:
        assert type(_id) == int, f"ID {_id} deve ser um inteiro."
        for row in self.get_table(table):
            if row.id == _id:
                return row
        raise ValueError(f"ID {_id} não encontrado na tabela '{table.__tablename__}':"
                         f"{[row.id for row in self.get_table(table)]}")

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_by_attribute(self, table: Type[M], attribute: str, value: any) -> list[M]:
        assert type(value) == int, f"Value {value} must be an integer."
        assert hasattr(table, attribute), f"Table '{table.__tablename__}' does not have attribute '{attribute}': {table.__dict__}"
        r = []
        for row in self.get_table(table):
            if getattr(row, attribute) == value:
                r.append(row)
        return r

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def load_table(self, session: Session, model: Type[T]) -> Sequence[Type[T]]:
        """Carrega uma tabela específica para a memória."""
        statement = select(model)
        return session.exec(statement).all()

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def refresh_cache(self, session: Session):
        """Atualiza o cache de todas as tabelas dinamicamente."""
        self.data.clear()
        self.load_all_data(session)

    def get_table(self, table: Type[M]) -> List[M]:
        """Retorna uma cópia dos dados da tabela especificada para evitar alterações no cache."""
        if table.__tablename__ not in self.data:
            raise ValueError(f"Tabela '{table.__tablename__}' não encontrada no cache.")
        return deepcopy(self.data.get(table.__tablename__, []))

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def is_team_busy(self, team_id: int, check_time: datetime) -> bool:
        """
        Verifica se uma equipe está ocupada no horário fornecido, utilizando dados do cache.

        Args:
            team_id (int): ID da equipe a ser verificada.
            check_time (datetime): Horário para verificar a disponibilidade.

        Returns:
            bool: True se a equipe estiver ocupada, False caso contrário.
        """
        # Filtra cirurgias associadas à equipe específica no cache
        surgery_team_links = [
            st for st in self.data['surgery_possible_teams']
            if st.team_id == team_id
        ]

        # Encontra os agendamentos associados às cirurgias da equipe
        schedules = [
            schedule for schedule in self.data['schedule']
            if any(st.surgery_id == schedule.surgery_id for st in surgery_team_links)
        ]
        if LogConfig.algorithm_details:
            logger.debug(f"Checking {schedules}")
        # Verifica se o horário fornecido coincide com algum agendamento
        for schedule in schedules:
            if LogConfig.algorithm_details:
                logger.debug(f"Checking schedule: {schedule} {schedule.start_time}")
            start_time = schedule.start_time
            end_time = start_time + timedelta(minutes=self.get_by_id(Surgery, schedule.surgery_id).duration)

            if start_time <= check_time < end_time:
                return True  # A equipe está ocupada

        return False  # A equipe está disponível

    def is_room_busy(self, room_id: int, check_time: datetime) -> bool:
        """
        Verifica se uma sala está ocupada no horário fornecido, utilizando dados do cache.

        Args:
            room_id (int): ID da sala a ser verificada.
            check_time (datetime): Horário para verificar a disponibilidade.

        Returns:
            bool: True se a sala estiver ocupada, False caso contrário.
        """
        # Filtra agendamentos associados à sala específica no cache
        schedules = self.get_by_attribute(Schedule, "room_id", room_id)
        if not schedules and LogConfig.algorithm_details:
            logger.warning(f"No schedules found for room {room_id}: {self.get_table(Schedule)}")

        for schedule in schedules:
            start_time = schedule.start_time
            end_time = start_time + timedelta(minutes=self.get_by_id(Surgery, schedule.surgery_id).duration)

            if start_time <= check_time < end_time:
                return True
        return False

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_available_teams(self, check_time: datetime) -> List[Team]:
        """
        Retorna todas as equipes disponíveis em um horário específico.

        Args:
            check_time (datetime): Horário para verificar a disponibilidade das equipes.

        Returns:
            List[Team]: Lista de equipes disponíveis no horário especificado.
        """
        available_teams = []

        # Itera sobre todas as equipes no cache
        for team in self.get_table(Team):
            # Se a equipe não está ocupada no horário especificado, adicione-a à lista de disponíveis
            if not self.is_team_busy(team.id, check_time):
                available_teams.append(team)

        return available_teams

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_next_surgery(self, surgeries: list[Surgery], team: Team) -> Surgery | SQLModel | None:
        """Retorna a próxima cirurgia a ser realizada por uma equipe específica."""
        possibles = self.data.get(SurgeryPossibleTeams.__tablename__)
        possibles = [psbl for psbl in possibles if psbl.team_id == team.id]

        if not possibles:
            logger.error(f"this team didn't have any corresponding surgery "
                         f"{team.name} (ID={team.id}): "
                         f"{self.data.get(SurgeryPossibleTeams.__tablename__)}")
            return None

        possibles = list(filter(lambda x: x.surgery_id in [surgery.id for surgery in surgeries], possibles))

        if not possibles:
            if LogConfig.algorithm_details:
                logger.error(f"no surgery found for team {team.name} (ID={team.id}) at this time")
            return None

        surgeries = [surgery for surgery in surgeries if surgery.id in [psbl.surgery_id for psbl in possibles]]
        surgeries = list(sorted(surgeries, key=lambda x: x.duration / (x.priority or 1)))
        return surgeries[0]

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def register_surgery(self, surgery: Surgery, team: Team, room: Room, start_time: datetime):
        """Registra uma cirurgia no cache."""
        if LogConfig.algorithm_details:
            logger.success(f"Registering surgery {surgery.name} for team {team.name} in room {room.name} at {start_time}")
        self.data['schedule'].append(
            Schedule(start_time=start_time, surgery_id=surgery.id, room_id=room.id, team_id=team.id)
        )

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_surgery_by_time_and_room(self, time: datetime, room: Room) -> Optional[Surgery]:
        """Retorna a cirurgia agendada para um horário e sala específicos."""
        self._validate_schedule_cache()
        surgery = self._find_surgery_by_time_and_room(time, room)
        if surgery:
            return surgery
        #occupied_intervals = self._get_room_schedule_intervals(room)
        #self._raise_schedule_error(time, room, occupied_intervals)

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _validate_schedule_cache(self):
        """Valida se os horários estão carregados no cache."""
        assert self.get_table(Schedule), "No schedules found in cache."

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _find_surgery_by_time_and_room(self, time: datetime, room: Room) -> Optional[Surgery]:
        """Procura por uma cirurgia agendada para o horário e sala específicos."""
        for schedule in self.get_table(Schedule):
            if schedule.room_id == room.id:
                final = schedule.start_time + timedelta(minutes=self.get_by_id(Surgery, schedule.surgery_id).duration)
                if schedule.start_time <= time < final:
                    return self.get_by_id(Surgery, schedule.surgery_id)
        return None

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _get_room_schedule_intervals(self, room: Room) -> list[tuple[datetime, datetime]]:
        """Gera a lista de intervalos ocupados em uma sala."""
        intervals = []
        for schedule in self.get_table(Schedule):
            if schedule.room_id == room.id:
                surgery = self.get_by_id(Surgery, schedule.surgery_id)
                intervals.append(
                    (
                        schedule.start_time,
                        schedule.start_time + timedelta(minutes=surgery.duration)
                    )
                )
        return intervals

    def _raise_schedule_error(self, time: datetime, room: Room, intervals: List[Tuple[datetime, datetime]]):
        """Lança uma exceção com informações detalhadas sobre os intervalos ocupados."""
        logger.critical(f"No surgery found for room {room.name} at {time}: {intervals}")
        #raise ValueError(f"No surgery found for room {room.name} at {time}: {intervals}")
        quit()

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_dict_surgeries_by_time(self, time: datetime) -> dict[str, str]:
        """Retorna um dicionário com todas as cirurgias agendadas para um horário específico."""
        _dict = {}
        for room in self.get_table(Room):
            surgery = self.get_surgery_by_time_and_room(time, room)
            if surgery:
                schedule = self.get_by_attribute(Schedule, "surgery_id", surgery.id)[0]
                _dict[room.name] = f"{self.get_by_id(Team, schedule.team_id).name} - {surgery.name} - {surgery.duration}min"
            else:
                _dict[room.name] = "None"
        return _dict

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_next_vacancies(self) -> list[tuple[Room, datetime]]:
        """Retorna um dicionário com as próximas vagas disponíveis em cada sala."""
        vacancies = []
        schedules = self.get_table(Schedule)
        rooms = self.get_table(Room)

        assert schedules, "No schedules found in cache."
        assert rooms, "No rooms found in cache."

        for room in rooms:
            local_schedules = [schedule for schedule in schedules if schedule.room_id == room.id]
            assert local_schedules, f"No schedules found for room {room.name}: {schedules}"
            last_schedule = max(local_schedules, key=lambda x: x.start_time)
            vacancies.append((
                room,
                last_schedule.start_time + timedelta(
                    minutes=self.get_by_id(Surgery, last_schedule.surgery_id).duration
                )
            ))

        return vacancies


class Algorithm:
    def __init__(self, cache: InMemoryCache = None):
        self.cache = cache
        self.surgeries: list[Surgery] = self.cache.get_table(Surgery)
        self.next_vacany = datetime(2024, 11, 1, 10, 0, 0)
        self._step = 0
        self.rooms_according_to_time = []

    @property
    def step(self):
        return self._step

    @step.setter
    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def step(self, value):
        self._step = value

    def print_table(self):
        df = pd.DataFrame(self.rooms_according_to_time)
        logger.debug("\n" + str(tabulate(df, headers="keys", tablefmt="grid")))

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_next_vacany(self) -> datetime:
        """Retorna a próxima vaga disponível."""
        self._validate_cache()  # Validações iniciais

        vacanies = self._get_sorted_vacancies()
        vacanies_dt = [vacany[1] for vacany in vacanies]

        # Ajusta valores duplicados, se necessário
        if self.next_vacany in vacanies_dt:
            vacanies_dt = self._adjust_duplicate_vacancies(vacanies_dt)

        return self._get_next_available_time(vacanies_dt)

    def _validate_cache(self):
        """Valida se o cache possui as tabelas necessárias."""
        if not self.cache.get_table(Schedule):
            raise ValueError("No schedules found in cache")
        if not self.cache.get_table(Room):
            raise ValueError("No rooms found in cache.")

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _get_sorted_vacancies(self) -> list:
        """Obtém e ordena as vagas disponíveis."""
        vacanies = self.cache.get_next_vacancies()
        if not vacanies:
            raise ValueError("No vacancies found.")
        return sorted(vacanies, key=lambda x: x[1])

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _adjust_duplicate_vacancies(self, vacanies_dt: list[datetime]) -> list[datetime]:
        """Ajusta valores duplicados na lista de tempos de vagas."""
        adjusted_vacanies = []
        previous_value = None

        for i, val in enumerate(vacanies_dt):
            if i > 0 and val == previous_value:
                val = adjusted_vacanies[-1] + timedelta(seconds=1)
            adjusted_vacanies.append(val)
            previous_value = val

        return adjusted_vacanies

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _get_next_available_time(self, vacanies_dt: list[datetime]) -> datetime:
        """Retorna o próximo horário disponível baseado na lista ajustada."""
        if LogConfig.algorithm_details:
            logger.debug(f"{self.next_vacany=}")
        if self.next_vacany in vacanies_dt:
            index = vacanies_dt.index(self.next_vacany)
            if index + 1 < len(vacanies_dt):
                return vacanies_dt[index + 1]

        return vacanies_dt[0] if vacanies_dt else self.next_vacany + timedelta(seconds=1)

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def execute(self, solution: list[int]):
        self.step = 0

        assert self.surgeries, "Sem cirurgias."
        assert self.cache.get_table(Team), "Sem equipes."
        assert self.cache.get_table(Room), "Sem salas."
        assert len(solution) == len(self.surgeries), "Solução inválida."

        while self.surgeries:
            available_teams = self.cache.get_available_teams(check_time=self.next_vacany)
            assert available_teams or self.step != 0, f"Sem equipes. {available_teams=}, {self.step=}"

            if available_teams:
                self.process_room(solution, available_teams)
                self.rooms_according_to_time.append({
                    "Tempo": self.next_vacany,
                    **self.cache.get_dict_surgeries_by_time(self.next_vacany)
                })
                if LogConfig.algorithm_details:
                    self.print_table()

            self.next_vacany = self.get_next_vacany()

        if LogConfig.algorithm_details:
            self.print_table()

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def process_room(self, solution: list[int], available_teams: List[Team]):
        assert self.surgeries, "Sem cirurgias."
        assert available_teams, "Sem equipes disponíveis."
        assert self.cache.get_table(Room), "Sem salas."

        for room in self.cache.get_table(Room):
            if not self.cache.is_room_busy(room.id, self.next_vacany) and self.surgeries and available_teams:
                self._process_room_with_teams(room, solution, available_teams)
            else:
                if LogConfig.algorithm_details:
                    logger.debug(f"Room {room.name} is busy at {self.next_vacany}")

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _process_room_with_teams(self, room: Room, solution: list[int], available_teams: List[Team]):
        try:
            team = available_teams[solution[self.step]]
        except IndexError as e:
            logger.error(f"IndexError: {solution=}, {self.step=}, {available_teams=} {self.surgeries=}")
            raise e

        surgery = self.cache.get_next_surgery(self.surgeries, team)

        if surgery:
            self._register_surgery_and_update(surgery, team, room, self.next_vacany)
        else:
            if not self._try_other_teams(room, available_teams):
                self._try_global_teams(room)

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _register_surgery_and_update(self, surgery: Surgery, team: Team, room: Room, start_time: datetime):
        self.cache.register_surgery(surgery, team, room, start_time)
        self.surgeries.remove(surgery)
        self.step += 1

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _try_other_teams(self, room: Room, available_teams: List[Team]) -> bool:
        for team in available_teams:
            surgery = self.cache.get_next_surgery(self.surgeries, team)
            if surgery:
                self._register_surgery_and_update(surgery, team, room, self.next_vacany)
                return True
        return False

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _try_global_teams(self, room: Room):
        for team in self.cache.get_table(Team):
            surgery = self.cache.get_next_surgery(self.surgeries, team)
            if surgery:
                schedules = self.cache.get_by_attribute(Schedule, "team_id", team.id)
                last_schedule = max(schedules, key=lambda x: x.start_time)
                start_time = last_schedule.start_time + timedelta(minutes=surgery.duration)
                _room = self.cache.get_by_id(Room, last_schedule.room_id)

                self._register_surgery_and_update(surgery, team, _room, start_time)
                return
        logger.error(f"No surgery found for any team. {self.surgeries=}")
        raise ValueError("No surgery found for any team.")


from sqlmodel import create_engine, Session
from datetime import datetime

# Configuração do banco
engine = create_engine(os.getenv("DB_URL"))

import unittest
from datetime import datetime, timedelta
from sqlmodel import SQLModel, create_engine, Session
from typing import List

# Inicializando o cache em memória
#cache = InMemoryCache()

# Classes para simulação dos dados
import unittest
from datetime import datetime, timedelta
from typing import List


import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session

def setup_test_session():
    engine = create_engine("sqlite:///:memory:")  # Banco de dados em memória
    SQLModel.metadata.create_all(engine)  # Cria as tabelas
    return Session(engine)


class TestInMemoryCache(unittest.TestCase):
    def setUp(self):
        """Configura os dados de teste no cache antes de cada teste usando uma sessão em memória"""
        self.session = setup_test_session()

        # Criar e adicionar equipes na sessão
        teams = [
            Team(id=1, name="Equipe A"),
            Team(id=2, name="Equipe B")
        ]
        self.session.add_all(teams)

        # Criar e adicionar pacientes na sessão
        patients = [
            Patient(id=1, name="Paciente 1"),
            Patient(id=2, name="Paciente 2")
        ]
        self.session.add_all(patients)

        # Criar e adicionar cirurgias na sessão
        surgeries = [
            Surgery(id=1, name="Cirurgia 1", duration=60, patient_id=1, priority=1),
            Surgery(id=2, name="Cirurgia 2", duration=120, patient_id=2, priority=2)
        ]
        self.session.add_all(surgeries)

        # Criar possíveis equipes para as cirurgias
        surgery_possible_teams = [
            SurgeryPossibleTeams(surgery_id=1, team_id=1),
            SurgeryPossibleTeams(surgery_id=2, team_id=2)
        ]
        self.session.add_all(surgery_possible_teams)

        rooms = [
            Room(id=1, name="Sala 1")
        ]
        self.session.add_all(rooms)

        # Commit para salvar todos os dados na sessão
        self.session.commit()

        self.cache = InMemoryCache(session=self.session)
        self.cache.load_all_data(self.session)

        #logger.debug(f"Teams: {self.cache.load_table(self.session, Team)}")
        #logger.debug(f"Schedule: {self.cache.load_table(self.session, Schedule)}")

        now = datetime.now()

        # Criar uma instância do algoritmo
        self.algorithm = Algorithm(self.cache)
        self.algorithm.surgeries = self.cache.get_table(Surgery)
        self.algorithm.next_vacany = now
        self.algorithm.step = 0
        assert self.algorithm.surgeries

    def test_is_team_busy(self):
        """Teste para verificar se uma equipe está ocupada em um horário específico"""
        now = datetime.now()

        schedules = [
            Schedule(surgery_id=1, start_time=now, room_id=1, team_id=1),
            Schedule(surgery_id=2, start_time=now + timedelta(hours=1), room_id=2, team_id=2)
        ]
        self.session.add_all(schedules)
        self.session.commit()
        self.cache.load_all_data(self.session)

        assert self.cache.get_table(Schedule)

        # Equipe 1 deve estar ocupada no horário do agendamento de Cirurgia 1
        self.assertTrue(self.cache.is_team_busy(1, now))

        # Equipe 1 não deve estar ocupada uma hora após o término de Cirurgia 1
        check_time = now + timedelta(hours=2)
        self.assertFalse(self.cache.is_team_busy(1, check_time))

        # Equipe 2 deve estar ocupada no horário do agendamento de Cirurgia 2
        self.assertTrue(self.cache.is_team_busy(2, now + timedelta(hours=1)))

    def test_get_available_teams(self):
        """Teste para verificar todas as equipes disponíveis em um horário específico"""
        now = datetime.now()

        schedules = [
            Schedule(surgery_id=1, start_time=now, room_id=1, team_id=1),
            Schedule(surgery_id=2, start_time=now + timedelta(hours=1), room_id=2, team_id=2)
        ]
        self.session.add_all(schedules)
        self.session.commit()
        self.cache.load_all_data(self.session)

        # Verifica equipes disponíveis durante o horário da Cirurgia 1
        available_teams = self.cache.get_available_teams(now)
        available_team_ids = [team.id for team in available_teams]
        self.assertIn(2, available_team_ids)
        self.assertNotIn(1, available_team_ids)

        # Verifica equipes disponíveis após o término de todas as cirurgias
        available_teams_after = self.cache.get_available_teams(now + timedelta(hours=3))
        available_team_ids_after = [team.id for team in available_teams_after]
        self.assertIn(1, available_team_ids_after)
        self.assertIn(2, available_team_ids_after)

    def test_process_room(self):
        """Teste para verificar o funcionamento do método process_room"""
        solution = [1, 0]  # Solução com índice para equipes disponíveis
        available_teams = self.cache.get_table(Team)

        # Limpar o cache de 'schedule' para simular um novo processo de agendamento
        self.cache.data['schedule'] = []

        # Executar o método process_room
        self.algorithm.process_room(solution, available_teams)

        # Verificar se a cirurgia foi registrada corretamente
        #self.assertEqual(len(self.cache.get_table(Surgery)), 1)  # Apenas uma cirurgia deve permanecer
        #self.assertEqual(self.algorithm.step, 1)  # O passo deve ter sido incrementado
        schedule = self.cache.get_table(Schedule)
        self.assertEqual(1, len(schedule))

        # Verificar se a cirurgia correta foi registrada em 'registered_surgeries'
        #registered_surgeries = self.cache.get_table(Schedule, [])
        #self.assertEqual(len(registered_surgeries), 1)  # Uma cirurgia deve ter sido registrada
        #self.assertEqual(registered_surgeries[0]['surgery'].id, 1)  # Cirurgia 1 deve ser registrada
        #self.assertEqual(registered_surgeries[0]['team'].id, 1)  # Equipe A deve ser a responsável
        #self.assertEqual(registered_surgeries[0]['room'].id, 1)  # Sala 1 deve ser a utilizada


class TestInMemoryCacheGetById(unittest.TestCase):
    def setUp(self):
        """Configura os dados de teste no cache antes de cada teste usando uma sessão em memória."""
        self.session = setup_test_session()

        # Criar e adicionar equipes na sessão
        teams = [
            Team(id=1, name="Equipe A"),
            Team(id=2, name="Equipe B")
        ]
        self.session.add_all(teams)
        self.session.commit()

        # Inicializa o cache com os dados carregados
        self.cache = InMemoryCache(session=self.session)

    def test_get_by_id_success(self):
        """Teste para verificar se o método retorna o objeto correto para um ID válido."""
        team = self.cache.get_by_id(Team, 1)
        self.assertIsNotNone(team)
        self.assertEqual(team.id, 1)
        self.assertEqual(team.name, "Equipe A")


class TestInMemoryCacheGetSurgeryByTimeAndRoom(unittest.TestCase):
    def setUp(self):
        # Configuração do banco de dados em memória
        self.engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        # Adicionando um paciente
        patient = Patient(id=1, name="John Doe")
        self.session.add(patient)

        # Adicionando equipes
        team_1 = Team(id=1, name="Team Alpha")
        team_2 = Team(id=2, name="Team Beta")
        self.session.add_all([team_1, team_2])

        # Adicionando profissionais
        professional_1 = Professional(id=1, name="Dr. Smith", team_id=1)
        professional_2 = Professional(id=2, name="Dr. Johnson", team_id=2)
        self.session.add_all([professional_1, professional_2])

        # Adicionando uma sala
        room = Room(id=1, name="Operating Room 1")
        self.session.add(room)

        # Adicionando cirurgias
        surgery_1 = Surgery(
            id=1,
            name="Appendectomy",
            duration=2,
            priority=1,
            patient_id=1,
        )
        surgery_2 = Surgery(
            id=2,
            name="Cholecystectomy",
            duration=3,
            priority=2,
            patient_id=1,
        )
        self.session.add_all([surgery_1, surgery_2])

        # Adicionando possíveis equipes para as cirurgias
        surgery_team_1 = SurgeryPossibleTeams(surgery_id=1, team_id=1)
        surgery_team_2 = SurgeryPossibleTeams(surgery_id=2, team_id=2)
        self.session.add_all([surgery_team_1, surgery_team_2])

        # Adicionando agendamentos
        schedule_1 = Schedule(
            start_time=datetime(2024, 11, 20, 8, 0),
            surgery_id=1,
            room_id=1,
            team_id=1,
        )
        schedule_2 = Schedule(
            start_time=datetime(2024, 11, 20, 10, 30),
            surgery_id=2,
            room_id=1,
            team_id=2,
        )
        self.session.add_all([schedule_1, schedule_2])
        self.session.commit()

    def test_get_surgery_by_time_and_room(self):
        # Inicializando o cache
        cache = InMemoryCache(self.session)

        # Buscando cirurgia pelo horário e sala
        result = cache.get_surgery_by_time_and_room(
            time=datetime(2024, 11, 20, 8, 0),
            room=cache.get_by_id(Room, 1)
        )

        # Validando o resultado
        assert result is not None
        assert result.id == 1
        assert result.name == "Appendectomy"


class TestGetNextVacancies(unittest.TestCase):
    def setUp(self):
        """Configura um ambiente inicial para os testes."""
        # Mock para o InMemoryCache
        self.cache = InMemoryCache()

        # Configura mock de dados
        self.room1 = Room(id=1, name="Sala 1")
        self.room2 = Room(id=2, name="Sala 2")

        self.schedule1 = Schedule(
            start_time=datetime(2024, 11, 17, 10, 0),
            surgery_id=1,
            room_id=1,
            team_id=1,
        )
        self.schedule2 = Schedule(
            start_time=datetime(2024, 11, 17, 11, 0),
            surgery_id=2,
            room_id=2,
            team_id=2,
        )
        self.surgery1 = Surgery(id=1, name="Cirurgia 1", duration=60, priority=1)
        self.surgery2 = Surgery(id=2, name="Cirurgia 2", duration=30, priority=2)

        # Adiciona dados no cache
        self.cache.data[Room.__tablename__] = [self.room1, self.room2]
        self.cache.data[Schedule.__tablename__] = [self.schedule1, self.schedule2]
        self.cache.data[Surgery.__tablename__] = [self.surgery1, self.surgery2]

    def test_next_vacancies_success(self):
        """Testa se as próximas vagas são retornadas corretamente."""
        vacancies = self.cache.get_next_vacancies()

        expected_vacancies = [
            (self.room1, datetime(2024, 11, 17, 11, 0)),
            (self.room2, datetime(2024, 11, 17, 11, 30)),
        ]
        self.assertEqual(vacancies, expected_vacancies)


class TestNextVacany(unittest.TestCase):

    def setUp(self):
        """Configura o ambiente para os testes."""
        # Mock do InMemoryCache
        self.cache = InMemoryCache()

        # Configura dados no cache
        self.room1 = Room(id=1, name="Sala 1")
        self.room2 = Room(id=2, name="Sala 2")

        self.schedule1 = Schedule(
            start_time=datetime(2024, 11, 17, 10, 0),
            surgery_id=1,
            room_id=1,
            team_id=1,
        )
        self.schedule2 = Schedule(
            start_time=datetime(2024, 11, 17, 11, 0),
            surgery_id=2,
            room_id=2,
            team_id=2,
        )
        self.surgery1 = Surgery(id=1, name="Cirurgia 1", duration=60, priority=1)
        self.surgery2 = Surgery(id=2, name="Cirurgia 2", duration=30, priority=2)

        # Adiciona dados ao cache
        self.cache.data[Room.__tablename__] = [self.room1, self.room2]
        self.cache.data[Schedule.__tablename__] = [self.schedule1, self.schedule2]
        self.cache.data[Surgery.__tablename__] = [self.surgery1, self.surgery2]

        # Instancia a classe Algorithm com o cache
        self.algorithm = Algorithm(self.cache)

    def test_get_next_vacany_basic(self):
        """Testa se o método get_next_vacany retorna a próxima vaga corretamente."""
        expected = datetime(2024, 11, 17, 11, 0)
        next_vacany = self.algorithm.get_next_vacany()
        self.assertEqual(next_vacany, expected)

    def test_get_next_vacany_with_adjustment(self):
        """Testa se o método ajusta corretamente as vagas quando há duplicatas."""
        # Adiciona uma vaga no mesmo horário
        self.cache.data[Schedule.__tablename__].append(
            Schedule(
                start_time=datetime(2024, 11, 17, 10, 0),
                surgery_id=3,
                room_id=1,
                team_id=3,
            )
        )
        logger.info(self.cache.data[Schedule.__tablename__])
        next_vacany = self.algorithm.get_next_vacany()
        expected = datetime(2024, 11, 17, 11, 0)  # A próxima vaga disponível após a duplicata
        self.assertEqual(next_vacany, expected)


class TestAlgorithmExecute(unittest.TestCase):
    def setUp(self):
        """Configura os dados de teste no cache antes de cada teste usando uma sessão em memória."""
        self.session = setup_test_session()

        # Criar e adicionar equipes na sessão
        self.teams = [
            Team(id=1, name="Equipe A"),
            Team(id=2, name="Equipe B")
        ]
        self.session.add_all(self.teams)

        # Criar e adicionar pacientes na sessão
        self.patients = [
            Patient(id=1, name="Paciente 1"),
            Patient(id=2, name="Paciente 2")
        ]
        self.session.add_all(self.patients)

        # Criar e adicionar cirurgias na sessão
        self.surgeries = [
            Surgery(id=1, name="Cirurgia 1", duration=60, patient_id=1, priority=1),
            Surgery(id=2, name="Cirurgia 2", duration=120, patient_id=2, priority=2)
        ]
        self.session.add_all(self.surgeries)

        # Criar possíveis equipes para as cirurgias
        surgery_possible_teams = [
            SurgeryPossibleTeams(surgery_id=1, team_id=1),
            SurgeryPossibleTeams(surgery_id=2, team_id=1),
            SurgeryPossibleTeams(surgery_id=2, team_id=2),
        ]
        self.session.add_all(surgery_possible_teams)

        rooms = [
            Room(id=1, name="Sala 1"),
            Room(id=2, name="Sala 2"),
        ]
        self.session.add_all(rooms)

        # Commit para salvar todos os dados na sessão
        self.session.commit()

        self.cache = InMemoryCache(session=self.session)
        self.cache.load_all_data(self.session)

        now = datetime.now()

        # Criar uma instância do algoritmo
        self.algorithm = Algorithm(self.cache)
        self.algorithm.surgeries = self.cache.get_table(Surgery)
        self.algorithm.next_vacany = now
        self.algorithm.step = 0

    def test_execute_surgeries(self):
        """Teste para verificar se o método execute agenda as cirurgias corretamente."""
        # Definindo uma solução válida que mapeia a execução da cirurgia
        solution = [0, 0]  # Usando índices da equipe disponível para mandar para as cirurgias
        self.algorithm.execute(solution)

        # Verifica que as cirurgias foram agendadas corretamente
        schedules = self.cache.get_table(Schedule)
        self.assertEqual(len(schedules), 2)  # Duas cirurgias devem ser agendadas

        scheduled_surgeries_ids = [schedule.surgery_id for schedule in schedules]
        self.assertIn(1, scheduled_surgeries_ids)  # Cirurgia 1 deve estar agendada
        self.assertIn(2, scheduled_surgeries_ids)  # Cirurgia 2 deve estar agendada


class TestAlgorithmExecuteWithMoreData(unittest.TestCase):
    def setUp(self):
        """Configura um grande conjunto de dados para teste."""
        self.session = setup_test_session()

        # Criar e adicionar equipes na sessão
        self.teams = [
            Team(id=i, name=f"Equipe {i}") for i in range(1, 11)  # 10 equipes
        ]
        self.session.add_all(self.teams)

        # Criar e adicionar pacientes na sessão
        self.patients = [
            Patient(id=i, name=f"Paciente {i}") for i in range(1, 21)  # 20 pacientes
        ]
        self.session.add_all(self.patients)

        # Criar e adicionar cirurgias na sessão
        self.surgeries = [
            Surgery(id=i, name=f"Cirurgia {i}", duration=(i + 1) * 30, patient_id=(i % 20) + 1, priority=i % 5 + 1)
            for i in range(1, 21)  # 20 cirurgias
        ]
        self.session.add_all(self.surgeries)

        # Criar possíveis equipes para as cirurgias
        surgery_possible_teams = [
            SurgeryPossibleTeams(surgery_id=i, team_id=(i % 10) + 1) for i in range(1, 21)
            # Cada cirurgia associada a uma equipe
        ]
        self.session.add_all(surgery_possible_teams)

        # Criar salas
        self.rooms = [
            Room(id=i, name=f"Sala {i}") for i in range(1, 6)  # 5 salas
        ]
        self.session.add_all(self.rooms)

        # Commit para salvar todos os dados na sessão
        self.session.commit()

        self.cache = InMemoryCache(session=self.session)
        self.cache.load_all_data(self.session)

        now = datetime.now()

        # Criar uma instância do algoritmo
        self.algorithm = Algorithm(self.cache)
        self.algorithm.surgeries = self.cache.get_table(Surgery)
        self.algorithm.next_vacany = now
        self.algorithm.step = 0

    def test_execute_with_large_data(self):
        """Teste para verificar se o método execute lida bem com um grande volume de dados."""
        # Definindo uma solução válida que mapeia para as cirurgias
        solution = [0 for i in range(len(self.surgeries))]  # Distribuindo as cirurgias nas 10 equipes

        # Executa o algoritmo
        self.algorithm.execute(solution)

        # Verifica que as cirurgias foram agendadas corretamente
        schedules = self.cache.get_table(Schedule)

        # Esperamos que todas as cirurgias sejam agendadas
        self.assertEqual(len(schedules), 20)  # Todas as 20 cirurgias devem estar agendadas

        scheduled_surgeries_ids = [schedule.surgery_id for schedule in schedules]

        for surgery in self.surgeries:
            self.assertIn(surgery.id, scheduled_surgeries_ids)  # Cada cirurgia deve estar agendada

        # Verifica se todas as equipes registradas possuem agendamentos
        scheduled_teams_ids = {schedule.team_id for schedule in schedules}
        self.assertEqual(len(scheduled_teams_ids), 10)  # Todas as 10 equipes devem estar agendadas
