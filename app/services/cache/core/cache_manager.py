from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Type, List, Any, Union, Tuple, Dict, TypeVar

from loguru import logger
from sqlmodel import SQLModel

from app.config import LogConfig, additional_tests
from app.models import Surgery, Team, Room, Schedule
from app.models.empty_schedule import EmptySchedule
from moonlogger import MoonLogger

M = TypeVar("M", bound=SQLModel)


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
