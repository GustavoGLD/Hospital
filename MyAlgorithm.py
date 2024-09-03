import os
import random
import sys
import time
from collections import defaultdict
from contextlib import contextmanager

import pandas as pd
import pygad
import streamlit as st
from loguru import logger


@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


class Cirurgy__:
    def __init__(self):
        self.possible_teams = None


class Room__:
    def __init__(self):
        pass


class Cirurgy(Cirurgy__):
    def __init__(self, duration: int, punishment: int):
        super().__init__()
        self.duration = duration
        self.punishment = punishment
        self.team = None

    def get_punishment(self, delay: int) -> int:
        return self.punishment * delay

    def __repr__(self):
        return f"Cirurgy({self.duration=}, {self.punishment=})"


class Room(Room__):
    def __init__(self):
        super().__init__()


class Distributing:
    def __init__(self, rooms: list[Room__], cirurgies: list[Cirurgy__]):
        self.rooms = rooms
        self.cirurgies = cirurgies
        self.gene_space, self.num_genes = self.genes()
        self.best_punishment = float('inf')
        self.best_order = None
        self.best_distr = None
        self.data = None

    def genes(self) -> tuple[list[dict[str, int]], int]:
        limits = [{'low': 0, 'high': len(self.rooms)} for _ in range(len(self.cirurgies))]
        return limits, len(limits)

    def create_ga_intance(self):
        guess, _ = GuessDistributing(self.rooms, self.cirurgies).run()
        st.write(f'{guess=}')
        return pygad.GA(
            num_generations=st.session_state['dist_num_generations'],
            num_parents_mating=st.session_state['dist_num_parents_mating'],
            fitness_func=self.fitness_func(),
            sol_per_pop=st.session_state['dist_sol_per_pop'],
            num_genes=self.num_genes,
            gene_space=self.gene_space,
            random_mutation_min_val=-len(self.rooms),
            random_mutation_max_val=len(self.rooms),
            gene_type=int,
            crossover_type=st.session_state['dist_crossover_type'],
            mutation_type=st.session_state['dist_mutation_type'],
            mutation_percent_genes=st.session_state['dist_mutation_percent_genes'],
            parent_selection_type=st.session_state['dist_parent_selection_type'],
            keep_parents=st.session_state['dist_keep_parents'],
            initial_population=[guess for _ in range(st.session_state['dist_sol_per_pop'])]
        )

    def get_guess(self):
        importance_cirg = sorted(tuple(enumerate(self.cirurgies)), key=lambda x: x[1].duration / x[1].punishment)
        guess = defaultdict(int)
        for i, cirurgy in enumerate(importance_cirg):
            id, cirurgy = cirurgy
            guess[id] = i % len(self.rooms)

        distr_guess = [value for key, value in sorted(guess.items(), key=lambda x: x[0])]

        return distr_guess

    def fitness_func(self):
        def fitness(ga_instance, solution, solution_idx):
            logger.trace(f"Solution: {solution}")
            if st.session_state['counter_gen'] != ga_instance.generations_completed:
                st.session_state['counter_gen'] = ga_instance.generations_completed
                st.session_state['counter_gen_container'].text(f"Geração: {ga_instance.generations_completed} / {ga_instance.num_generations}")

            ordering = Ordering(self.cirurgies, solution)
            ordering.run()
            if ordering.best_punishment < self.best_punishment:
                self.best_punishment = ordering.best_punishment
                self.best_order = ordering.best_ord
                self.best_distr = solution
                self.data = ordering.data
                st.info(f"Melhor solução: {solution} - Indice: {ga_instance.generations_completed} - Punição: {self.best_punishment}")
            return -ordering.best_punishment
        return fitness

    def run(self):
        ga_instance = self.create_ga_intance()
        with suppress_stdout():
            ga_instance.run()
        return self.best_order, self.best_punishment


