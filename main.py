import copy
import random
from itertools import permutations
from sys import stdout
from contextlib import contextmanager
import sys, os
import pygad
from matplotlib import pyplot as plt
from skopt import gp_minimize
from skopt.plots import plot_convergence
from loguru import logger
import streamlit as st

logger.remove()
logger.add(stdout, level="DEBUG")


class Global:
    cirurgies_to_order: list["Cirurgy"] = []
    roomlist_to_organize: "RoomList" = None


class Cirurgy:
    __counter = 0
    __all_cirurgies = []

    def __init__(self, duration: int, punishment: int):
        self.punishment = punishment
        self.duration = duration
        self.id = self.__generate_id()
        self.__register_cirurgy()

    @staticmethod
    def reset_cirurgies():
        Cirurgy.__all_cirurgies.clear()
        Cirurgy.__counter = 0

    @staticmethod
    def __generate_id():
        _id = Cirurgy.__counter
        Cirurgy.__counter += 1
        return _id

    def __register_cirurgy(self):
        Cirurgy.__all_cirurgies.append(self)

    def get_punishment(self, total_time: int) -> int:
        return self._punishment * total_time

    @property
    def punishment(self) -> int:
        return self._punishment

    @punishment.setter
    def punishment(self, value: int):
        if not isinstance(value, int):
            raise TypeError("Punishment must be an integer")
        self._punishment = value

    @property
    def duration(self) -> int:
        return self._duration

    @duration.setter
    def duration(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError("Duration must be an integer")
        self._duration = value

    @classmethod
    def get_all_cirurgies(cls) -> list["Cirurgy"]:
        return cls.__all_cirurgies

    @staticmethod
    def get_by_id(_id: int) -> "Cirurgy":
        return next(filter(lambda x: x.id == _id, Cirurgy.__all_cirurgies), None)

    def __repr__(self):
        return f"Cirurgy(duration={self.duration}, punishment={self.punishment})"


class RoomList:
    def __init__(self, rooms: list["Room"]):
        self.__rooms = rooms
        for i, room in enumerate(self.__rooms):
            room.id = i

    def get_by_id(self, _id: int) -> "Room":
        r = next(filter(lambda x: x.id == _id, self.__rooms), None)
        if r is None:
            raise ValueError(f"Room with id {_id} not found. all IDs: {[r.id for r in self.__rooms]}")
        return r

    def reset_all_rooms(self):
        for room in self.__rooms:
            room.reset_cirurgies()

    def get_all_rooms(self) -> list["Room"]:
        return copy.copy(self.__rooms)

    def best_rooms_organization(self) -> None:
        best_distribution = Logic.best_distribution(Cirurgy.get_all_cirurgies(), self)
        for cirurgy_id, room_id in enumerate(best_distribution):
            self.get_by_id(room_id).add_cirurgies([Cirurgy.get_by_id(cirurgy_id)])

        for room in self.__rooms:
            with suppress_stdout():
                room.calculate_less_punishment()
            logger.info(f"Sala {room.id}: {room.best_order}")

    def __len__(self):
        return len(self.__rooms)

    def __getitem__(self, item):
        return self.__rooms[item]

    def __setitem__(self, key, value):
        self.__rooms[key] = value

    def __iter__(self):
        return iter(self.__rooms)


class Room:

    def __init__(self, cirurgies: list[Cirurgy] = None):
        self.cirurgies = cirurgies if cirurgies else []
        self.total_punishment = None
        self.best_order = None
        self.id = 0

    def calculate_less_punishment(self) -> int:
        self.best_order, self.total_punishment = Logic.get_best_order(self.cirurgies)
        #logger.debug(f"Sala: {self.id}; Total punishment: {self.total_punishment}; Best order: {self.best_order},")
        return self.total_punishment

    def reset_cirurgies(self):
        self.cirurgies.clear()
        self.total_punishment = None
        self.best_order = None

    @property
    def total_punishment(self) -> int:
        if self._total_punishment is None: self.calculate_less_punishment()
        return self._total_punishment

    @total_punishment.setter
    def total_punishment(self, value: int) -> None:
        self._total_punishment = value

    def add_cirurgies(self, cirurgies: list[Cirurgy]) -> None:
        if not all(isinstance(c, Cirurgy) for c in cirurgies):
            raise TypeError("All items must be instances of Cirurgy")
        self.cirurgies.extend(cirurgies)


class Logic:
    @staticmethod
    def calculate_total_punishment(cirurgies: list[Cirurgy]) -> int:
        # Pt (Punição Total), C (Cirurgia), D (Duração), P (Punição)
        # Ordem: C1, C2, C3, ..., Cn
        # Pt = P2*D1 + P3*(D1+D2) + P4*(D1+D2+D3) + ... + Pn*(D1+D2+D3+...+Dn-1)
        total_punishment = 0
        for i, cirurgy in enumerate(cirurgies[1:], start=1):
            total_punishment += cirurgy.get_punishment(sum(c.duration for c in cirurgies[:i]))
        return total_punishment

    @staticmethod
    def get_order_by_permutation(cirurgies: list[Cirurgy]) -> tuple[list[Cirurgy], int]:
        min_punishment = float("inf")
        best_order = None
        for perm in list(permutations(cirurgies)):
            punishment = Logic.calculate_total_punishment(perm)
            logger.trace(f"Punishment: {punishment}, Permutation: {perm}")
            if punishment < min_punishment:
                min_punishment = punishment
                best_order = perm

        assert best_order is not None
        return list(best_order), min_punishment

    @staticmethod
    def get_best_order(cirurgies: list[Cirurgy]) -> tuple[list[Cirurgy], int]:
        if len(cirurgies) <= 5:
            return Logic.get_order_by_permutation(cirurgies)
        else:
            Global.cirurgies_to_order = cirurgies

            limits = [(0, n) for n in range(len(cirurgies)-1, 0, -1)]

            configs = st.session_state['ord_config']
            num_generations = configs['num_generations']
            num_parents_mating = configs['num_parents_mating']
            sol_per_pop = configs['sol_per_pop']
            num_genes = len(limits)

            # Definindo os intervalos para cada gene
            gene_space = [{'low': low, 'high': high} for low, high in limits]

            # Configurando o GA
            ga_instance = pygad.GA(
                num_generations=num_generations,
                num_parents_mating=num_parents_mating,
                fitness_func=Logic.room_fitness_func,
                sol_per_pop=sol_per_pop,
                num_genes=num_genes,
                gene_space=gene_space,
                random_mutation_min_val=-num_genes,
                random_mutation_max_val=num_genes,
                gene_type=int,
                crossover_type=configs['crossover_type'],  # Usando crossover uniforme
                mutation_type=configs['mutation_type'],  # Usando mutação adaptativa
                mutation_percent_genes=configs['mutation_percent_genes'],  # Faixa de porcentagem de genes a serem mutados
                parent_selection_type=configs['parent_selection_type'],  # Seleção por roleta (Steady State Selection)
                keep_parents=configs['keep_parents'],  # Número de pais mantidos para a próxima geração
            )
            with suppress_stdout():
                ga_instance.run()
            solution, solution_fitness, _ = ga_instance.best_solution()
            return Logic.order_by_indexes(cirurgies, solution), -solution_fitness

    @staticmethod
    def room_fitness_func(ga_instance, solution: list[int], solution_idx):
        ordened = Logic.order_by_indexes(Global.cirurgies_to_order, solution)
        return -Logic.calculate_total_punishment(ordened)

    @staticmethod
    def order_by_indexes(cirurgies: list[Cirurgy], indexes: list[int]) -> list[Cirurgy]:
        print(indexes)
        options = copy.copy(cirurgies)
        ordened = [options.pop(i) for i in indexes] + options
        return ordened

    @staticmethod
    def best_distribution(cirurgies: list[Cirurgy], rooms: "RoomList") -> list[int]:
        # algoritmo genético para encontrar a distribuição de cirurgias que minimiza a punição total
        Global.cirurgies_to_order = cirurgies

        config = st.session_state['dist_config']

        gene_space = [{'low': 0, 'high': len(rooms)} for _ in range(len(cirurgies))]
        num_generations = config['num_generations']
        num_parents_mating = config['num_parents_mating']
        sol_per_pop = config['sol_per_pop']
        num_genes = len(cirurgies)

        st.session_state['counter_gen_container'] = st.empty()
        st.session_state['counter_gen'] = -1

        ga_instance = pygad.GA(
            num_generations=num_generations,
            num_parents_mating=num_parents_mating,
            fitness_func=Logic.roomlist_fitness_func(rooms),
            sol_per_pop=sol_per_pop,
            num_genes=num_genes,
            gene_space=gene_space,
            random_mutation_min_val=-len(rooms),
            random_mutation_max_val=len(rooms),
            gene_type=int,
            crossover_type=config['crossover_type'],  # Usando crossover uniforme
            mutation_type=config['mutation_type'],  # Usando mutação adaptativa
            mutation_percent_genes=config['mutation_percent_genes'],  # Faixa de porcentagem de genes a serem mutados
            parent_selection_type=config['parent_selection_type'],  # Seleção por roleta (Steady State Selection)
            keep_parents=config['keep_parents'],  # Número de pais mantidos para a próxima geração
        )

        with suppress_stdout():
            ga_instance.run()

        solution, solution_fitness, _ = ga_instance.best_solution()
        logger.info(f"Solution: {solution}, Solution fitness: {-solution_fitness}")
        return solution

    @staticmethod
    def roomlist_fitness_func(roomlist):
        def fitness_func(ga_instance, solution, solution_idx):
            logger.trace(f"Solution: {solution}")

            if st.session_state['counter_gen'] != ga_instance.generations_completed:
                st.session_state['counter_gen'] = ga_instance.generations_completed
                st.session_state['counter_gen_container'].text(f"Geração: {ga_instance.generations_completed} / {ga_instance.num_generations}")

            # somar a punição de todas as salas
            total_punishment = 0
            for cirurgy_id, room_id in enumerate(solution):
                roomlist.get_by_id(room_id).add_cirurgies([Cirurgy.get_by_id(cirurgy_id)])

            for room_id in [r.id for r in roomlist.get_all_rooms()]:
                total_punishment += roomlist.get_by_id(room_id).calculate_less_punishment()
                roomlist.get_by_id(room_id).reset_cirurgies()

            return -total_punishment
        return fitness_func


@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


if __name__ == "__main__":
    for _ in range(9):
        n = random.randint(1, 100)
        Cirurgy(duration=n, punishment=100-n)

    roomlist = RoomList([Room() for _ in range(3)])

    with suppress_stdout():
        roomlist.best_rooms_organization()
