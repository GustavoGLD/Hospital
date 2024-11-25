import os
import unittest
from copy import deepcopy
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session

from app import Algorithm, InMemoryCache, Optimizer, Schedule, Surgery, Room, Patient, Team, SurgeryPossibleTeams, \
    Professional
from moonlogger import MoonLogger


def setup_test_session():
    engine = create_engine("sqlite:///:memory:")  # Banco de dados em memória
    SQLModel.metadata.create_all(engine)  # Cria as tabelas
    return Session(engine)


class TestGeneSpace(unittest.TestCase):
    def setUp(self):
        # Mock do cache para simular os métodos
        self.mock_cache = MagicMock()
        self.optimizer = Optimizer(cache=self.mock_cache)

    def test_gene_space_two_rooms_three_teams_four_surgeries(self):
        # Simular dados para 2 salas, 3 equipes e 4 cirurgias
        self.mock_cache.get_table.side_effect = lambda model: {
            Team: list(range(3)),
            Surgery: list(range(4)),
            Room: list(range(2))
        }[model]

        # Executar método
        result = self.optimizer.gene_space()

        # Resultado esperado
        expected = [
            {"low": 0, "high": 2},
            {"low": 0, "high": 1},
            {"low": 0, "high": 1},
            {"low": 0, "high": 1},
        ]

        # Validar o resultado
        self.assertEqual(result, expected)

    def test_gene_space_three_rooms_three_teams_four_surgeries(self):
        # Simular dados para 3 salas, 3 equipes e 4 cirurgias
        self.mock_cache.get_table.side_effect = lambda model: {
            Team: list(range(3)),
            Room: list(range(3)),
            Surgery: list(range(4))
        }[model]

        # Executar método
        result = self.optimizer.gene_space()

        # Resultado esperado
        expected = [
            {"low": 0, "high": 2},
            {"low": 0, "high": 1},
            {"low": 0, "high": 0},
            {"low": 0, "high": 0},
        ]

        # Validar o resultado
        self.assertEqual(result, expected)

    def test_gene_space_five_rooms_ten_teams_twelve_surgeries(self):
        # Simular dados para 5 salas, 10 equipes e 12 cirurgias
        self.mock_cache.get_table.side_effect = lambda model: {
            Team: list(range(10)),
            Surgery: list(range(12)),
            Room: list(range(5))
        }[model]

        # Executar método
        result = self.optimizer.gene_space()

        # Resultado esperado
        expected = [
            {"low": 0, "high": 9},
            {"low": 0, "high": 8},
            {"low": 0, "high": 7},
            {"low": 0, "high": 6},
            {"low": 0, "high": 5},
            {"low": 0, "high": 5},
            {"low": 0, "high": 5},
            {"low": 0, "high": 5},
            {"low": 0, "high": 5},
            {"low": 0, "high": 5},
            {"low": 0, "high": 5},
            {"low": 0, "high": 5},
        ]

        # Validar o resultado
        self.assertEqual(result, expected)


