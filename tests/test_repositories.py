import os
import sys
from inspect import getsourcefile


current_dir = os.path.dirname(os.path.abspath(getsourcefile(lambda:0)))
sys.path.insert(0, current_dir[:current_dir.rfind(os.path.sep)])

import unittest
from src.entities import CirurgyEntity, ProfessionalEntity, RoomEntity, TeamEntity
from src.models import CirurgyModel, ProfessionalModel, RoomModel, TeamModel
from src.repositories.cirurgy_repository import CirurgyRepository
from src.repositories.professional_repository import ProfessionalRepository
from src.repositories.room_repository import RoomRepository
from src.repositories.team_repository import TeamRepository


class TestRepositories(unittest.TestCase):

    def setUp(self):
        # Configuração inicial antes dos testes
        self.cirurgy_model = CirurgyModel()
        self.professional_model = ProfessionalModel()
        self.room_model = RoomModel()
        self.team_model = TeamModel()

        # Criando entidades
        self.cirurgy_entity = CirurgyEntity(model=self.cirurgy_model)
        self.professional_entity = ProfessionalEntity(model=self.professional_model)
        self.room_entity = RoomEntity(model=self.room_model)
        self.team_entity = TeamEntity(model=self.team_model)

        # Criando repositórios
        self.cirurgy_repository = CirurgyRepository()
        self.professional_repository = ProfessionalRepository()
        self.room_repository = RoomRepository()
        self.team_repository = TeamRepository()

    def test_add_cirurgy(self):
        # Adicionando uma cirurgia e verificando se foi adicionado corretamente
        self.cirurgy_repository.add(self.cirurgy_entity)
        cirurgies = self.cirurgy_repository.get_all()
        self.assertEqual(len(cirurgies), 1)
        self.assertEqual(cirurgies[0], self.cirurgy_entity)

    def test_add_professional(self):
        # Adicionando um profissional e verificando se foi adicionado corretamente
        self.professional_repository.add(self.professional_entity)
        professionals = self.professional_repository.get_all()
        self.assertEqual(len(professionals), 1)
        self.assertEqual(professionals[0], self.professional_entity)

    def test_add_room(self):
        # Adicionando uma sala e verificando se foi adicionado corretamente
        self.room_repository.add(self.room_entity)
        rooms = self.room_repository.get_all()
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0], self.room_entity)

    def test_add_team(self):
        # Adicionando uma equipe e verificando se foi adicionado corretamente
        self.team_repository.add(self.team_entity)
        teams = self.team_repository.get_all()
        self.assertEqual(len(teams), 1)
        self.assertEqual(teams[0], self.team_entity)

    def test_get_by_id(self):
        # Teste de obter uma entidade pelo ID
        self.room_repository.add(self.room_entity)
        retrieved_room = self.room_repository.get_by_id(self.room_entity.model.id.value)
        self.assertEqual(retrieved_room, self.room_entity)

    def test_get_by_name(self):
        # Teste de obter uma entidade pelo nome
        self.team_entity.model.name.value = "Equipe A"
        self.team_repository.add(self.team_entity)
        retrieved_team = self.team_repository.get_by_name("Equipe A")
        self.assertEqual(retrieved_team, self.team_entity)


if __name__ == '__main__':
    unittest.main()
