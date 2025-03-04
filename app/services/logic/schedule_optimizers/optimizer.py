from datetime import datetime
from typing import List, Dict, Type

import pygad
from loguru import logger

from app.config import LogConfig, DefaultConfig
from app.models import Team, Room, Surgery
from app.services.cache.cache_in_dict import CacheInDict
from app.services.logic.schedule_builders.algorithm import Algorithm
from app.services.logic.schedule_optimizers.solver import Solver
from moonlogger import MoonLogger


class Optimizer:
    def __init__(self, cache: CacheInDict = None, algorithm_base: Type[Algorithm] = Algorithm):
        assert type(cache) == CacheInDict, f"Invalid cache type: {type(cache)}"

        self.cache = cache
        self.zero_time = datetime.now()
        self.solver = Solver(cache)
        self.algorithm = algorithm_base(self.solver.mobile_surgeries, cache, self.zero_time)

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
            num_genes=len(self.solver.mobile_surgeries),
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
