import os
from abc import ABC, abstractmethod
from copy import deepcopy, copy
from datetime import datetime, timedelta
from typing import Optional, List, TypeVar, Type, Sequence, Tuple, Union, Dict
from unittest.mock import MagicMock

import pandas as pd
import pygad
from loguru import logger
from sqlmodel import Field, SQLModel, Relationship
from tabulate import tabulate

from moonlogger import MoonLogger
from dotenv import load_dotenv

load_dotenv()

T = TypeVar("T")
M = TypeVar("M", bound=SQLModel)


class DefaultConfig:
    num_generations = 25
    sol_per_pop = 50
    num_parents_mating = 9
    mutation_percent_genes = [5, 4]
    keep_parents = -1
    crossover_type = "single_point"
    mutation_type = "random"
    parent_selection_type = "sss"


class LogConfig:
    algorithm_details: bool = True
    optimizer_details: bool = True


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


class CacheManager(ABC):
    @abstractmethod
    def get_table(self, table: Type[M]) -> List[M]:
        raise NotImplementedError

    @abstractmethod
    def get_next_vacancies(self):
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, table: Type[M], _id: int) -> M:
        raise NotImplementedError

    @abstractmethod
    def get_by_attribute(self, table: Type[M], attribute: str, value: any) -> List[M]:
        raise NotImplementedError

    @abstractmethod
    def is_team_busy(self, team_id: int, check_time: datetime) -> bool:
        raise NotImplementedError

    @abstractmethod
    def is_room_busy(self, room_id: int, check_time: datetime) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_available_teams(self, check_time: datetime) -> List[Team]:
        raise NotImplementedError

    @abstractmethod
    def register_surgery(self, surgery: Surgery, team: Team, room: Room, start_time: datetime):
        raise NotImplementedError

    @abstractmethod
    def get_next_surgery(self, surgeries: List[Surgery], team: Team) -> Union[Surgery, SQLModel, None]:
        raise NotImplementedError

    @abstractmethod
    def get_dict_surgeries_by_time(self, time: datetime) -> Dict[str, str]:
        raise NotImplementedError

    @abstractmethod
    def __copy__(self):
        raise NotImplementedError


