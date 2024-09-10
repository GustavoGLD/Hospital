import random
from collections import defaultdict

import pandas as pd
import streamlit
from loguru import logger
from tabulate import tabulate
from typing import List, Optional
import pygad
import streamlit as st
import time

if 'num_generations' not in st.session_state:
    st.session_state['num_generations'] = 100

if 'sol_per_pop' not in st.session_state:
    st.session_state['sol_per_pop'] = 10

if 'num_parents_mating' not in st.session_state:
    st.session_state['num_parents_mating'] = 9

if 'crossover_type' not in st.session_state:
    st.session_state['crossover_type'] = "single_point"

if 'mutation_type' not in st.session_state:
    st.session_state['mutation_type'] = "random"

if 'mutation_percent_genes' not in st.session_state:
    st.session_state['mutation_percent_genes'] = [5, 4]

if 'parent_selection_type' not in st.session_state:
    st.session_state['parent_selection_type'] = "sss"

if 'keep_parents' not in st.session_state:
    st.session_state['keep_parents'] = -1


class Equipe:
    all_equipes: dict[str, "Equipe"] = {}

    def __init__(self, nome: str):
        self.nome = nome
        self.possible_cirurgies: List["Cirurgia"] = []
        self.cirurgias: List[Cirurgia] = []
        Equipe.all_equipes[nome] = self

    def esta_ocupada(self, no_tempo: int) -> bool:
        r = any(
            cirurgia.tempo_inicio <= no_tempo < cirurgia.tempo_inicio + cirurgia.duracao for cirurgia in self.cirurgias
        )
        return r

    def adicionar_cirurgia(self, cirurgia: "Cirurgia"):
        self.cirurgias.append(cirurgia)

    def __repr__(self):
        return f"{self.nome}"


class Sala:
    all_salas: dict[str, "Sala"] = {}

    def __init__(self, nome: str):
        self.nome = nome
        self.cirurgias: List[Cirurgia] = []
        Sala.all_salas[nome] = self

    def esta_ocupada(self, no_tempo: int) -> bool:
        r = any(
            cirurgia.tempo_inicio <= no_tempo < cirurgia.tempo_inicio + cirurgia.duracao for cirurgia in self.cirurgias)
        return r

    def proxima_desocupacao(self) -> Optional[int]:
        if not self.cirurgias:
            return None
        return max(cirurgia.tempo_inicio + cirurgia.duracao for cirurgia in self.cirurgias)

    def adicionar_cirurgia(self, cirurgia: "Cirurgia"):
        self.cirurgias.append(cirurgia)

    def __repr__(self):
        return f"Sala({self.nome})"


class Cirurgia:
    def __init__(self, nome: str, duracao: int, punicao: int, equipes_possiveis: list[str]):
        self.nome = nome
        self.duracao = duracao
        self.punicao = punicao
        self.equipe: Optional[Equipe] = None
        self.equipes_possiveis = equipes_possiveis
        self.tempo_inicio: Optional[int] = None
        self.sala: Optional[Sala] = None

    def __repr__(self):
        return f"Cirurgia({self.nome}, {self.duracao})"


def proxima_cirurgia(cirurgias: List[Cirurgia], equipe: Equipe):
    for cirurgia in sorted(cirurgias, key=lambda c: c.duracao / c.punicao):
        for equipe_possivel in cirurgia.equipes_possiveis:
            if int(equipe_possivel) == int(equipe.id):
                return cirurgia


class Mediador:
    def __init__(self, equipes: List[Equipe] = None, salas: List[Sala] = None):
        self.cirurgias_registradas: List[Cirurgia] = []
        self.equipes: List[Equipe] = equipes or []
        self.salas: List[Sala] = salas or []

    def registrar_cirurgia(self, cirurgia: Cirurgia, equipe: Equipe, sala: Sala, no_tempo: int):
        cirurgia.tempo_inicio = no_tempo
        cirurgia.equipe = equipe
        cirurgia.sala = sala
        equipe.adicionar_cirurgia(cirurgia)
        sala.adicionar_cirurgia(cirurgia)
        self.cirurgias_registradas.append(cirurgia)

    def descobrir_cirurgia(self, no_tempo: int, sala: Sala) -> Optional[Cirurgia]:
        for cirurgia in sala.cirurgias:
            if cirurgia.tempo_inicio <= no_tempo < cirurgia.tempo_inicio + cirurgia.duracao:
                return cirurgia
        return None

    def calcular_punicao(self) -> dict:
        assert self.salas and self.cirurgias_registradas and self.equipes, "Não há salas, cirurgias ou equipes"

        punicoes_por_sala = {}
        punicao_total_geral = 0

        for sala in self.salas:
            punicao_total = 0
            for cirurgia in sala.cirurgias:
                if cirurgia.tempo_inicio is not None:
                    tempo_espera = cirurgia.tempo_inicio
                    if tempo_espera > 0:
                        punicao_total += tempo_espera * cirurgia.punicao

            punicoes_por_sala[sala.nome] = punicao_total
            punicao_total_geral += punicao_total

        return {"punicoes_por_sala": punicoes_por_sala, "punicao_total_geral": punicao_total_geral}

    def pegar_cirurgias_nao_registradas(self) -> List[Cirurgia]:
        return [c for c in self.cirurgias_registradas if c.tempo_inicio is None]

    def pegar_equipes_livres(self, no_tempo: int) -> List[Equipe]:
        assert self.equipes, "Não há equipes"
        r = [equipe for equipe in self.equipes if not equipe.esta_ocupada(no_tempo)]
        return r

    def limpar_registros(self):
        self.cirurgias_registradas.clear()
        for equipe in self.equipes:
            equipe.cirurgias.clear()
        for sala in self.salas:
            sala.cirurgias.clear()


