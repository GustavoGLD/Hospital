from datetime import datetime
from typing import List

from loguru import logger

from app.config import LogConfig
from app.models import Team, Room, Surgery, Schedule
from app.services.cache.cache_in_dict import CacheInDict
from moonlogger import MoonLogger


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