class TestInMemoryCache(unittest.TestCase):
    def setUp(self):
        """Configura os dados de teste no cache antes de cada teste usando uma sessão em memória"""
        self.session = setup_test_session()

        # Criar e adicionar equipes na sessão
        teams = [
            Team(id=1, name="Equipe A"),
            Team(id=2, name="Equipe B")
        ]
        self.session.add_all(teams)

        # Criar e adicionar pacientes na sessão
        patients = [
            Patient(id=1, name="Paciente 1"),
            Patient(id=2, name="Paciente 2")
        ]
        self.session.add_all(patients)

        # Criar e adicionar cirurgias na sessão
        surgeries = [
            Surgery(id=1, name="Cirurgia 1", duration=60, patient_id=1, priority=1),
            Surgery(id=2, name="Cirurgia 2", duration=120, patient_id=2, priority=2)
        ]
        self.session.add_all(surgeries)

        # Criar possíveis equipes para as cirurgias
        surgery_possible_teams = [
            SurgeryPossibleTeams(surgery_id=1, team_id=1),
            SurgeryPossibleTeams(surgery_id=2, team_id=2)
        ]
        self.session.add_all(surgery_possible_teams)

        rooms = [
            Room(id=1, name="Sala 1")
        ]
        self.session.add_all(rooms)

        # Commit para salvar todos os dados na sessão
        self.session.commit()

        self.cache = InMemoryCache(session=self.session)
        self.cache.load_all_data(self.session)

        #logger.debug(f"Teams: {self.cache.load_table(self.session, Team)}")
        #logger.debug(f"Schedule: {self.cache.load_table(self.session, Schedule)}")

        now = datetime.now()

        # Criar uma instância do algoritmo
        self.algorithm = Algorithm(self.cache)
        self.algorithm.surgeries = deepcopy(self.cache.get_table(Surgery))
        self.algorithm.next_vacany = now
        self.algorithm.step = 0
        assert self.algorithm.surgeries

    def test_is_team_busy(self):
        """Teste para verificar se uma equipe está ocupada em um horário específico"""
        now = datetime.now()

        schedules = [
            Schedule(surgery_id=1, start_time=now, room_id=1, team_id=1),
            Schedule(surgery_id=2, start_time=now + timedelta(hours=1), room_id=2, team_id=2)
        ]
        self.session.add_all(schedules)
        self.session.commit()
        self.cache.load_all_data(self.session)

        assert self.cache.get_table(Schedule)

        # Equipe 1 deve estar ocupada no horário do agendamento de Cirurgia 1
        self.assertTrue(self.cache.is_team_busy(1, now))

        # Equipe 1 não deve estar ocupada uma hora após o término de Cirurgia 1
        check_time = now + timedelta(hours=2)
        self.assertFalse(self.cache.is_team_busy(1, check_time))

        # Equipe 2 deve estar ocupada no horário do agendamento de Cirurgia 2
        self.assertTrue(self.cache.is_team_busy(2, now + timedelta(hours=1)))

    def test_get_available_teams(self):
        """Teste para verificar todas as equipes disponíveis em um horário específico"""
        now = datetime.now()

        schedules = [
            Schedule(surgery_id=1, start_time=now, room_id=1, team_id=1),
            Schedule(surgery_id=2, start_time=now + timedelta(hours=1), room_id=2, team_id=2)
        ]
        self.session.add_all(schedules)
        self.session.commit()
        self.cache.load_all_data(self.session)

        # Verifica equipes disponíveis durante o horário da Cirurgia 1
        available_teams = self.cache.get_available_teams(now)
        available_team_ids = [team.id for team in available_teams]
        self.assertIn(2, available_team_ids)
        self.assertNotIn(1, available_team_ids)

        # Verifica equipes disponíveis após o término de todas as cirurgias
        available_teams_after = self.cache.get_available_teams(now + timedelta(hours=3))
        available_team_ids_after = [team.id for team in available_teams_after]
        self.assertIn(1, available_team_ids_after)
        self.assertIn(2, available_team_ids_after)

    def test_process_room(self):
        """Teste para verificar o funcionamento do método process_room"""
        solution = [1, 0]  # Solução com índice para equipes disponíveis
        available_teams = self.cache.get_table(Team)

        # Limpar o cache de 'schedule' para simular um novo processo de agendamento
        self.cache.data['schedule'] = []

        # Executar o método process_room
        self.algorithm.process_room(solution, available_teams)

        # Verificar se a cirurgia foi registrada corretamente
        #self.assertEqual(len(self.cache.get_table(Surgery)), 1)  # Apenas uma cirurgia deve permanecer
        #self.assertEqual(self.algorithm.step, 1)  # O passo deve ter sido incrementado
        schedule = self.cache.get_table(Schedule)
        self.assertEqual(1, len(schedule))

        # Verificar se a cirurgia correta foi registrada em 'registered_surgeries'
        #registered_surgeries = self.cache.get_table(Schedule, [])
        #self.assertEqual(len(registered_surgeries), 1)  # Uma cirurgia deve ter sido registrada
        #self.assertEqual(registered_surgeries[0]['surgery'].id, 1)  # Cirurgia 1 deve ser registrada
        #self.assertEqual(registered_surgeries[0]['team'].id, 1)  # Equipe A deve ser a responsável
        #self.assertEqual(registered_surgeries[0]['room'].id, 1)  # Sala 1 deve ser a utilizada