def criar_equipamentos_e_salas(mediador: Mediador, num_equipas: int, num_salas: int):
    equipes = [Equipe(f"Equipe {chr(65 + i)}") for i in range(num_equipas)]
    salas = [Sala(f"Sala {i + 1}") for i in range(num_salas)]

    mediador.equipes.extend(equipes)
    mediador.salas.extend(salas)


def criar_cirurgias(num_cirurgias: int) -> List[Cirurgia]:
    return [Cirurgia(f"Cirurgia {i + 1}", random.randint(10, 90), random.randint(1, 50)) for i in range(num_cirurgias)]


def descobrir_cirurgias_das_salas(mediador: Mediador, proximo_tempo: int) -> dict:
    return {
        sala.nome: (
            f'{mediador.descobrir_cirurgia(proximo_tempo, sala).equipe} - {mediador.descobrir_cirurgia(proximo_tempo, sala).nome}'
            if mediador.descobrir_cirurgia(proximo_tempo, sala) else "")
        for sala in mediador.salas
    }


def embaralharLista(lista):
    lista_embaralhada = lista[:]
    random.shuffle(lista_embaralhada)
    return lista_embaralhada


class Algoritmo:
    def __init__(self, mediador: Mediador, cirurgias: List[Cirurgia]):
        self.ordering: List[str] = []
        self.mediador = mediador
        self.cirurgias = cirurgias
        self.proximo_tempo = 0
        self.dados_tabela = []
        self.step = 0

    def descobrir_cirurgias_das_salas(self) -> dict:
        """Retorna um dicionário com as cirurgias alocadas em cada sala no tempo atual. Cada entrada do dicionário
        contém o nome da equipe e o nome da cirurgia."""
        return {
            sala.nome: (
                f'{self.mediador.descobrir_cirurgia(self.proximo_tempo, sala).equipe} - {self.mediador.descobrir_cirurgia(self.proximo_tempo, sala).nome}'
                if self.mediador.descobrir_cirurgia(self.proximo_tempo, sala) else "")
            for sala in self.mediador.salas
        }

    def registrar_cirurgia(self, cirurgia: Cirurgia, equipe: Equipe, sala: Sala):
        """Registra uma cirurgia em uma sala específica com uma equipe específica, removendo a cirurgia da lista
        pendente e logando a ação."""
        #logger.critical(cirurgia)
        self.mediador.registrar_cirurgia(cirurgia, equipe, sala, self.proximo_tempo)
        #logger.info(f"Registrando {cirurgia} com {equipe} na {sala} às {self.proximo_tempo} minutos")
        self.cirurgias.remove(cirurgia)

    def processar_salas(self, equipes_livres: List[Equipe], ordering: List[int], step: int):
        for sala in self.mediador.salas:
            if not sala.esta_ocupada(self.proximo_tempo) and self.cirurgias and equipes_livres:
                try:
                    equipe = equipes_livres[ordering[self.step]]
                except IndexError as e:
                    logger.error(f"IndexError: {ordering=}, {self.step=}, {equipes_livres=}")
                    for i, o in enumerate(equipes_livres):
                        logger.error(f"{i}, {o.nome}")
                    for equipe in self.mediador.equipes:
                        logger.error(f"{equipe.cirurgias}")
                    raise e
                cirurgia = proxima_cirurgia(self.cirurgias, equipe)

                i = 0
                while not cirurgia:
                    equipe = equipes_livres[i]
                    cirurgia = proxima_cirurgia(self.cirurgias, equipe)
                    i += 1

                if cirurgia:
                    self.registrar_cirurgia(cirurgia, equipe, sala)
                    equipes_livres.remove(equipe)
                    self.step += 1
                    #step nao ta avançando. "proximo_tempo" sempre volta para o mesmo lugar

                #logger.info(f"Step: {self.step}; Proximo tempo: {self.proximo_tempo}; Tempos: {[sala.proxima_desocupacao() for sala in self.mediador.salas if sala.proxima_desocupacao() is not None]}")

    def calcular_proxima_desocupacao(self) -> int:
        # Obter e ordenar a lista de tempos de desocupação
        desocupacoes = sorted(
            [sala.proxima_desocupacao() for sala in self.mediador.salas if sala.proxima_desocupacao() is not None]
        )
        assert desocupacoes, "Não há desocupações disponíveis"

        # Se self.proximo_tempo estiver na lista, ajusta valores repetidos
        if self.proximo_tempo in desocupacoes:
            adjusted_desocupacoes = []
            previous_value = None

            for i, val in enumerate(desocupacoes):
                if i > 0 and val == previous_value:
                    # Ajustar o valor repetido incrementando em 1
                    val = adjusted_desocupacoes[-1] + 1
                adjusted_desocupacoes.append(val)
                previous_value = val

            desocupacoes = adjusted_desocupacoes

        # Verificar se o self.proximo_tempo está na lista e pegar o próximo valor
        if self.proximo_tempo in desocupacoes:
            index = desocupacoes.index(self.proximo_tempo)
            # Retornar o próximo valor na lista, se disponível
            if index + 1 < len(desocupacoes):
                return desocupacoes[index + 1]

        # Se self.proximo_tempo não estiver na lista ou não houver um próximo valor, retornar o menor valor
        #logger.debug(f"Desocupações: {desocupacoes}")
        return desocupacoes[0] if desocupacoes else self.proximo_tempo + 1

    def conferir_ordering(self, ordering: List[int]):
        assert len(ordering) == len(self.cirurgias), f"{len(ordering)=}, {len(self.cirurgias)=}"

    def executar(self, ordering: List[int]):
        self.conferir_ordering(ordering)
        self.mediador.limpar_registros()
        step = 0
        while self.cirurgias:
            equipes_livres = self.mediador.pegar_equipes_livres(no_tempo=self.proximo_tempo)
            assert equipes_livres or step != 0, f"Sem equipes. {equipes_livres=}, {step=}"

            if equipes_livres:
                self.processar_salas(equipes_livres, ordering, step)
                self.dados_tabela.append({
                    "Tempo (min)": self.proximo_tempo,
                    **self.descobrir_cirurgias_das_salas()
                })

            self.proximo_tempo = self.calcular_proxima_desocupacao()
            #logger.debug(f"Próxima desocupação em: {self.proximo_tempo} minutos; Step: {step};")
            step += 1

            if self.proximo_tempo > 5000:
                raise Exception("Tempo limite excedido")

    def imprimir_tabela(self):
        df = pd.DataFrame(self.dados_tabela)
        print(tabulate(df, headers="keys", tablefmt="grid"))
        #time.sleep(1)
        #print('\n' * 5)


