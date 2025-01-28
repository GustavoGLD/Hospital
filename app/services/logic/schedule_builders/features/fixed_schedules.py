from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Union

from loguru import logger

from app.config import LogConfig
from app.models import Schedule, Room, Team, Surgery
from app.models.empty_schedule import EmptySchedule
from app.services.logic.schedule_builders.algorithm import Algorithm
from moonlogger import MoonLogger


class FixedSchedules:
    def get_next_schedule(self: Algorithm, room_id: int, check_time: datetime) -> Optional[Schedule | EmptySchedule]:
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
    def _process_room_with_teams(self: Algorithm, room: Room, solution: List[int], available_teams: List[Team]):
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

        surgery = self.get_next_surgery(self.surgeries, team)

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
    def get_next_vacancies(self: Algorithm, zero_time: datetime, fixed_schedules_considered: list[Schedule],
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
    def _try_other_teams(self: Algorithm, room: Room, available_teams: List[Team], interval=timedelta()) -> bool:
        for team in available_teams:
            surgery = self.get_next_surgery(self.surgeries, team)
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
