from loguru import logger


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
    algorithm_details: bool = False
    optimizer_details: bool = True


additional_tests = True


logger.add("app.log", rotation="10 MB", retention="10 days", level="DEBUG")
