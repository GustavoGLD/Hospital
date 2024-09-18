import os
import sys
from inspect import getsourcefile


current_dir = os.path.dirname(os.path.abspath(getsourcefile(lambda:0)))
sys.path.insert(0, current_dir[:current_dir.rfind(os.path.sep)])

import unittest
from src.models.cirurgy_model import CirurgyModel
from src.models.professional_model import ProfessionalModel
from src.models.room_model import RoomModel
from src.models.team_model import TeamModel
from src.objects.id_obj import IdObj
from src.objects.time_obj import TimeObj
from src.objects.punishment_obj import PunishmentObj
from src.entities.cirurgy_entity import CirurgyEntity
from src.entities.professional_entity import ProfessionalEntity
from src.entities.room_entity import RoomEntity
from src.entities.team_entity import TeamEntity
from src.objects import NameObj


class TestEntities(unittest.TestCase):

    def test_create_cirurgy_entity(self):
        # Criar um modelo de cirurgia com dados específicos
        cirurgy_model = CirurgyModel(
            punicao=PunishmentObj(value=50),
            equipes_ids=[IdObj(value=1), IdObj(value=2)],
            equipes_possiveis_ids=[IdObj(value=1)],
            tempo_inicio=TimeObj(start=1200),
            sala_id=IdObj(value=10)
        )
        cirurgy_entity = CirurgyEntity(model=cirurgy_model)

        # Verificações
        self.assertEqual(cirurgy_entity.model.punicao.value, 50)
        self.assertEqual(cirurgy_entity.model.equipes_ids[0].value, 1)
        self.assertEqual(cirurgy_entity.model.tempo_inicio.start, 1200)
        self.assertEqual(cirurgy_entity.model.sala_id.value, 10)

    def test_create_professional_entity(self):
        # Criar um modelo de profissional com dados específicos
        professional_model = ProfessionalModel(
            id=IdObj(value=3),
            name=NameObj(value="Dr. John Doe"),
            equipes_ids=[IdObj(value=1), IdObj(value=2)],
            equipes_responsaveis_ids=[IdObj(value=2)]
        )
        professional_entity = ProfessionalEntity(model=professional_model)

        # Verificações
        self.assertEqual(professional_entity.model.id.value, 3)
        self.assertEqual(professional_entity.model.name.value, "Dr. John Doe")
        self.assertEqual(len(professional_entity.model.equipes_ids), 2)

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
            profissionais_ids=[IdObj(value=10), IdObj(value=11)],
            medico_responsavel_id=IdObj(value=20)
        )
        team_entity = TeamEntity(model=team_model)

        # Verificações
        self.assertEqual(team_entity.model.id.value, 7)
        self.assertEqual(team_entity.model.name.value, "Equipe A")
        self.assertEqual(team_entity.model.medico_responsavel_id.value, 20)
        self.assertEqual(len(team_entity.model.profissionais_ids), 2)


if __name__ == "__main__":
    unittest.main()