def main1():
    mediador = Mediador()
    criar_equipamentos_e_salas(mediador, num_equipas=4, num_salas=3)
    cirurgias_iniciais = criar_cirurgias(num_cirurgias=10)
    ordering = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]

    while True:
        mediador.cirurgias_registradas.clear()
        for equipe in mediador.equipes:
            equipe.cirurgias.clear()
        for sala in mediador.salas:
            sala.cirurgias.clear()

        cirurgias = cirurgias_iniciais[:]
        algoritmo = Algoritmo(mediador, cirurgias)
        algoritmo.executar(ordering)
        print(mediador.calcular_punicao())
        #logger.success("Reiniciando o processo...")


class AnalisadorModel:
    def __init__(self):
        self._historico: list[dict[str, float]] = []

    def analise(self, punicao: int, geracao: int):
        if not self._historico or punicao < min(self._historico, key=lambda x: x["punicao"])["punicao"]:
            self._historico.append({"punicao": punicao, "geracao": geracao})



class AnalisadorView:
    def __init__(self, model: AnalisadorModel):
        pass


class AnalisadorController:
    def __init__(self, model: AnalisadorModel, view: AnalisadorView):
        pass

class Otimizador:
    def __init__(self, mediador: Mediador, cirurgias: List[Cirurgia]):
        self.mediador = mediador
        self.analisador = AnalisadorModel()

        cirurgias.sort(key=lambda cirurgia: cirurgia.duracao / cirurgia.punicao)
        self.cirurgias = cirurgias[:]

    def gene_space(self):
        array = []
        high = len(self.mediador.equipes) - 1  # self.n_equipes - 1
        decrementos = len(self.mediador.salas) - 1  # self.n_salas - 1

        for i in range(len(self.cirurgias)):
            array.append({"low": 0, "high": high})

            if i < decrementos:
                high -= 1

        return array

    def fitness_func(self):
        def func(ga_instance, solution, solution_idx):
            self.mediador.cirurgias_registradas.clear()
            for equipe in self.mediador.equipes:
                equipe.cirurgias.clear()
            for sala in self.mediador.salas:
                sala.cirurgias.clear()

            algoritmo = Algoritmo(self.mediador, self.cirurgias.copy())
            try:
                algoritmo.executar(solution)
            except Exception as e:
                logger.error(f"Erro ao executar o algoritmo: {e}")
                return -float("inf")

            # Calcular a punição total
            total_punicao = self.mediador.calcular_punicao()["punicao_total_geral"]
            self.analisador.analise(total_punicao, ga_instance.generations_completed)

            # A função de aptidão retorna o negativo da punição para que o GA minimize a punição
            return -total_punicao

        return func

    def otimizar_punicao(self):
        # Configuração dos parâmetros do GA
        gene_space_array = self.gene_space()

        ga_instance = pygad.GA(
            num_generations=st.session_state["num_generations"],
            num_parents_mating=st.session_state["num_parents_mating"],
            sol_per_pop=st.session_state["sol_per_pop"],
            num_genes=len(self.cirurgias),
            gene_space=gene_space_array,
            fitness_func=self.fitness_func(),
            random_mutation_min_val=-3,
            random_mutation_max_val=3,
            #mutation_percent_genes=st.session_state["mutation_percent_genes"],
            mutation_type=st.session_state["mutation_type"],
            gene_type=int,
            parent_selection_type=st.session_state["parent_selection_type"],
            keep_parents=st.session_state["keep_parents"],
            crossover_type=st.session_state["crossover_type"]
        )

        # Executar o GA
        ga_instance.run()

        #st.dataframe(self.analisador._historico)

        # Obter a melhor solução
        solution, solution_fitness, _ = ga_instance.best_solution()
        return solution, -solution_fitness