class GuessDistributing:
    def __init__(self, rooms: list[Room__], cirurgies: list[Cirurgy__]):
        self.rooms = rooms
        self.cirurgies = cirurgies
        self.gene_space, self.num_genes = self.genes()
        self.best_punishment = float('inf')
        self.best_order = None
        self.best_distr = None
        self.data = None

    def genes(self) -> tuple[list[dict[str, int]], int]:
        limits = [{'low': 0, 'high': len(self.rooms)} for _ in range(len(self.cirurgies))]
        return limits, len(limits)

    def get_guess(self):
        importance_cirg = sorted(tuple(enumerate(self.cirurgies)), key=lambda x: x[1].duration / x[1].punishment)
        guess = defaultdict(int)
        for i, cirurgy in enumerate(importance_cirg):
            id, cirurgy = cirurgy
            guess[id] = i % len(self.rooms)

        distr_guess = [value for key, value in sorted(guess.items(), key=lambda x: x[0])]

        return distr_guess

    def create_ga_intance(self):
        guess = self.get_guess()
        distances = [(limit['high'] - limit['low']) for limit in self.gene_space]
        average_distance = sum(distances) / len(distances) if distances else 0

        return pygad.GA(
            num_generations=self.num_genes * 10,
            num_parents_mating=5,
            fitness_func=self.fitness_func(),
            sol_per_pop=300,
            num_genes=self.num_genes,
            gene_space=self.gene_space,
            random_mutation_min_val=-len(self.rooms)//3 if len(self.rooms) > 3 else -1,
            random_mutation_max_val=len(self.rooms)//3 if len(self.rooms) > 3 else 1,
            gene_type=int,
            crossover_type=st.session_state['dist_crossover_type'],
            mutation_type=st.session_state['dist_mutation_type'],
            mutation_percent_genes=(30, 10),  # st.session_state['dist_mutation_percent_genes'],
            parent_selection_type=st.session_state['dist_parent_selection_type'],
            keep_parents=st.session_state['dist_keep_parents'],
            initial_population=[guess for _ in range(st.session_state['dist_sol_per_pop'])]
        )

    def fitness_func(self):
        def fitness(ga_instance, solution, solution_idx):
            logger.trace(f"Solution: {solution}")
            if st.session_state['counter_gen'] != ga_instance.generations_completed:
                st.session_state['counter_gen'] = ga_instance.generations_completed
                st.session_state['counter_gen_container'].text(
                    f"Geração: {ga_instance.generations_completed} / {ga_instance.num_generations}")

            ordering = Ordering(self.cirurgies, solution)
            ordering.run_guess()
            if ordering.best_punishment < self.best_punishment:
                self.best_punishment = ordering.best_punishment
                self.best_order = self.best_order
                self.best_distr = solution
                self.data = ordering.data
                st.info(
                    f"Melhor solução: {solution} - Indice: {ga_instance.generations_completed} - Punição: {self.best_punishment}")
            return -ordering.best_punishment

        return fitness

    def run(self):
        ga_instance = self.create_ga_intance()
        with suppress_stdout():
            ga_instance.run()
        return self.best_distr, self.best_punishment