class TestInMemoryCacheGetById(unittest.TestCase):
    def setUp(self):
        """Configura os dados de teste no cache antes de cada teste usando uma sessão em memória."""
        self.session = setup_test_session()

        # Criar e adicionar equipes na sessão
        teams = [
            Team(id=1, name="Equipe A"),
            Team(id=2, name="Equipe B")
        ]
        self.session.add_all(teams)
        self.session.commit()

        # Inicializa o cache com os dados carregados
        self.cache = InMemoryCache(session=self.session)

    def test_get_by_id_success(self):
        """Teste para verificar se o método retorna o objeto correto para um ID válido."""
        team = self.cache.get_by_id(Team, 1)
        self.assertIsNotNone(team)
        self.assertEqual(team.id, 1)
        self.assertEqual(team.name, "Equipe A")


class TestInMemoryCacheGetSurgeryByTimeAndRoom(unittest.TestCase):
    def setUp(self):
        # Configuração do banco de dados em memória
        self.engine = create_engine("sqlite:///:memory:")
        SQLModel.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        # Adicionando um paciente
        patient = Patient(id=1, name="John Doe")
        self.session.add(patient)

        # Adicionando equipes
        team_1 = Team(id=1, name="Team Alpha")
        team_2 = Team(id=2, name="Team Beta")
        self.session.add_all([team_1, team_2])

        # Adicionando profissionais
        professional_1 = Professional(id=1, name="Dr. Smith", team_id=1)
        professional_2 = Professional(id=2, name="Dr. Johnson", team_id=2)
        self.session.add_all([professional_1, professional_2])

        # Adicionando uma sala
        room = Room(id=1, name="Operating Room 1")
        self.session.add(room)

        # Adicionando cirurgias
        surgery_1 = Surgery(
            id=1,
            name="Appendectomy",
            duration=2,
            priority=1,
            patient_id=1,
        )
        surgery_2 = Surgery(
            id=2,
            name="Cholecystectomy",
            duration=3,
            priority=2,
            patient_id=1,
        )
        self.session.add_all([surgery_1, surgery_2])

        # Adicionando possíveis equipes para as cirurgias
        surgery_team_1 = SurgeryPossibleTeams(surgery_id=1, team_id=1)
        surgery_team_2 = SurgeryPossibleTeams(surgery_id=2, team_id=2)
        self.session.add_all([surgery_team_1, surgery_team_2])

        # Adicionando agendamentos
        schedule_1 = Schedule(
            start_time=datetime(2024, 11, 20, 8, 0),
            surgery_id=1,
            room_id=1,
            team_id=1,
        )
        schedule_2 = Schedule(
            start_time=datetime(2024, 11, 20, 10, 30),
            surgery_id=2,
            room_id=1,
            team_id=2,
        )
        self.session.add_all([schedule_1, schedule_2])
        self.session.commit()

    def test_get_surgery_by_time_and_room(self):
        # Inicializando o cache
        cache = InMemoryCache(self.session)

        # Buscando cirurgia pelo horário e sala
        result = cache.get_surgery_by_time_and_room(
            time=datetime(2024, 11, 20, 8, 0),
            room=cache.get_by_id(Room, 1)
        )

        # Validando o resultado
        assert result is not None
        assert result.id == 1
        assert result.name == "Appendectomy"


class TestGetNextVacancies(unittest.TestCase):
    def setUp(self):
        """Configura um ambiente inicial para os testes."""
        # Mock para o InMemoryCache
        self.cache = InMemoryCache()

        # Configura mock de dados
        self.room1 = Room(id=1, name="Sala 1")
        self.room2 = Room(id=2, name="Sala 2")

        self.schedule1 = Schedule(
            start_time=datetime(2024, 11, 17, 10, 0),
            surgery_id=1,
            room_id=1,
            team_id=1,
        )
        self.schedule2 = Schedule(
            start_time=datetime(2024, 11, 17, 11, 0),
            surgery_id=2,
            room_id=2,
            team_id=2,
        )
        self.surgery1 = Surgery(id=1, name="Cirurgia 1", duration=60, priority=1)
        self.surgery2 = Surgery(id=2, name="Cirurgia 2", duration=30, priority=2)

        # Adiciona dados no cache
        self.cache.data[Room.__tablename__] = [self.room1, self.room2]
        self.cache.data[Schedule.__tablename__] = [self.schedule1, self.schedule2]
        self.cache.data[Surgery.__tablename__] = [self.surgery1, self.surgery2]

    def test_next_vacancies_success(self):
        """Testa se as próximas vagas são retornadas corretamente."""
        vacancies = self.cache.get_next_vacancies()

        expected_vacancies = [
            (self.room1, datetime(2024, 11, 17, 11, 0)),
            (self.room2, datetime(2024, 11, 17, 11, 30)),
        ]
        self.assertEqual(vacancies, expected_vacancies)


