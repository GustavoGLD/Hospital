from datetime import timedelta
from typing import List, Optional

from loguru import logger

from app.config import LogConfig
from app.models import Room, Surgery, Team, SurgeryPossibleTeams, SurgeryPossibleRooms, Schedule
from app.services.logic.schedule_builders.algorithm import Algorithm
from app.services.logic.schedule_builders.functions.additional_tests import additional_test
from moonlogger import MoonLogger


class RoomLimiter:
    def __init__(self):
        self.finished_rooms = list[Room]()

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def get_next_surgery(self: "Algorithm | RoomLimiter", surgeries: List[Surgery], team: Team) -> Optional[Surgery]:
        """Retorna a próxima cirurgia a ser realizada por uma equipe específica."""
        possibles = self.cache.get_by_attribute(SurgeryPossibleTeams, "team_id", team.id)
        assert possibles, f"this team didn't have any corresponding surgery {team.name} (ID={team.id}): "

        surgeries_possible_room = self.cache.get_by_attribute(SurgeryPossibleRooms, "room_id", self.next_vacany_room.id)
        assert surgeries_possible_room, f"this room didn't have any corresponding surgery {team.name} (ID={self.next_vacany_room.id}): "

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
                    if schedule.surgery_id in [sch.surgery_id for sch in surgeries_possible_room]:
                        psb_cgrs.append(self.cache.get_by_id(Surgery, schedule.surgery_id))

        if not psb_cgrs:
            if LogConfig.algorithm_details:
                logger.error(f"no surgery found for team {team.name} (ID={team.id}) at this time")
            return None

        self.check_agreement()

        surgeries = list(sorted(psb_cgrs, key=lambda x: x.duration / (x.priority or 1)))
        return surgeries[0]

    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def if_no_teams_for_room(self: "Algorithm | RoomLimiter"):
        self.finished_rooms.append(self.next_vacany_room)
        logger.warning(f"No surgery found for any team in room {self.next_vacany_room.name} (ID={self.next_vacany_room.id})")
        all_rooms = self.cache.get_table(Room)

        # future feature: usar o proximo next_vacany_room ao invés de pegar o primeiro
        if len(self.finished_rooms) != len(all_rooms):
            for room in all_rooms:
                if room not in self.finished_rooms:
                    self.next_vacany_room = room
                    room_last_sch = max(self.cache.get_by_attribute(Schedule, "room_id", room.id), key=lambda sch: sch.start_time)
                    self.next_vacany = room_last_sch.start_time + timedelta(
                        minutes=self.cache.get_by_id(Surgery, room_last_sch.surgery_id).duration)
                    self._process_room_with_teams(room, self.solution, self.available_teams)
        else:
            logger.error(
                f"No surgery found for any team.\n{self.surgeries=}\n{self.cache.get_table(SurgeryPossibleTeams)=}")
            # raise ValueError("No surgery found for any team.")
            raise ValueError("No surgery found for any team.")

    @additional_test
    @MoonLogger.log_func(enabled=LogConfig.algorithm_details)
    def check_agreement(self: Algorithm):
        # conferir se as cirurgias agendadas estão de acordo com as possibilidades das salas
        for sch in self.cache.get_table(Schedule):
            if sch.room_id in self.cache.get_by_attribute(SurgeryPossibleRooms, "surgery_id", sch.surgery_id):
                logger.error(f"this schedule is not in agreement with the room possibilities: {sch=}")
                quit()
