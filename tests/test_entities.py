import os
import sys
from inspect import getsourcefile

current_dir = os.path.dirname(os.path.abspath(getsourcefile(lambda:0)))
sys.path.insert(0, current_dir[:current_dir.rfind(os.path.sep)])

import unittest
from src.backend.models.cirurgy_model import CirurgyModel
from src.backend.models import ProfessionalModel
from src.backend.models import RoomModel
from src.backend.models.team_model import TeamModel
from src.backend.objects import IdObj, DurationObj
from src.backend.objects import TimeObj
from src.backend.objects import PunishmentObj
from src.backend.entities.cirurgy_entity import CirurgyEntity
from src.backend.entities.professional_entity import ProfessionalEntity
from src.backend.entities.room_entity import RoomEntity
from src.backend.entities import TeamEntity
from src.backend.objects import NameObj


class TestEntities(unittest.TestCase):

    def setUp(self):
        # Configurações iniciais
        self.cirurgy_model = CirurgyModel(
            penalty=PunishmentObj(value=50),
            duration=DurationObj(hours=1, minutes=30),
            possible_teams_ids=[IdObj(value=1), IdObj(value=2)],
            possible_rooms_ids=[IdObj(value=3), IdObj(value=4)],
            team_id=IdObj(value=1),
            room_id=IdObj(value=2),
            time=TimeObj(start=1200)
        )
        self.room_model = RoomModel(id=IdObj(value=2))
        self.team_model = TeamModel(id=IdObj(value=3))
        self.professional_model = ProfessionalModel(id=IdObj(value=4))

        self.cirurgy_entity = CirurgyEntity(self.cirurgy_model)
        self.room_entity = RoomEntity(self.room_model)
        self.team_entity = TeamEntity(self.team_model)
        self.professional_entity = ProfessionalEntity(self.professional_model)

    def test_create_professional_entity(self):
        # Criar um modelo de profissional com dados específicos
        professional_model = ProfessionalModel(
            id=IdObj(value=3),
            name=NameObj(value="Dr. John Doe"),
            teams_ids=[IdObj(value=1), IdObj(value=2)],  # Verifique se este é o nome do campo correto
            responsable_teams_ids=[IdObj(value=2)]
        )
        # Corrija a linha abaixo caso os nomes dos campos estejam diferentes no modelo
        professional_entity = ProfessionalEntity(model=professional_model)

        # Verificações
        self.assertEqual(professional_entity.model.id.value, 3)
        self.assertEqual(professional_entity.model.name.value, "Dr. John Doe")
        self.assertEqual(len(professional_entity.model.teams_ids), 2)

    def test_create_room_entity(self):
        # Criar um modelo de sala com dados específicos
        room_model = RoomModel(
            id=IdObj(value=5),
            name=NameObj(value="Sala de Cirurgia 1"),
            cirurgias_ids=[IdObj(value=101), IdObj(value=102)]
        )
        room_entity = RoomEntity(model=room_model)

        # Verificações
        self.assertEqual(room_entity.model.id.value, 5)
        self.assertEqual(room_entity.model.name.value, "Sala de Cirurgia 1")
        self.assertEqual(len(room_entity.model.cirurgias_ids), 2)

    def test_create_team_entity(self):
        # Criar um modelo de equipe com dados específicos
        team_model = TeamModel(
            id=IdObj(value=7),
            name=NameObj(value="Equipe A"),
            professionals_ids=[IdObj(value=10), IdObj(value=11)],
            responsible_professional_id=IdObj(value=20)
        )
        team_entity = TeamEntity(model=team_model)

        # Verificações
        self.assertEqual(team_entity.model.id.value, 7)
        self.assertEqual(team_entity.model.name.value, "Equipe A")
        self.assertEqual(team_entity.model.responsible_professional_id.value, 20)
        self.assertEqual(len(team_entity.model.professionals_ids), 2)


class TestEntitiesBehaviours(unittest.TestCase):

    def setUp(self):
        # Create an instance of CirurgyModel with all required fields filled out
        self.cirurgy_model = CirurgyModel(
            id=IdObj(value=1),  # Assuming you want an ID of 1
            penalty=PunishmentObj(value=50),  # Example penalty value
            duration=DurationObj(hours=1, minutes=30),  # Example duration value
            possible_teams_ids=[IdObj(value=2), IdObj(value=3)],  # Example teams
            possible_rooms_ids=[IdObj(value=4), IdObj(value=5)],  # Example rooms
            team_id=IdObj(value=2),  # Example team ID
            room_id=IdObj(value=4),  # Example room ID
            time=TimeObj(start=1200)  # Example start time
        )
        # Create other entities as needed
        self.room_model = RoomModel(id=IdObj(value=2))  # Example room model
        self.team_model = TeamModel(id=IdObj(value=3))  # Example team model
        self.professional_model = ProfessionalModel(id=IdObj(value=4))  # Example professional model

        # Initialize entities
        self.cirurgy_entity = CirurgyEntity(self.cirurgy_model)
        self.room_entity = RoomEntity(self.room_model)
        self.team_entity = TeamEntity(self.team_model)
        self.professional_entity = ProfessionalEntity(self.professional_model)

    def test_set_team(self):
        # Testa se a cirurgia foi associada ao time corretamente
        self.cirurgy_entity.set_team(self.team_entity)
        self.assertEqual(self.cirurgy_model.team_id, self.team_model.id)
        self.assertIn(self.cirurgy_model.id, self.team_model.cirurgias_ids)

    def test_set_room(self):
        # Testa se a cirurgia foi associada à sala corretamente
        self.cirurgy_entity.set_room(self.room_entity)
        self.assertEqual(self.cirurgy_model.room_id, self.room_model.id)
        self.assertIn(self.cirurgy_model.id, self.room_model.cirurgias_ids)

    def test_add_cirurgy_to_room(self):
        # Testa se a cirurgia foi adicionada à sala corretamente
        self.room_entity.add_cirurgy(self.cirurgy_entity)
        self.assertEqual(self.cirurgy_model.room_id, self.room_model.id)
        self.assertIn(self.cirurgy_model.id, self.room_model.cirurgias_ids)

    def test_add_professional_to_team(self):
        # Testa se o profissional foi adicionado ao time corretamente
        self.team_entity.add_professional(self.professional_entity)
        self.assertIn(self.professional_model.id, self.team_model.professionals_ids)
        self.assertIn(self.team_model.id, self.professional_model.teams_ids)

    def test_set_responsible_professional(self):
        # Testa se o profissional foi definido como responsável corretamente
        self.team_entity.add_professional(self.professional_entity)
        self.team_entity.set_responsible(self.professional_entity)
        self.assertEqual(self.team_model.responsible_professional_id, self.professional_model.id)
        self.assertIn(self.team_model.id, self.professional_model.responsibles_teams_ids)

    def test_set_responsible_professional_invalid(self):
        # Testa se o erro é lançado ao tentar definir um responsável que não está no time
        with self.assertRaises(ValueError):
            self.team_entity.set_responsible(self.professional_entity)


if __name__ == "__main__":
    unittest.main()
