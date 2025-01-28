from copy import copy
from datetime import datetime, timedelta
from typing import List, Tuple, Union, Optional

import pandas as pd
from loguru import logger
from sqlmodel import SQLModel
from tabulate import tabulate

from app.config import LogConfig
from app.models import Surgery, Schedule, Room, Team, SurgeryPossibleTeams
from app.models.empty_schedule import EmptySchedule
from app.services.cache.cache_in_dict import CacheInDict
from app.services.cache.core.cache_manager import CacheManager
from app.services.logic.schedule_builders.functions.additional_tests import additional_test
from moonlogger import MoonLogger


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
        self.solution = []
        self.available_teams = []

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
        self._validate_cache()
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
    def get_next_surgery(self, surgeries: List[Surgery], team: Team) -> Union[Surgery, SQLModel, None]:
        """Retorna a próxima cirurgia a ser realizada por uma equipe específica."""
        possibles = self.cache.get_by_attribute(SurgeryPossibleTeams, "team_id", team.id)

        if not possibles:
            logger.error(f"this team didn't have any corresponding surgery "
                         f"{team.name} (ID={team.id}): ")
            # f"{self.data.get(SurgeryPossibleTeams.__tablename__)}")
            return None

        for surgery in surgeries:
            if surgery.id in [sch.surgery_id for sch in self.cache.get_table(Schedule) if not sch.fixed]:
                logger.error(f"this surgery is already scheduled: {surgery.name}\n{surgery=}")
                logger.error(f"{[sch for sch in self.cache.get_table(Schedule) if sch.surgery_id == surgery.id]=}")
                quit()

            if sch := self.cache.get_by_attribute(Schedule, "surgery_id", surgery.id):
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
                if schedule.surgery_id not in [sch.surgery_id for sch in self.cache.get_table(Schedule) if not sch.fixed]:
                    psb_cgrs.append(self.cache.get_by_id(Surgery, schedule.surgery_id))

        if not psb_cgrs:
            if LogConfig.algorithm_details:
                logger.error(f"no surgery found for team {team.name} (ID={team.id}) at this time")
            return None

        surgeries = list(sorted(psb_cgrs, key=lambda x: x.duration / (x.priority or 1)))
        return surgeries[0]

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
    def get_next_vacany(self) -> Tuple[Room, datetime]:
        """Retorna a próxima vaga disponível."""

        value = self._get_sorted_vacancies()[0]
        self._check_duplicate_vacancy([value])

        return value

    def _check_duplicate_vacancy(self, value, last_value=[None]):
        """Verifica se a próxima vaga é igual à última registrada."""
        if value[0] == last_value[0]:
            logger.error("The next vacancy is the same as the last one")
            logger.error(f"{last_value[0]=}")
            logger.error(f"{value[0]=}")
            raise ValueError("Duplicate vacancy")
        else:
            last_value[0] = value[0]

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
        self.solution = solution

        while self.surgeries:
            self.available_teams = self.cache.get_available_teams(check_time=self.next_vacany)
            assert self.available_teams or self.step != 0, f"Sem equipes. {self.available_teams=}, {self.step=}"

            if self.available_teams:
                self.process_room(solution, self.available_teams)
                self.rooms_according_to_time.append({
                    "Tempo": self.next_vacany,
                    **self.cache.get_dict_surgeries_by_time(self.next_vacany)
                })
                if LogConfig.algorithm_details:
                    self.print_table()

            self.check_non_creation_sch()
            last_next_vacany = self.next_vacany
            self.next_vacany_room, self.next_vacany = self.get_next_vacany()
            self.check_non_use_of_time(self.available_teams, last_next_vacany)

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

        surgery = self.get_next_surgery(self.surgeries, team)

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
            surgery = self.get_next_surgery(self.surgeries, team)
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
            surgery = self.get_next_surgery(self.surgeries, team)
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

        self.if_no_teams_for_room()

    def if_no_teams_for_room(self):
        logger.error(
            f"No surgery found for any team.\n{self.surgeries=}\n{self.cache.get_table(SurgeryPossibleTeams)=}")
        # raise ValueError("No surgery found for any team.")
        quit()