class TestNextVacany(unittest.TestCase):

    def setUp(self):
        """Configura o ambiente para os testes."""
        # Mock do InMemoryCache
        self.cache = InMemoryCache()

        # Configura dados no cache
        self.room1 = Room(id=1, name="Sala 1")
        self.room2 = Room(id=2, name="Sala 2")

        self.schedule1 = Schedule(
            start_time=datetime(2024, 11, 17, 10, 0),
            surgery_id=1,
            room_id=1,
            team_id=1,
        )
        self.schedule2 = Schedule(
            start_time=datetime(2024, 11, 17, 11, 0),
            surgery_id=2,
            room_id=2,
            team_id=2,
        )
        self.surgery1 = Surgery(id=1, name="Cirurgia 1", duration=60, priority=1)
        self.surgery2 = Surgery(id=2, name="Cirurgia 2", duration=30, priority=2)

        # Adiciona dados ao cache
        self.cache.data[Room.__tablename__] = [self.room1, self.room2]
        self.cache.data[Schedule.__tablename__] = [self.schedule1, self.schedule2]
        self.cache.data[Surgery.__tablename__] = [self.surgery1, self.surgery2]

        # Instancia a classe Algorithm com o cache
        self.algorithm = Algorithm(self.cache)

    def test_get_next_vacany_basic(self):
        """Testa se o método get_next_vacany retorna a próxima vaga corretamente."""
        expected = datetime(2024, 11, 17, 11, 0)
        next_vacany = self.algorithm.get_next_vacany()
        self.assertEqual(next_vacany, expected)

    def test_get_next_vacany_with_adjustment(self):
        """Testa se o método ajusta corretamente as vagas quando há duplicatas."""
        # Adiciona uma vaga no mesmo horário
        self.cache.data[Schedule.__tablename__].append(
            Schedule(
                start_time=datetime(2024, 11, 17, 10, 0),
                surgery_id=3,
                room_id=1,
                team_id=3,
            )
        )
        logger.info(self.cache.data[Schedule.__tablename__])
        next_vacany = self.algorithm.get_next_vacany()
        expected = datetime(2024, 11, 17, 11, 0)  # A próxima vaga disponível após a duplicata
        self.assertEqual(next_vacany, expected)


class TestAlgorithmExecute(unittest.TestCase):
    def setUp(self):
        """Configura os dados de teste no cache antes de cada teste usando uma sessão em memória."""
        self.session = setup_test_session()

        # Criar e adicionar equipes na sessão
        self.teams = [
            Team(id=1, name="Equipe A"),
            Team(id=2, name="Equipe B")
        ]
        self.session.add_all(self.teams)

        # Criar e adicionar pacientes na sessão
        self.patients = [
            Patient(id=1, name="Paciente 1"),
            Patient(id=2, name="Paciente 2")
        ]
        self.session.add_all(self.patients)

        # Criar e adicionar cirurgias na sessão
        self.surgeries = [
            Surgery(id=1, name="Cirurgia 1", duration=60, patient_id=1, priority=1),
            Surgery(id=2, name="Cirurgia 2", duration=120, patient_id=2, priority=2)
        ]
        self.session.add_all(self.surgeries)

        # Criar possíveis equipes para as cirurgias
        surgery_possible_teams = [
            SurgeryPossibleTeams(surgery_id=1, team_id=1),
            SurgeryPossibleTeams(surgery_id=2, team_id=1),
            SurgeryPossibleTeams(surgery_id=2, team_id=2),
        ]
        self.session.add_all(surgery_possible_teams)

        rooms = [
            Room(id=1, name="Sala 1"),
            Room(id=2, name="Sala 2"),
        ]
        self.session.add_all(rooms)

        # Commit para salvar todos os dados na sessão
        self.session.commit()

        self.cache = InMemoryCache(session=self.session)
        self.cache.load_all_data(self.session)

        now = datetime.now()

        # Criar uma instância do algoritmo
        self.algorithm = Algorithm(self.cache)
        self.algorithm.surgeries = self.cache.get_table(Surgery)
        self.algorithm.next_vacany = now
        self.algorithm.step = 0

    def test_execute_surgeries(self):
        """Teste para verificar se o método execute agenda as cirurgias corretamente."""
        # Definindo uma solução válida que mapeia a execução da cirurgia
        solution = [0, 0]  # Usando índices da equipe disponível para mandar para as cirurgias
        self.algorithm.execute(solution)

        # Verifica que as cirurgias foram agendadas corretamente
        schedules = self.cache.get_table(Schedule)
        self.assertEqual(len(schedules), 2)  # Duas cirurgias devem ser agendadas

        scheduled_surgeries_ids = [schedule.surgery_id for schedule in schedules]
        self.assertIn(1, scheduled_surgeries_ids)  # Cirurgia 1 deve estar agendada
        self.assertIn(2, scheduled_surgeries_ids)  # Cirurgia 2 deve estar agendada