class Export:
    def __init__(self, algorithm: Algoritmo):
        self.algorithm = algorithm

    def by_teams(self):
        r = defaultdict(list)
        for cirurg in self.algorithm.mediador.cirurgias_registradas:
            r[cirurg.equipe.nome].append(cirurg.nome)
        return {cirurgia.equipe.nome: cirurgia.nome for cirurgia in self.algorithm.mediador.cirurgias_registradas}


def testar_otimizador():
    n_salas = 5
    n_equipes = 4
    n_cirurgias = 10

    logger.remove()

    mediador = Mediador()
    criar_equipamentos_e_salas(mediador, num_equipas=n_equipes, num_salas=n_salas)
    cirurgias = criar_cirurgias(n_cirurgias)

    otimizador = Otimizador(mediador, cirurgias)
    melhor_solucao, menor_punicao = otimizador.otimizar_punicao()

    print(f"Melhor Solução: {melhor_solucao}")
    print(f"Menor Punição: {menor_punicao}")


import streamlit as st


def testar_algoritmo():
    print('iniciando')
    from app import Data

    if not Data.get_cirurgies():
        filepath = "data/data_teste_2.json"
        print('carregando arquivo')
        Data.load_json(filepath)

    mediador = Mediador(equipes=Data.get_teams(), salas=Data.get_rooms())

    t = st.text_input("Digite a solução: ")
    solucao = None
    if t and st.button("Executar"):
        solucao = eval(t)
        st.write(f"{solucao=} {type(solucao)=}")
        assert isinstance(solucao, list) and all(isinstance(i, int) for i in solucao), "A solução deve ser uma lista de inteiros"

        print('criando algoritmo')
        algoritmo = Algoritmo(mediador, Data.get_cirurgies())
        print('executando')
        algoritmo.executar(solucao)
        print('calculando punição')
        algoritmo.imprimir_tabela()
        print(mediador.calcular_punicao())
        st.dataframe(algoritmo.dados_tabela)


if __name__ == "__main__":
    # Dicionário de opções
    opcoes = {
        "Testar Algoritmo": testar_algoritmo,
        "Testar Otimizador": testar_otimizador,
    }

    opcao = st.selectbox("Escolha uma opção:", list(opcoes.keys()))
    opcoes[opcao]()

    # [10, 10, 2, 5, 7, 8, 1, 0, 8, 8, 2, 6, 3, 1, 9, 6, 2, 5, 3, 3]
