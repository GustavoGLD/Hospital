from copy import deepcopy
from datetime import datetime, timedelta
from typing import Optional, Any, List, Type, Sequence, TypeVar

from loguru import logger
from sqlmodel import Session, SQLModel, select

from app.config import LogConfig
from app.models import Team, Professional, Patient, Schedule, Surgery, SurgeryPossibleTeams, Room, SurgeryPossibleRooms
from app.models.empty_schedule import EmptySchedule
from app.services.cache.core.cache_manager import CacheManager
from app.services.logic.schedule_builders.functions.additional_tests import additional_test
from moonlogger import MoonLogger

T = TypeVar("T")
M = TypeVar("M", bound=SQLModel)


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
        # reconhecer todas as classes em app/models
        return [Team, Professional, Patient, Schedule, Surgery, SurgeryPossibleTeams, Room, EmptySchedule,
                SurgeryPossibleRooms]

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
