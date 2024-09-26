import os
import sys
from inspect import getsourcefile

current_dir = os.path.dirname(os.path.abspath(getsourcefile(lambda: 0)))
sys.path.insert(0, current_dir[:current_dir.rfind(os.path.sep)])

import unittest
from src.backend.repositories.cirurgy_repository import CirurgyRepository
from src.backend.repositories.professional_repository import ProfessionalRepository
from src.backend.repositories.room_repository import RoomRepository
from src.backend.repositories.team_repository import TeamRepository
from src.backend.entities import CirurgyEntity, ProfessionalEntity, RoomEntity, TeamEntity
from src.backend.models import CirurgyModel, ProfessionalModel, RoomModel, TeamModel
from src.backend.objects import NameObj, IdObj, PunishmentObj, DurationObj, TimeObj


class TestRepositories(unittest.TestCase):

    def setUp(self):
        # Dados de exemplo
        self.cirurgy_model_1 = CirurgyModel(
            penalty=PunishmentObj(value=50),
            duration=DurationObj(hours=1, minutes=0),  # Você precisa fornecer a duração adequada
            possible_teams_ids=[IdObj(value=1)],  # Fornecendo IDs de exemplo
            possible_rooms_ids=[IdObj(value=2)],  # Fornecendo IDs de exemplo
            team_id=IdObj(value=1),  # Adicionando um ID de equipe
            room_id=IdObj(value=2),  # Adicionando um ID de sala
            time=TimeObj(start=1200),  # Exemplo de tempo
            name=NameObj(value="Cirurgy A")
        )
        self.cirurgy_model_2 = CirurgyModel(
            penalty=PunishmentObj(value=75),
            duration=DurationObj(hours=2, minutes=30),
            possible_teams_ids=[IdObj(value=3)],
            possible_rooms_ids=[IdObj(value=4)],
            team_id=IdObj(value=3),
            room_id=IdObj(value=4),
            time=TimeObj(start=1000),
            name=NameObj(value="Cirurgy B")
        )

        self.team_model_1 = TeamModel(name=NameObj(value="Team X"))
        self.team_model_2 = TeamModel(name=NameObj(value="Team Y"))
        self.professional_model_1 = ProfessionalModel(name=NameObj(value="Professional 1"))
        self.professional_model_2 = ProfessionalModel(name=NameObj(value="Professional 2"))
        self.room_model_1 = RoomModel(name=NameObj(value="Room 1"))
        self.room_model_2 = RoomModel(name=NameObj(value="Room 2"))

        # Instanciando entidades
        self.cirurgy_entity_1 = CirurgyEntity(self.cirurgy_model_1)
        self.cirurgy_entity_2 = CirurgyEntity(self.cirurgy_model_2)
        self.team_entity_1 = TeamEntity(self.team_model_1)
        self.team_entity_2 = TeamEntity(self.team_model_2)
        self.professional_entity_1 = ProfessionalEntity(self.professional_model_1)
        self.professional_entity_2 = ProfessionalEntity(self.professional_model_2)
        self.room_entity_1 = RoomEntity(self.room_model_1)
        self.room_entity_2 = RoomEntity(self.room_model_2)

        # Criando repositórios
        self.cirurgy_repository = CirurgyRepository([self.cirurgy_entity_1, self.cirurgy_entity_2])
        self.team_repository = TeamRepository([self.team_entity_1, self.team_entity_2])
        self.professional_repository = ProfessionalRepository([self.professional_entity_1, self.professional_entity_2])
        self.room_repository = RoomRepository([self.room_entity_1, self.room_entity_2])

    # Testando método `add_all` e `get_all` com CirurgyRepository
    def test_add_all_and_get_all_cirurgies(self):
        cirurgy_model_3 = CirurgyModel(
            penalty=PunishmentObj(value=60),
            duration=DurationObj(hours=0, minutes=45),
            possible_teams_ids=[IdObj(value=5)],
            possible_rooms_ids=[IdObj(value=6)],
            team_id=IdObj(value=5),
            room_id=IdObj(value=6),
            time=TimeObj(start=900),
            name=NameObj(value="Cirurgy C")
        )
        cirurgy_model_4 = CirurgyModel(
            penalty=PunishmentObj(value=85),
            duration=DurationObj(hours=3, minutes=15),
            possible_teams_ids=[IdObj(value=7)],
            possible_rooms_ids=[IdObj(value=8)],
            team_id=IdObj(value=7),
            room_id=IdObj(value=8),
            time=TimeObj(start=1500),
            name=NameObj(value="Cirurgy D")
        )
        cirurgy_entity_3 = CirurgyEntity(cirurgy_model_3)
        cirurgy_entity_4 = CirurgyEntity(cirurgy_model_4)

        self.cirurgy_repository.add_all([cirurgy_entity_3, cirurgy_entity_4])

        all_cirurgies = self.cirurgy_repository.get_all()
        self.assertEqual(len(all_cirurgies), 4)
        self.assertEqual(all_cirurgies[-1].model.name.value, "Cirurgy D")

    # Testando `get_by_name` com TeamRepository
    def test_get_by_name_team(self):
        team = self.team_repository.get_by_name("Team X")
        self.assertIsNotNone(team)
        self.assertEqual(team.model.name.value, "Team X")

    # Testando `get_by_id` com RoomRepository
    def test_get_by_id_room(self):
        room = self.room_repository.get_by_id(0)
        self.assertIsNotNone(room)
        self.assertEqual(room.model.name.value, "Room 1")

    # Testando `get_names` com ProfessionalRepository
    def test_get_names_professionals(self):
        professional_names = self.professional_repository.get_names()
        self.assertEqual(professional_names, ["Professional 1", "Professional 2"])

    # Testando `get_names_and_ids` com CirurgyRepository
    def test_get_names_and_ids_cirurgies(self):
        names_and_ids = self.cirurgy_repository.get_names_and_ids()
        self.assertEqual(names_and_ids, ["Cirurgy A - 0", "Cirurgy B - 1"])

    # Testando `get_id_by_names_with_ids` com TeamRepository
    def test_get_id_by_names_with_ids_team(self):
        team_ids = [0, 1]
        result = self.team_repository.get_id_by_names_with_ids(team_ids)
        self.assertEqual(["Team X - 0", "Team Y - 1"], result)

    # Testando `extract_names_with_ids` com RoomRepository
    def test_extract_names_with_ids_room(self):
        rooms = self.room_repository.get_all()
        extracted = RoomRepository.extract_names_with_ids(rooms)
        self.assertEqual(extracted, ["Room 1 - 0", "Room 2 - 1"])


if __name__ == '__main__':
    unittest.main()