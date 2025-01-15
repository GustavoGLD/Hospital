import os
from abc import ABC, abstractmethod
from copy import deepcopy, copy
from datetime import timedelta
from typing import Optional, List, TypeVar, Type, Sequence, Tuple, Union, Dict, Any

import pandas as pd
import pygad  # type: ignore
from loguru import logger
from sqlmodel import SQLModel
from tabulate import tabulate

from app.config import DefaultConfig, LogConfig, additional_tests
from app.models.empty_schedule import EmptySchedule
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.room import Room
from app.models.schedule import Schedule
from app.models.surgery import Surgery
from app.models.surgery_possible_teams import SurgeryPossibleTeams
from app.models.team import Team
from moonlogger import MoonLogger
from dotenv import load_dotenv

load_dotenv()

T = TypeVar("T")
M = TypeVar("M", bound=SQLModel)


def setup_test_session():
    engine = create_engine("sqlite:///:memory:")  # Banco de dados em memória
    SQLModel.metadata.create_all(engine)  # Cria as tabelas
    return Session(engine)


def additional_test(func):
    def wrapper(*args, **kwargs):
        if additional_tests:
            return func(*args, **kwargs)
        return None

    return wrapper


from datetime import datetime
from sqlmodel import Session, select


class CacheManager(ABC):
    @abstractmethod
    def get_table(self, table: Type[M]) -> List[M]:
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, table: Type[M], _id: int) -> M:
        raise NotImplementedError

    @abstractmethod
    def get_by_attribute(self, table: Type[M], attribute: str, value: Any) -> List[M]:
        raise NotImplementedError

    @abstractmethod
    def register_surgery(self, surgery: Surgery, team: Team, room: Room, start_time: datetime):
        raise NotImplementedError

    @abstractmethod
    def __copy__(self):
        raise NotImplementedError

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
        available_teams = []

        for team in self.get_table(Team):
            if not self.is_team_busy(team.id, check_time):
                available_teams.append(team)

        return available_teams

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_available_rooms(self, check_time: datetime) -> List[Room]:
        available_rooms = []

        for room in self.get_table(Room):
            if not self.is_room_busy(room.id, check_time):
                available_rooms.append(room)

        return available_rooms

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_next_surgery(self, surgeries: List[Surgery], team: Team) -> Union[Surgery, SQLModel, None]:
        """Retorna a próxima cirurgia a ser realizada por uma equipe específica."""
        possibles = self.get_by_attribute(SurgeryPossibleTeams, "team_id", team.id)

        if not possibles:
            logger.error(f"this team didn't have any corresponding surgery "
                         f"{team.name} (ID={team.id}): ")
            # f"{self.data.get(SurgeryPossibleTeams.__tablename__)}")
            return None

        for surgery in surgeries:
            if surgery.id in [sch.surgery_id for sch in self.get_table(Schedule) if not sch.fixed]:
                logger.error(f"this surgery is already scheduled: {surgery.name}\n{surgery=}")
                logger.error(f"{[sch for sch in self.get_table(Schedule) if sch.surgery_id == surgery.id]=}")
                quit()

            if sch := self.get_by_attribute(Schedule, "surgery_id", surgery.id):
                if sch[0].fixed:
                    logger.error(f"we can't schedule this surgery: {surgery.name} because it's fixed")
                    logger.error(f"{sch[0]=}")
                    quit()

        psb_cgrs = []
        for schedule in possibles:
            # logger.debug(f"{schedule.team_id == team.id=}")
            # logger.debug(f"{schedule.surgery_id in [surgery.id for surgery in surgeries]=}")
            # logger.debug(f"{schedule.surgery_id not in [sch.surgery_id for sch in self.get_table(Schedule) if not sch.fixed]=}")
            if schedule.team_id == team.id and schedule.surgery_id in [surgery.id for surgery in surgeries]:
                if schedule.surgery_id not in [sch.surgery_id for sch in self.get_table(Schedule) if not sch.fixed]:
                    psb_cgrs.append(self.get_by_id(Surgery, schedule.surgery_id))

        if not psb_cgrs:
            if LogConfig.algorithm_details:
                logger.error(f"no surgery found for team {team.name} (ID={team.id}) at this time")
            return None

        surgeries = list(sorted(psb_cgrs, key=lambda x: x.duration / (x.priority or 1)))
        return surgeries[0]

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_surgery_by_time_and_room(self, time: datetime, room: Room) \
            -> Union[tuple[Surgery, Schedule], tuple[None, None], tuple[None, EmptySchedule]]:
        """Retorna a cirurgia agendada para um horário e sala específicos."""
        assert self.get_table(Schedule), "No schedules found in cache."
        surgery, schedule = self._find_surgery_by_time_and_room(time, room)
        return surgery, schedule
        # occupied_intervals = self._get_room_schedule_intervals(room)
        # self._raise_schedule_error(time, room, occupied_intervals)

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _find_surgery_by_time_and_room(self, time: datetime, room: Room) \
            -> Union[tuple[Surgery, Schedule], tuple[None, None], tuple[None, EmptySchedule]]:
        """Procura por uma cirurgia agendada para o horário e sala específicos."""
        last_value: Union[tuple[Surgery, Schedule], tuple[None, None], tuple[None, EmptySchedule], None] = None

        for schedule in self.get_table(Schedule):
            if schedule.room_id == room.id:
                final = schedule.start_time + timedelta(minutes=self.get_by_id(Surgery, schedule.surgery_id).duration)
                if schedule.start_time <= time < final:
                    value = self.get_by_id(Surgery, schedule.surgery_id), schedule
                    if additional_tests:
                        if not last_value:
                            last_value = value
                        else:
                            logger.error(f"More than one surgery found for room {room.name} at {time}: "
                                         f"{last_value}, {value}")
                            logger.error(f"{last_value[0].name}: \t {last_value[1].start_time} -> "
                                         f"{last_value[1].start_time + timedelta(minutes=last_value[0].duration)}")
                            logger.error(f"{value[0].name}: \t {value[1].start_time} -> "
                                         f"{schedule.start_time + timedelta(minutes=value[0].duration)}")
                            quit()
                    else:
                        return value

        for emptysch in self.get_table(EmptySchedule):
            if emptysch.room_id == room.id:
                final = emptysch.start_time + timedelta(minutes=emptysch.duration)
                if emptysch.start_time <= time < final:
                    value = None, emptysch
                    if not last_value:
                        last_value = None, emptysch
                    else:
                        logger.error(f"More than one schedule found for room {room.name} at {time}")

        if last_value:
            return last_value
        else:
            return None, None

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

    @staticmethod
    def _raise_schedule_error(time: datetime, room: Room, intervals: List[Tuple[datetime, datetime]]):
        """Lança uma exceção com informações detalhadas sobre os intervalos ocupados."""
        logger.critical(f"No surgery found for room {room.name} at {time}: {intervals}")
        # raise ValueError(f"No surgery found for room {room.name} at {time}: {intervals}")
        quit()

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_dict_surgeries_by_time(self, time: datetime) -> Dict[str, str]:
        """Retorna um dicionário com todas as cirurgias agendadas para um horário específico."""
        _dict = {}
        for room in self.get_table(Room):
            surgery, schedule = self.get_surgery_by_time_and_room(time, room)
            if surgery and type(schedule) == Schedule:
                _dict[
                    room.name] = f"{self.get_by_id(Team, schedule.team_id).name} - {surgery.name} - {surgery.duration}min"
            elif not surgery and type(schedule) == EmptySchedule:
                _dict[room.name] = f"Empty Schedule - {schedule.duration}min"
            else:
                _dict[room.name] = "None"
        return _dict

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
                    local_total += int(waiting_time.total_seconds() // 60)
            per_room[room.id] = local_total
            global_total += local_total

        return global_total


class CacheInDict(CacheManager):
    def __init__(self, session: Optional[Session] = None):
        """Inicializa o cache e carrega os dados em memória de forma dinâmica."""
        if not hasattr(self, 'data'):
            self.data: dict[str, Any] = {cls.__tablename__: [] for cls in self.get_table_classes()}
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
        return [Team, Professional, Patient, Schedule, Surgery, SurgeryPossibleTeams, Room, EmptySchedule]

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

    # @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
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
    def get_by_attribute(self, table: Type[M], attribute: str, value: Any) -> List[M]:
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

    # @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_table(self, table: Type[M]) -> List[M]:
        """Retorna uma cópia dos dados da tabela especificada para evitar alterações no cache."""
        if table.__tablename__ not in self.data:
            raise ValueError(f"Tabela '{table.__tablename__}' não encontrada no cache.")
        return self.data.get(table.__tablename__, [])

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def register_surgery(self, surgery: Surgery, team: Team, room: Room, start_time: datetime):
        """Registra uma cirurgia no cache e atualiza os índices."""
        self.check_preexistence_sch(surgery)
        self.check_superposition(room, start_time, surgery)

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

    @additional_test
    def check_preexistence_sch(self, surgery):
        if self.get_by_attribute(Schedule, "surgery_id", surgery.id):
            logger.error(f"this surgery is already scheduled: {surgery.name}")
            logger.error(f"{[sch for sch in self.get_table(Schedule) if sch.surgery_id == surgery.id]=}")
            quit()

    @additional_test
    def check_superposition(self, room, start_time, surgery):
        # verificar se sobrepõe com outra cirurgia
        for schedule in self.get_table(Schedule):
            if schedule.room_id == room.id:
                other_surgery = self.get_by_id(Surgery, schedule.surgery_id)
                other_end_time = schedule.start_time + timedelta(minutes=other_surgery.duration)
                if (schedule.start_time < start_time < other_end_time) or \
                        (schedule.start_time < start_time + timedelta(minutes=surgery.duration) < other_end_time):
                    logger.error(f"this surgery overlaps with another surgery: {surgery}")
                    logger.error(f"{surgery.name}: {start_time} -> {start_time + timedelta(minutes=surgery.duration)}")
                    logger.error(f"{schedule.surgery_id}: {schedule.start_time} -> {other_end_time}")
                    logger.error(f"{schedule=}")
                    quit()


class Solver:
    def __init__(self, cache: CacheInDict):
        self.cache = cache
        self.zero_time = datetime.now()
        self.mobile_surgeries = self.get_mobile_surgeries()

    @MoonLogger.log_func(enabled=LogConfig.optimizer_details)
    def gene_space(self):
        _array = []
        high = len(self.cache.get_table(Team)) - 1
        decrements = len(self.cache.get_table(Room)) - 1

        for i in range(len(self.mobile_surgeries)):
            _array.append({"low": 0, "high": high})
            if i < decrements:
                high -= 1
        return _array

    @MoonLogger.log_func(enabled=LogConfig.optimizer_details)
    def get_mobile_surgeries(self):
        fixed_surgeries = [self.cache.get_by_id(Surgery, sch.surgery_id)
                           for sch in self.cache.get_by_attribute(Schedule, "fixed", True)]
        mobile_surgeries = [surgery for surgery in self.cache.get_table(Surgery) if surgery not in fixed_surgeries]

        if not mobile_surgeries:
            logger.error("No mobile surgeries found.")
            quit()

        return mobile_surgeries

    def set_solution(self, solution: List[int]):
        if len(solution) != len(self.mobile_surgeries):
            logger.error(f"Invalid solution. {len(solution)=}, {len(self.mobile_surgeries)=}")
            quit()


class Algorithm:
    def __init__(self, surgeries: List[Surgery], cache: CacheManager = None, zero_time: datetime = datetime.now()):
        assert type(cache) == CacheInDict, f"Invalid cache type: {type(cache)}"

        self.cache = copy(cache)
        self.surgeries: List[Surgery] = copy(surgeries)
        self.zero_time = zero_time
        self.next_vacany = zero_time
        self.next_vacany_room = self.get_first_next_vacany_room()
        self._step = 0
        self.rooms_according_to_time = []
        self.fixed_schedules_considered = list[Schedule]()
        self.empty_schedules_considered = list[EmptySchedule]()

        self.fixed_schedules_disregarded = self.cache.get_by_attribute(Schedule, "fixed", True)

    @property
    def step(self):
        return self._step

    @property
    def fixed_schedules_disregarded(self):
        return self.__fixed_schedules_disregarded

    @fixed_schedules_disregarded.setter
    @MoonLogger.log_func(enabled=True)
    def fixed_schedules_disregarded(self, value):
        self.__fixed_schedules_disregarded = value

    @step.setter
    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def step(self, value):
        self._step = value

    @property
    def fixed_schedules_considered(self):
        return self.__fixed_schedules_considered

    @fixed_schedules_considered.setter
    @MoonLogger.log_func(enabled=True)
    def fixed_schedules_considered(self, value):
        self.__fixed_schedules_considered = value

    @property
    def empty_schedules_considered(self):
        return self.__empty_schedules_considered

    @empty_schedules_considered.setter
    @MoonLogger.log_func(enabled=True)
    def empty_schedules_considered(self, value):
        self.__empty_schedules_considered = value

    def get_first_next_vacany_room(self) -> Room:
        if v := self.cache.get_available_rooms(self.next_vacany):
            return v[0]
        else:
            raise ValueError(f"No rooms available at {self.next_vacany}: {self.cache.get_table(Schedule)}")

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_next_vacancies(self, zero_time: datetime, fixed_schedules_considered: list[Schedule],
                           empty_schedules_considered: list[EmptySchedule]) -> List[Tuple[Room, datetime]]:
        """Retorna um dicionário com as próximas vagas disponíveis em cada sala."""
        vacancies = []
        schedules: list[Schedule | EmptySchedule] = self.cache.get_table(Schedule)
        rooms = self.cache.get_table(Room)

        schedules.extend(fixed_schedules_considered)
        schedules.extend(empty_schedules_considered)

        #assert schedules, "No schedules found in cache."
        assert rooms, "No rooms found in cache."

        for room in rooms:

            local_schedules: list[Schedule | EmptySchedule] = [
                schedule for schedule in schedules if schedule.room_id == room.id
            ]

            # assert local_schedules, f"No schedules found for room {room.name}: {schedules}"
            if not local_schedules:
                vacancies.append((room, zero_time))
            else:
                """
                considerar a ultimo (max) agendamento agendado entre:
                agendamentos não fixos + agendamentos fixos já CONSIDERADOS (fixed_schedules_considered)
                """
                last_schedule = max(local_schedules, key=lambda x: x.start_time + timedelta(
                    minutes=self.cache.get_by_id(Surgery, x.surgery_id).duration
                ))
                vacancies.append((
                    room,
                    last_schedule.start_time + timedelta(
                        minutes=self.cache.get_by_id(Surgery, last_schedule.surgery_id).duration
                    )
                ))

        return vacancies

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_next_schedule(self, room_id: int, check_time: datetime) -> Optional[Schedule | EmptySchedule]:
        schedules: list[Schedule | EmptySchedule] = []
        schedules.extend(self.cache.get_by_attribute(Schedule, "room_id", room_id))
        schedules.extend(self.cache.get_by_attribute(EmptySchedule, "room_id", room_id))

        if schedules:
            future_schs = [sch for sch in schedules if sch.start_time >= check_time]
            if future_schs:
                sch = min(future_schs, key=lambda x: self.how_close_schedule(x, check_time))
                return sch
            else:
                return None

    @step.setter
    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def step(self, value):
        self._step = value

    def print_table(self):
        df = pd.DataFrame(self.rooms_according_to_time)
        logger.debug("\n" + str(tabulate(df, headers="keys", tablefmt="grid")))

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_next_vacany(self, last_value=[None]) -> Tuple[Room, datetime]:
        """Retorna a próxima vaga disponível."""

        self._validate_cache()  # Validações iniciais
        value = self._get_sorted_vacancies()[0]

        if value == last_value[0]:
            logger.error(f"The next vacancy is the same as the last one")
            logger.error(f"{last_value[0]=}")
            logger.error(f"{value=}")
            quit()
        else:
            last_value[0] = value

        return value

    def _validate_cache(self):
        """Valida se o cache possui as tabelas necessárias."""
        if not self.cache.get_table(Schedule):
            raise ValueError("No schedules found in cache")
        if not self.cache.get_table(Room):
            raise ValueError("No rooms found in cache.")

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def _get_sorted_vacancies(self) -> List[Tuple[Room, datetime]]:
        """Obtém e ordena as vagas disponíveis."""
        vacanies = self.get_next_vacancies(self.zero_time, self.fixed_schedules_considered,
                                           self.empty_schedules_considered)
        if not vacanies:
            raise ValueError("No vacancies found.")
        return sorted(vacanies, key=lambda x: x[1])

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def execute(self, solution: List[int]) -> pd.DataFrame:
        self.step = 0

        assert self.surgeries, "Sem cirurgias."
        assert self.cache.get_table(Team), "Sem equipes."
        assert self.cache.get_table(Room), "Sem salas."
        assert len(solution) == len(self.surgeries), f"Solução inválida. {len(solution)=}, {len(self.surgeries)=}"

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

            self.check_non_creation_sch()
            last_next_vacany = self.next_vacany
            self.next_vacany_room, self.next_vacany = self.get_next_vacany()
            self.check_non_use_of_time(available_teams, last_next_vacany)

        # montar um dataframe de todos os agendamentos em função do tempo
        schedules_dict = []
        for sch in self.cache.get_table(Schedule):
            schedules_dict.append([{
                "Tempo": sch.start_time,
                **self.cache.get_dict_surgeries_by_time(sch.start_time)
            }])
        for emptysch in self.cache.get_table(EmptySchedule):
            schedules_dict.append([{
                "Tempo": emptysch.start_time,
                **self.cache.get_dict_surgeries_by_time(emptysch.start_time)
            }])

        self.check_remaining_surgeries()

        df = pd.DataFrame([item for sublist in schedules_dict for item in sublist])
        if LogConfig.algorithm_details:
            logger.debug("\n" + str(tabulate(df, headers="keys", tablefmt="grid")))
        return df

    @additional_test
    def check_remaining_surgeries(self):
        surgs_scheduled = [sch.surgery_id for sch in self.cache.get_table(Schedule)]
        for surg in self.cache.get_table(Surgery):
            if surg.id not in surgs_scheduled:
                logger.error(f"this surgery wasn't scheduled: {surg=}")
                quit()

    @additional_test
    def check_non_creation_sch(self):
        schs = self.cache.get_by_attribute(Schedule, "room_id", self.next_vacany_room.id)
        if not any([sch.start_time == self.next_vacany for sch in schs]):
            logger.error(f"the schedule wasn't created in '{self.next_vacany_room.name}' at {self.next_vacany}")

    @additional_test
    def check_non_use_of_time(self, available_teams, last_next_vacany):
        if last_next_vacany < self.next_vacany:
            for room in self.cache.get_table(Room):
                if not self.cache.is_room_busy(room.id, last_next_vacany):
                    for surg in self.surgeries:
                        for pss_sch in self.cache.get_by_attribute(SurgeryPossibleTeams, "surgery_id", surg.id):
                            if pss_sch.team_id in [team.id for team in available_teams]:
                                logger.warning(f"there is a surgery that can be scheduled in room {room.name} "
                                               f"at {last_next_vacany} but it's not being scheduled.")
                                logger.warning(f"{surg=}, {pss_sch=}, {available_teams=}")

    @staticmethod
    def how_close_schedule(sch: Schedule, ntime: datetime) -> timedelta:
        n = sch.start_time - ntime
        if n < timedelta():
            return timedelta(days=999999999)
        else:
            return n

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def process_room(self, solution: List[int], available_teams: List[Team]):
        assert self.surgeries, "Sem cirurgias."
        assert available_teams, "Sem equipes disponíveis."
        assert self.cache.get_table(Room), "Sem salas."

        self._process_room_with_teams(self.next_vacany_room, solution, available_teams)

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
        def get_last_schedule() -> Tuple[Union[Schedule, EmptySchedule], int]:
            schedules = list[Tuple[Union[Schedule, EmptySchedule], int]]()

            for sch in self.cache.get_table(Schedule):
                if sch.room_id == room.id:
                    schedules.append((sch, self.cache.get_by_id(Surgery, sch.surgery_id).duration))
            for sch in self.cache.get_table(EmptySchedule):
                if sch.room_id == room.id:
                    schedules.append((sch, sch.duration))

            return max(schedules, key=lambda x: x[0].start_time + timedelta(minutes=x[1]))

        for team in self.cache.get_table(Team):
            surgery = self.cache.get_next_surgery(self.surgeries, team)
            if surgery:
                schedules = self.cache.get_by_attribute(Schedule, "team_id", team.id)

                # last_team_schedule = max(schedules, key=lambda x: x.start_time + timedelta(
                #    minutes=self.cache.get_by_id(Surgery, x.surgery_id).duration
                # ))
                # start_time = last_team_schedule.start_time + timedelta(minutes=surgery.duration)

                last_sch = get_last_schedule()
                start_time = last_sch[0].start_time + timedelta(minutes=last_sch[1])
                room = self.cache.get_by_id(Room, last_sch[0].room_id)
                self._register_surgery_and_update(surgery, team, room, start_time)
                return

                # _room = self.cache.get_by_id(Room, last_team_schedule.room_id)
                # self._register_surgery_and_update(surgery, team, _room, start_time)

        logger.error(
            f"No surgery found for any team.\n{self.surgeries=}\n{self.cache.get_table(SurgeryPossibleTeams)=}")
        # raise ValueError("No surgery found for any team.")
        quit()


class FixedSchedules(Algorithm):
    def get_next_schedule(self, room_id: int, check_time: datetime) -> Optional[Schedule | EmptySchedule]:
        schedules: list[Schedule | EmptySchedule] = []
        schedules.extend(self.cache.get_by_attribute(Schedule, "room_id", room_id))
        schedules.extend(self.cache.get_by_attribute(EmptySchedule, "room_id", room_id))

        if schedules:
            future_schs = [sch for sch in schedules if sch.start_time >= check_time]
            if future_schs:
                sch = min(future_schs, key=lambda x: self.how_close_schedule(x, check_time))
                return sch
            else:
                return None

    @staticmethod
    def how_close_schedule(sch: Schedule, ntime: datetime) -> timedelta:
        n = sch.start_time - ntime
        if n < timedelta():
            return timedelta(days=999999999)
        else:
            return n

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

        if any([sc.start_time > self.next_vacany for sc in self.cache.get_by_attribute(Schedule, "room_id", room.id)]):
            schedule = self.get_next_schedule(room.id, self.next_vacany)

            if surgery:
                if schedule.start_time - self.next_vacany >= timedelta(minutes=surgery.duration) > timedelta():
                    self._register_surgery_and_update(surgery, team, room, self.next_vacany)
                else:
                    # não é possível encaixar a cirurgia no horário disponível
                    interval = schedule.start_time - self.next_vacany
                    if not self._try_other_teams(room, available_teams):
                        empty_schedule = EmptySchedule(
                            room_id=room.id,
                            start_time=self.next_vacany,
                            duration=int(interval.total_seconds() // 60)
                        )
                        if schedule.fixed:
                            if schedule not in self.fixed_schedules_considered:
                                self.fixed_schedules_considered.append(schedule)
                            if schedule in self.fixed_schedules_disregarded:
                                self.fixed_schedules_disregarded.remove(schedule)
                        self.empty_schedules_considered.append(empty_schedule)
                        logger.success(f"Empty schedule created at {self.next_vacany}. { EmptySchedule=}")
                        logger.success(f"New considered schedule: {empty_schedule}")
            else:
                interval = schedule.start_time - self.next_vacany
                if not self._try_other_teams(room, available_teams, interval=interval):
                    empty_schedule = EmptySchedule(
                        room_id=room.id,
                        start_time=self.next_vacany,
                        duration=int(interval.total_seconds() // 60)
                    )
                    if schedule.fixed:
                        if schedule not in self.fixed_schedules_considered:
                            self.fixed_schedules_considered.append(schedule)
                        if schedule in self.fixed_schedules_disregarded:
                            self.fixed_schedules_disregarded.remove(schedule)
                    self.empty_schedules_considered.append(empty_schedule)
                    logger.success(f"Empty schedule created at {self.next_vacany}. { EmptySchedule=}")
                    logger.success(f"New considered schedule: {empty_schedule}")

        elif surgery:
            self._register_surgery_and_update(surgery, team, room, self.next_vacany)
        else:
            if not self._try_other_teams(room, available_teams):
                self._try_global_teams(room)

        @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
        def get_next_vacancies(self, zero_time: datetime, fixed_schedules_considered: list[Schedule],
                               empty_schedules_considered: list[EmptySchedule]) -> List[Tuple[Room, datetime]]:
            """Retorna um dicionário com as próximas vagas disponíveis em cada sala."""
            vacancies = []
            schedules: list[Schedule | EmptySchedule] = self.cache.get_table(Schedule)
            rooms = self.cache.get_table(Room)

            assert schedules, "No schedules found in cache."
            assert rooms, "No rooms found in cache."

            for room in rooms:

                local_schedules: list[Schedule | EmptySchedule] = [
                    schedule for schedule in schedules if schedule.room_id == room.id
                ]

                def is_room_empty() -> bool:
                    for sch in schedules:
                        if not sch.fixed and sch.room_id == room.id:
                            return False
                    for sch in empty_schedules_considered:
                        if sch.room_id == room.id:
                            return False
                    for sch in fixed_schedules_considered:
                        if sch.room_id == room.id:
                            return False
                    return True

                def latest_schedule_in_room(room: Room) -> tuple[Union[Schedule, EmptySchedule], int]:
                    all_schedules = list[tuple[Union[Schedule, EmptySchedule], int]]()
                    for sch in schedules:
                        if not sch.fixed and sch.room_id == room.id:
                            all_schedules.append((sch, self.cache.get_by_id(Surgery, sch.surgery_id).duration))
                    for sch in empty_schedules_considered:
                        if sch.room_id == room.id:
                            all_schedules.append((sch, sch.duration))
                    for sch in fixed_schedules_considered:
                        if sch.room_id == room.id:
                            all_schedules.append((sch, self.cache.get_by_id(Surgery, sch.surgery_id).duration))

                    return max(all_schedules, key=lambda x: x[0].start_time + timedelta(minutes=x[1]))

                if is_room_empty():
                    vacancies.append((room, zero_time))
                else:
                    """
                    considerar a ultimo (max) agendamento agendado entre:
                    agendamentos não fixos + agendamentos fixos já CONSIDERADOS (fixed_schedules_considered)
                    """
                    last_schedule = latest_schedule_in_room(room)
                    vacancies.append((
                        room,
                        last_schedule[0].start_time + timedelta(minutes=last_schedule[1])
                    ))

            return vacancies

        @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
        def _try_other_teams(self, room: Room, available_teams: List[Team], interval=timedelta()) -> bool:
            for team in available_teams:
                surgery = self.cache.get_next_surgery(self.surgeries, team)
                if surgery:
                    if next_sch := self.get_next_schedule(room.id, self.next_vacany):
                        interval = next_sch.start_time - self.next_vacany
                        if interval >= timedelta(minutes=surgery.duration) > timedelta():
                            # a cirurgia cabe no intervalo
                            self._register_surgery_and_update(surgery, team, room, self.next_vacany)
                            return True
                    else:
                        self._register_surgery_and_update(surgery, team, room, self.next_vacany)
                        return True
            return False


class Optimizer:
    def __init__(self, cache: CacheInDict = None):
        assert type(cache) == CacheInDict, f"Invalid cache type: {type(cache)}"

        self.cache = cache
        self.zero_time = datetime.now()
        self.solver = Solver(cache)
        self.algorithm = Algorithm(self.solver.mobile_surgeries, cache, self.zero_time)

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
        algorithm = Algorithm(self.solver.mobile_surgeries, cache, self.zero_time)
        try:
            algorithm.execute(solution)
        except Exception as e:
            logger.error(f"Error in fitness function: {e}")
            return -float("inf")
        punishment = algorithm.cache.calculate_punishment(self.zero_time)
        if LogConfig.optimizer_details:
            logger.debug(f"Punishment: {punishment}")
        return -punishment

    def fitness_function(self):
        def function(ga_instance, solution, solution_idx):
            @MoonLogger.log_func(enabled=LogConfig.optimizer_details)
            def function2(self, ga_instance, solution, solution_idx):
                if LogConfig.optimizer_details:
                    logger.debug(f"Solution: {solution}, {solution_idx=}")
                algorithm = Algorithm(self.solver.mobile_surgeries, self.cache, self.zero_time)
                try:
                    algorithm.execute(solution)
                except Exception as e:

                    logger.error(f"Error in fitness function: {e}")
                    return -float("inf")
                punishment = algorithm.cache.calculate_punishment(self.zero_time)
                if LogConfig.optimizer_details:
                    logger.debug(f"Punishment: {punishment}")
                return -punishment

            return function2(self, ga_instance, solution, solution_idx)

        return function

    @MoonLogger.log_func(enabled=LogConfig.optimizer_details)
    def run(self) -> List[int]:
        gene_space_array = self.solver.gene_space()

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

    engine = create_engine(str(os.getenv("DB_URL")))
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        try:
            logger.info("Limpando a tabela de agendamentos...")
            for row in session.exec(select(Schedule)).all():
                session.delete(row)
            session.commit()

            logger.info("Recolhendo dados do banco de dados...")
            cache = CacheInDict(session=session)

            logger.info("Executando o algoritmo...")
            optimizer = Optimizer(cache=cache)
            solution = optimizer.run()

            logger.info("Processando a solução...")
            algorithm = Algorithm(optimizer.solver.mobile_surgeries, cache, datetime.now())
            algorithm.execute(solution)
            algorithm.print_table()

            logger.info("Salvando os resultados no banco de dados...")

            session.add_all(algorithm.cache.get_table(Schedule))
            session.commit()
        except Exception as e:
            logger.error(f"Erro ao executar.")
            raise e
        else:
            logger.success(f"Análise de Desempenho. Tempo gasto: {MoonLogger.time_dict}")