class Ordering:
    def __init__(self, cirurgies: list[Cirurgy__], distribuitions: list[int]):
        self.cirurgies = cirurgies
        self.distr = distribuitions
        self.best_ord = None
        self.best_punishment = float('inf')
        self.gene_space, self.num_genes = self.genes()
        self.data = None
        #logger.info(f"{distribuitions=}")

    def genes(self) -> tuple[list[dict[str, int]], int]:
        rooms_coutings = defaultdict(int)
        limits: list[dict[str, int]] = []

        for room_id in self.distr:
            rooms_coutings[room_id] += 1

        for room_id in self.distr:
            rooms_coutings[room_id] -= 1
            limits.append({'low': 0, 'high': rooms_coutings[room_id]})

        return limits, len(limits)

    def create_ga_intance(self):
        guess = self.get_guess()
        return pygad.GA(
                num_generations=st.session_state['ord_num_generations'],
                num_parents_mating=st.session_state['ord_num_parents_mating'],
                fitness_func=self.room_fitness_func(self.distr),
                sol_per_pop=st.session_state['ord_sol_per_pop'],
                num_genes=self.num_genes,
                gene_space=self.gene_space,
                random_mutation_min_val=-self.num_genes,
                random_mutation_max_val=self.num_genes,
                gene_type=int,
                crossover_type=st.session_state['ord_crossover_type'],  # Usando crossover uniforme
                mutation_type=st.session_state['ord_mutation_type'],  # Usando mutação adaptativa
                mutation_percent_genes=sorted(st.session_state['ord_mutation_percent_genes'], reverse=True),
                # Faixa de porcentagem de genes a serem mutados
                parent_selection_type=st.session_state['ord_parent_selection_type'],  # Seleção de pais
                keep_parents=st.session_state['ord_keep_parents'],  # Número de pais mantidos
                initial_population=[guess for _ in range(st.session_state['ord_sol_per_pop'])]
            )

    def get_guess(self):
        rooms = defaultdict(list)
        for cirurgy_id, room_id in enumerate(self.distr):
            rooms[room_id].append((self.cirurgies[cirurgy_id], cirurgy_id))

        print(rooms)
        rooms_sorted = defaultdict(list)

        for room_id, cirurgies in rooms.items():
            room = sorted(cirurgies, key=lambda x: x[0].duration / x[0].punishment)
            for i, cirurgy in enumerate(room):
                rooms_sorted[room_id].append((cirurgy[0], cirurgy[1], i))

        ord_guess = [None] * len(self.distr)
        for room_id, cirurgies in rooms_sorted.items():
            room = sorted(cirurgies, key=lambda x: x[1])
            indexes_to_choice = list(range(len(cirurgies)))
            for i, cirurgy in enumerate(room):
                index = indexes_to_choice.index(cirurgy[2])
                indexes_to_choice.pop(index)
                ord_guess[cirurgy[1]] = index

        return ord_guess

    def room_fitness_func(self, distr: list[int]):
        def fitness(ga_instance, solution, solution_idx):
            order = solution
            rooms = defaultdict(list)

            # Organize cirurgias por salas e ordem
            teams = defaultdict(list)
            for cirurgy_id, room_id in enumerate(distr):
                rooms[room_id].append((self.cirurgies[cirurgy_id], order[cirurgy_id]))
                teams[min(self.cirurgies[cirurgy_id].possible_teams, key=lambda x: len(teams[x]))].append(self.cirurgies[cirurgy_id])

            total_punishment = 0

            # Ordene cirurgias por sala e calcule a punição total
            data = defaultdict(list)
            for room_id, cirurgies in rooms.items():
                cirurgies.sort(key=lambda x: x[1])
                sorted_cirurgies = [cirurgy[0] for cirurgy in cirurgies]
                data[room_id] = sorted_cirurgies
                total_punishment += FinalAlgorithm.calculate_total_punishment(sorted_cirurgies)

            if total_punishment < self.best_punishment:
                self.best_punishment = total_punishment
                self.best_ord = solution
                self.data = data
                for team_id, crgs in teams.items():
                    for cirg in crgs:
                        cirg.team = team_id

            return -total_punishment

        return fitness

    def get_best_order(self) -> tuple[list[int], int]:
        ga_instance = self.create_ga_intance()
        with suppress_stdout():
            ga_instance.run()
        best_solution, best_solution_fitness, _ = ga_instance.best_solution()

        return best_solution, -best_solution_fitness

    def run(self):
        #(self.best_solution, self.best_punishment) = self.get_best_order()
        return self.get_best_order()

    def run_guess(self):
        self.room_fitness_func(self.distr)(None, self.get_guess(), 0)


class SettingTeams:
    pass


class FinalAlgorithm:
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
    def get_best_order(cirurgies: list[Cirurgy]) -> list[Cirurgy]:
        for cirurgy in cirurgies:
            cirurgy.best_room = 1
        return cirurgies


if __name__ == '__main__':
    if "random_df" not in st.session_state:
        ns = [random.randint(1, 99) for _ in range(120)]
        st.session_state.random_df = pd.DataFrame(
            {
                "duration": ns,
                "punishment": [100-n for n in ns]
            }
        )


    def gerar():
        ns = [random.randint(1, 99) for _ in range(st.session_state['q'])]
        st.session_state.random_df = pd.DataFrame(
            {
                "duration": ns,
                "punishment": [100 - n for n in ns]
            }
        )


    q = st.number_input("Número de cirurgias", min_value=1, max_value=500, value=120, step=1, on_change=gerar, key="q")

    edited_df = st.data_editor(
        st.session_state.random_df,
        column_config={
            "duration": st.column_config.NumberColumn(
                "Duração (minutos)", min_value=0, max_value=100, step=1
            ),
            "punishment": st.column_config.NumberColumn(
                "Punição por atraso", min_value=0, max_value=100, step=1
            )
        },
        num_rows="dynamic",
        use_container_width=True,
    )

    num_rooms = st.number_input("Número de salas", min_value=1, max_value=150, value=30, step=1)

    if 'counter_gen_container' not in st.session_state:
        st.session_state['counter_gen_container'] = st.empty()

    if st.button("Organizar salas"):
        cirurgies = []
        for index, row in edited_df.iterrows():
            cirurgies.append(Cirurgy(duration=int(row["duration"]), punishment=int(row["punishment"])))

        rooms = [Room() for _ in range(num_rooms)]

        inicio = time.time()
        with st.spinner("Organizando salas..."):
            with suppress_stdout():
                distributing = Distributing(rooms, cirurgies)
                distributing.run()

        st.write(f"Tempo de execução: {time.time() - inicio:.2f}s")
        logger.critical(f"Tempo de execução: {time.time() - inicio:.2f}s")

        #st.write(f"Melhor solução: {distributing.data}")

        st.write("Organização das salas:")
        for i, room in distributing.data.items():
            st.write(f"Sala {i}: {room}")