class CacheInDict(CacheManager):
    def __init__(self, session: Optional[Session] = None):
        """Inicializa o cache e carrega os dados em memória de forma dinâmica."""
        if not hasattr(self, 'data'):
            self.data = {cls.__tablename__: [] for cls in self.get_table_classes()}
            self.indexes = {}
            if session:
                self.load_all_data(session)

    def __copy__(self):
        _new = CacheInDict()
        _new.data = deepcopy(self.data)
        return _new

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
    def _build_index(self, table: Type[M]):
        tablename = table.__tablename__
        if tablename not in self.indexes:
            self.indexes[tablename] = {row.id: row for row in self.data.get(tablename, [])}

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _build_attribute_index(self, table: Type[M], attribute: str):
        tablename = table.__tablename__
        # Garante a estrutura do índice por tabela e atributo
        if tablename not in self.indexes:
            self.indexes[tablename] = {}
        if attribute not in self.indexes[tablename]:
            # Cria o índice para o atributo específico
            self.indexes[tablename][attribute] = {}
            for row in self.data.get(tablename, []):
                attr_value = getattr(row, attribute, None)
                if attr_value not in self.indexes[tablename][attribute]:
                    self.indexes[tablename][attribute][attr_value] = []
                self.indexes[tablename][attribute][attr_value].append(row)

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_by_id(self, table: Type[M], _id: int) -> M:
        assert isinstance(_id, int), f"ID {_id} deve ser um inteiro."

        self._build_index(table)  # Garante que o índice existe

        tablename = table.__tablename__
        if _id in self.indexes[tablename]:
            return self.indexes[tablename][_id]

        raise ValueError(f"ID {_id} não encontrado na tabela '{tablename}'.")

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_by_attribute(self, table: Type[M], attribute: str, value: any) -> List[M]:
        assert hasattr(table, attribute), f"Table '{table.__tablename__}' does not have attribute '{attribute}'."

        self._build_attribute_index(table, attribute)

        # Recupera e retorna as linhas correspondentes ao valor do atributo
        tablename = table.__tablename__
        return self.indexes[tablename][attribute].get(value, [])

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

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_table(self, table: Type[M]) -> List[M]:
        """Retorna uma cópia dos dados da tabela especificada para evitar alterações no cache."""
        if table.__tablename__ not in self.data:
            raise ValueError(f"Tabela '{table.__tablename__}' não encontrada no cache.")
        return self.data.get(table.__tablename__, [])

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def is_team_busy(self, team_id: int, check_time: datetime) -> bool:
        schedules = self.get_by_attribute(Schedule, "team_id", team_id)
        if not schedules:
            return False

        for schedule in schedules:
            start_time = schedule.start_time
            end_time = start_time + timedelta(minutes=self.get_by_id(Surgery, schedule.surgery_id).duration)
            if start_time <= check_time < end_time:
                return True
        return False

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
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
    def get_next_surgery(self, surgeries: List[Surgery], team: Team) -> Union[Surgery, SQLModel, None]:
        """Retorna a próxima cirurgia a ser realizada por uma equipe específica."""
        possibles = self.get_by_attribute(SurgeryPossibleTeams, "team_id", team.id)

        if not possibles:
            logger.error(f"this team didn't have any corresponding surgery "
                         f"{team.name} (ID={team.id}): "
                         f"{self.data.get(SurgeryPossibleTeams.__tablename__)}")
            return None

        psb_cgrs = []
        for schedule in possibles:
            if schedule.team_id == team.id and schedule.surgery_id in [surgery.id for surgery in surgeries]:
                psb_cgrs.append(self.get_by_id(Surgery, schedule.surgery_id))

        if not psb_cgrs:
            if LogConfig.algorithm_details:
                logger.error(f"no surgery found for team {team.name} (ID={team.id}) at this time")
            return None

        surgeries = list(sorted(psb_cgrs, key=lambda x: x.duration / (x.priority or 1)))
        return surgeries[0]

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def register_surgery(self, surgery: Surgery, team: Team, room: Room, start_time: datetime):
        """Registra uma cirurgia no cache e atualiza os índices."""
        if LogConfig.algorithm_details:
            logger.success(
                f"Registering surgery {surgery.name} for team {team.name} in room {room.name} at {start_time}")

        # Criação do objeto Schedule
        new_schedule = Schedule(
            start_time=start_time,
            surgery_id=surgery.id,
            room_id=room.id,
            team_id=team.id
        )

        # Adiciona ao cache
        tablename = 'schedule'
        self.data[tablename].append(new_schedule)

        # Atualiza os índices (usando a chave composta)
        if tablename not in self.indexes:
            self.indexes[tablename] = {}  # Garante a inicialização

        # Índice pela chave composta: (surgery_id, room_id, team_id)
        composite_key = (new_schedule.surgery_id, new_schedule.room_id, new_schedule.team_id)
        if 'composite_key' not in self.indexes[tablename]:
            self.indexes[tablename]['composite_key'] = {}
        self.indexes[tablename]['composite_key'][composite_key] = new_schedule

        # Índices adicionais por atributos importantes
        for attribute in ['surgery_id', 'room_id', 'team_id', 'start_time']:
            if attribute not in self.indexes[tablename]:
                self.indexes[tablename][attribute] = {}
            attr_value = getattr(new_schedule, attribute)
            if attr_value not in self.indexes[tablename][attribute]:
                self.indexes[tablename][attribute][attr_value] = []
            self.indexes[tablename][attribute][attr_value].append(new_schedule)

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
    def _get_room_schedule_intervals(self, room: Room) -> List[Tuple[datetime, datetime]]:
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
    def get_dict_surgeries_by_time(self, time: datetime) -> Dict[str, str]:
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
    def get_next_vacancies(self) -> List[Tuple[Room, datetime]]:
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

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def calculate_punishment(self, zero_time: datetime) -> float:
        assert self.get_table(Room), "No rooms found in cache."

        if not self.get_table(Schedule):
            logger.warning("No schedules found in cache.")
            return 0

        per_room = {}
        global_total = 0

        for room in self.get_table(Room):
            local_total = 0
            for schedule in self.get_by_attribute(Schedule, "room_id", room.id):
                waiting_time = schedule.start_time - zero_time
                if waiting_time.total_seconds() > 0:
                    local_total += waiting_time.total_seconds() // 60
            per_room[room.id] = local_total
            global_total += local_total

        return global_total


class Algorithm:
    def __init__(self, cache: CacheManager = None, zero_time: datetime = datetime.now()):
        self.cache = copy(cache)
        self.surgeries: List[Surgery] = copy(self.cache.get_table(Surgery))
        self.next_vacany = zero_time
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
    def _get_sorted_vacancies(self) -> List:
        """Obtém e ordena as vagas disponíveis."""
        vacanies = self.cache.get_next_vacancies()
        if not vacanies:
            raise ValueError("No vacancies found.")
        return sorted(vacanies, key=lambda x: x[1])

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _adjust_duplicate_vacancies(self, vacanies_dt: List[datetime]) -> List[datetime]:
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
    def _get_next_available_time(self, vacanies_dt: List[datetime]) -> datetime:
        """Retorna o próximo horário disponível baseado na lista ajustada."""
        if LogConfig.algorithm_details:
            logger.debug(f"{self.next_vacany=}")
        if self.next_vacany in vacanies_dt:
            index = vacanies_dt.index(self.next_vacany)
            if index + 1 < len(vacanies_dt):
                return vacanies_dt[index + 1]

        return vacanies_dt[0] if vacanies_dt else self.next_vacany + timedelta(seconds=1)

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def execute(self, solution: List[int]):
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
    def process_room(self, solution: List[int], available_teams: List[Team]):
        assert self.surgeries, "Sem cirurgias."
        assert available_teams, "Sem equipes disponíveis."
        assert self.cache.get_table(Room), "Sem salas."

        for room in self.cache.get_table(Room):
            if self.surgeries and available_teams and not self.cache.is_room_busy(room.id, self.next_vacany) :
                self._process_room_with_teams(room, solution, available_teams)
            else:
                if LogConfig.algorithm_details:
                    logger.debug(f"Room {room.name} is busy at {self.next_vacany}")

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _process_room_with_teams(self, room: Room, solution: List[int], available_teams: List[Team]):
        try:
            team_n = solution[self.step]
        except IndexError as e:
            logger.error(f"The step is out of range. {len(solution)=}, {self.step=}, {solution=}")
            raise e

        try:
            if team_n >= len(available_teams):
                team = available_teams[-1]
            else:
                team = available_teams[team_n]
        except IndexError as e:
            logger.error(f"there are not enough teams for this index."
                         f"{team_n=}, {len(available_teams)=}, {available_teams=}, {solution=}")
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