class TestAlgorithmExecuteWithMoreData(unittest.TestCase):
    def setUp(self):
        """Configura um grande conjunto de dados para teste."""
        self.session = setup_test_session()

        # Criar e adicionar equipes na sessão
        self.teams = [
            Team(id=i, name=f"Equipe {i}") for i in range(1, 11)  # 10 equipes
        ]
        self.session.add_all(self.teams)

        # Criar e adicionar pacientes na sessão
        self.patients = [
            Patient(id=i, name=f"Paciente {i}") for i in range(1, 21)  # 20 pacientes
        ]
        self.session.add_all(self.patients)

        # Criar e adicionar cirurgias na sessão
        self.surgeries = [
            Surgery(id=i, name=f"Cirurgia {i}", duration=(i + 1) * 30, patient_id=(i % 20) + 1, priority=i % 5 + 1)
            for i in range(1, 21)  # 20 cirurgias
        ]
        self.session.add_all(self.surgeries)

        # Criar possíveis equipes para as cirurgias
        surgery_possible_teams = [
            SurgeryPossibleTeams(surgery_id=i, team_id=(i % 10) + 1) for i in range(1, 21)
            # Cada cirurgia associada a uma equipe
        ]
        self.session.add_all(surgery_possible_teams)

        # Criar salas
        self.rooms = [
            Room(id=i, name=f"Sala {i}") for i in range(1, 6)  # 5 salas
        ]
        self.session.add_all(self.rooms)

        # Commit para salvar todos os dados na sessão
        self.session.commit()

        self.cache = InMemoryCache(session=self.session)
        self.cache.load_all_data(self.session)

        now = datetime.now()

        # Criar uma instância do algoritmo
        self.algorithm = Algorithm(self.cache)
        self.algorithm.surgeries = self.cache.get_table(Surgery)
        self.algorithm.next_vacany = now
        self.algorithm.step = 0

    def test_execute_with_large_data(self):
        """Teste para verificar se o método execute lida bem com um grande volume de dados."""
        # Definindo uma solução válida que mapeia para as cirurgias
        solution = [1 for i in range(len(self.surgeries))]  # Distribuindo as cirurgias nas 10 equipes

        # Executa o algoritmo
        self.algorithm.execute(solution)

        # Verifica que as cirurgias foram agendadas corretamente
        schedules = self.cache.get_table(Schedule)

        # Esperamos que todas as cirurgias sejam agendadas
        self.assertEqual(len(schedules), 20)  # Todas as 20 cirurgias devem estar agendadas

        scheduled_surgeries_ids = [schedule.surgery_id for schedule in schedules]

        for surgery in self.surgeries:
            self.assertIn(surgery.id, scheduled_surgeries_ids)  # Cada cirurgia deve estar agendada

        # Verifica se todas as equipes registradas possuem agendamentos
        scheduled_teams_ids = {schedule.team_id for schedule in schedules}
        self.assertEqual(len(scheduled_teams_ids), 10)  # Todas as 10 equipes devem estar agendadas


class TestInMemoryCacheCalculatePunishment(unittest.TestCase):
    def setUp(self):
        """Configura o ambiente inicial para os testes com dados simulados."""
        self.session = setup_test_session()
        self.cache = InMemoryCache(session=self.session)

        # Criar e adicionar salas na sessão
        self.room1 = Room(id=1, name="Room 1")
        self.room2 = Room(id=2, name="Room 2")
        self.session.add_all([self.room1, self.room2])

        # Criar e adicionar cirurgias na sessão
        self.surgery1 = Surgery(id=1, name="Surgery 1", duration=30, patient_id=None, priority=1)
        self.surgery2 = Surgery(id=2, name="Surgery 2", duration=60, patient_id=None, priority=2)
        self.surgery3 = Surgery(id=3, name="Surgery 3", duration=45, patient_id=None, priority=1)
        self.session.add_all([self.surgery1, self.surgery2, self.surgery3])

        # Criar e adicionar agendamentos (schedules) na sessão
        now = datetime.now()
        self.schedule1 = Schedule(start_time=now + timedelta(minutes=10), surgery_id=1, room_id=1, team_id=1)
        self.schedule2 = Schedule(start_time=now + timedelta(minutes=20), surgery_id=2, room_id=1, team_id=1)
        self.schedule3 = Schedule(start_time=now + timedelta(minutes=30), surgery_id=3, room_id=2, team_id=2)
        self.session.add_all([self.schedule1, self.schedule2, self.schedule3])
        self.now = now

        # Efetuar o commit para salvar os dados no banco de dados
        self.session.commit()

        # Carregar todos os dados do banco de dados para o cache
        self.cache.load_all_data(self.session)

    def test_calculate_punishment(self):
        """Teste para calcular a punição total de agendamentos."""
        zero_time = self.now
        punishment = self.cache.calculate_punishment(zero_time)

        # Verifica a soma dos tempos de espera em minutos
        expected_punishment = 10 + 20 + 30  # 10, 20 e 30 minutos, respectivamente
        self.assertEqual(punishment, expected_punishment)

    def test_no_schedules(self):
        """Teste com nenhuma cirurgia agendada."""
        self.cache.data[Schedule.__tablename__] = []  # Remove todos os agendamentos
        punishment = self.cache.calculate_punishment(datetime.now())
        self.assertEqual(punishment, 0)

    def test_future_schedules_only(self):
        """Teste se a punição é zero para agendamentos futuros além do zero_time."""
        zero_time = self.now + timedelta(hours=2)  # Um tempo no futuro
        punishment = self.cache.calculate_punishment(zero_time)
        self.assertEqual(punishment, 0)

    def test_empty_solution(self):
        """Teste para verificar se a solução vazia não afeta o cálculo da punição."""
        zero_time = self.now
        punishment = self.cache.calculate_punishment(zero_time)
        expected_punishment = 10 + 20 + 30
        self.assertEqual(punishment, expected_punishment)


class TestOptimizer(unittest.TestCase):
    def setUp(self):
        """Configura um ambiente inicial para os testes."""
        pass

    def test_gene_space(self):
        engine = create_engine(os.getenv("DB_URL"))
        with Session(engine) as session:
            cache = InMemoryCache(session=session)
            optimizer = Optimizer(cache=cache)
            solution = optimizer.run()

            algorithm = Algorithm(cache)
            algorithm.execute(solution)
            algorithm.print_table()
        logger.success(f"Teste concluído com sucesso: {MoonLogger.time_dict}")

    def test_testing(self):
        optimizer = Optimizer({})
        optimizer.fitness_function()

    def test_algorithm(self):
        engine = create_engine(os.getenv("DB_URL"))
        solution = [ 6, 11, 10,  0,  7,  5,  6,  2,  4,  1,  6,  5,  6,  0,  1,  4,  7,
        1,  0,  1,  0,  6,  4,  4,  3,  3,  2,  8,  3]

        try:
            with Session(engine) as session:
                cache = InMemoryCache(session=session)
                algorithm = Algorithm(cache)
                algorithm.execute(solution)
                algorithm.print_table()
        except Exception as e:
            logger.error(f"Erro ao executar o algoritmo. {e}")

        logger.success(f"Teste concluído: {MoonLogger.time_dict}")

    def test_1(self):
        engine = create_engine(os.getenv("DB_URL"))

        with Session(engine) as session:
            cache = InMemoryCache(session=session)
            optimizer = Optimizer(cache=cache)
            logger.success(optimizer.gene_space())