class Optimizer:
    def __init__(self, cache: CacheInDict = None):
        self.cache = cache
        self.zero_time = datetime.now()
        self.algorithm = Algorithm(cache, self.zero_time)

    @MoonLogger.log_func(enabled=LogConfig.optimizer_details)
    def gene_space(self) -> List[Dict[str, int]]:
        _array: List[Dict[str, int]] = []
        high = len(self.cache.get_table(Team)) - 1
        decrements = len(self.cache.get_table(Room)) - 1

        for i in range(len(self.cache.get_table(Surgery))):
            _array.append({"low": 0, "high": high})
            if i < decrements:
                high -= 1
        return _array

    @MoonLogger.log_func(enabled=LogConfig.optimizer_details)
    def function2(self, ga_instance, solution, solution_idx):
        if LogConfig.optimizer_details:
            logger.debug(f"Solution: {solution}, {solution_idx=}")
        algorithm = Algorithm(self.cache)
        try:
            algorithm.execute(solution)
        except Exception as e:
            logger.error(f"Error in fitness function: {e}")
            return -float("inf")
        punishment = self.cache.calculate_punishment(self.zero_time)
        if LogConfig.optimizer_details:
            logger.debug(f"Punishment: {punishment}")
        return -punishment

    def fitness_function(self):
        def function(ga_instance, solution, solution_idx):
            @MoonLogger.log_func(enabled=LogConfig.optimizer_details)
            def function2(self, ga_instance, solution, solution_idx):
                if LogConfig.optimizer_details:
                    logger.debug(f"Solution: {solution}, {solution_idx=}")
                algorithm = Algorithm(self.cache)
                try:
                    algorithm.execute(solution)
                except Exception as e:
                    logger.error(f"Error in fitness function: {e}")
                    return -float("inf")
                punishment = self.cache.calculate_punishment(self.zero_time)
                if LogConfig.optimizer_details:
                    logger.debug(f"Punishment: {punishment}")
                return -punishment
            return function2(self, ga_instance, solution, solution_idx)
        return function

    @MoonLogger.log_func(enabled=LogConfig.optimizer_details)
    def run(self) -> List[int]:
        gene_space_array = self.gene_space()

        ga_instance = pygad.GA(
            num_generations=DefaultConfig.num_generations,
            num_parents_mating=DefaultConfig.num_parents_mating,
            sol_per_pop=DefaultConfig.sol_per_pop,
            num_genes=len(self.cache.get_table(Surgery)),
            gene_space=gene_space_array,
            fitness_func=self.fitness_function(),
            random_mutation_min_val=-3,
            random_mutation_max_val=3,
            mutation_type=DefaultConfig.mutation_type,
            gene_type=int,
            parent_selection_type=DefaultConfig.parent_selection_type,
            keep_parents=DefaultConfig.keep_parents,
            crossover_type=DefaultConfig.crossover_type
        )

        ga_instance.run()
        solution, punishment, solution_idx = ga_instance.best_solution()
        return solution


from sqlmodel import create_engine, Session
from datetime import datetime


if __name__ == "__main__":
    engine = create_engine(os.getenv("DB_URL"))

    with Session(engine) as session:
        try:
            logger.info("Lendo o banco de dados...")
            cache = CacheInDict(session=session)
            logger.info("Executando o algoritmo...")
            optimizer = Optimizer(cache=cache)
            solution = optimizer.run()

            logger.info("Processando a solução...")
            algorithm = Algorithm(cache)
            algorithm.execute(solution)
            algorithm.print_table()

            logger.info("Salvando os resultados no banco de dados...")
            for row in session.exec(select(Schedule)).all():
                session.delete(row)

            session.add_all(algorithm.cache.get_table(Schedule))
            session.commit()
        except Exception as e:
            logger.error(f"Erro ao executar.")
            raise e
        else:
            logger.success(f"Análise de Desempenho. Tempo gasto: {MoonLogger.time_dict}")

