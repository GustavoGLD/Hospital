import os
import sys
from inspect import getsourcefile
import unittest

current_dir = os.path.dirname(os.path.abspath(getsourcefile(lambda: 0)))
sys.path.insert(0, current_dir[:current_dir.rfind(os.path.sep)])

from src.backend.models.cirurgy_model import CirurgyModel
from src.backend.models.generic_model import GenericModel
from src.backend.models import RoomModel
from src.backend.models.team_model import TeamModel
from src.backend.models import ProfessionalModel
from src.backend.objects import IdObj, TimeObj, PunishmentObj, NameObj
from src.backend.objects.duration import DurationObj


class TestModels(unittest.TestCase):

    def test_generic_model_custom_data(self):
        # Cria dados personalizados
        custom_id = IdObj(value=10)
        custom_name = NameObj(value="Cirurgia Teste")

        # Instancia o GenericModel com dados personalizados
        generic_model = GenericModel(id=custom_id, name=custom_name)

        # Verifica se os dados estão corretos
        self.assertEqual(generic_model.id.value, 10)
        self.assertEqual(generic_model.name.value, "Cirurgia Teste")

        print(generic_model.model_dump())

    def test_cirurgy_model_custom_data(self):
        # Cria dados personalizados
        punicao_custom = PunishmentObj(value=5)
        duration_custom = DurationObj(hours=1, minutes=0)
        equipe_id_custom = IdObj(value=1)
        tempo_start_custom = TimeObj(start=100)
        sala_id_custom = IdObj(value=42)

        # Instancia o CirurgyModel com dados personalizados
        cirurgy_model = CirurgyModel(
            penalty=punicao_custom,
            duration=duration_custom,
            possible_teams_ids=[IdObj(value=3), IdObj(value=4)],
            possible_rooms_ids=[IdObj(value=5), IdObj(value=6)],
            team_id=equipe_id_custom,
            room_id=sala_id_custom,
            time=tempo_start_custom
        )

        # Verifica se os dados estão corretos
        self.assertEqual(cirurgy_model.penalty.value, 5)
        self.assertEqual(cirurgy_model.team_id.value, 1)
        self.assertEqual(cirurgy_model.duration.hours, 1)
        self.assertEqual(cirurgy_model.room_id.value, 42)
        self.assertEqual(cirurgy_model.time.start, 100)

        print(cirurgy_model.model_dump())

    def test_room_model_custom_data(self):
        # Cria dados personalizados
        cirurgias_ids_custom = [IdObj(value=10), IdObj(value=20)]

        # Instancia o RoomModel com dados personalizados
        room_model = RoomModel(cirurgias_ids=cirurgias_ids_custom)

        # Verifica se os dados estão corretos
        self.assertEqual(len(room_model.cirurgias_ids), 2)
        self.assertEqual(room_model.cirurgias_ids[0].value, 10)
        self.assertEqual(room_model.cirurgias_ids[1].value, 20)

        print(room_model.model_dump())

    def test_team_model_custom_data(self):
        # Cria dados personalizados
        profissionais_ids_custom = [IdObj(value=100), IdObj(value=101)]
        medico_responsavel_custom = IdObj(value=200)

        # Instancia o TeamModel com dados personalizados
        team_model = TeamModel(
            professionals_ids=profissionais_ids_custom,
            responsible_professional_id=medico_responsavel_custom
        )

        # Verifica se os dados estão corretos
        self.assertEqual(len(team_model.professionals_ids), 2)
        self.assertEqual(team_model.professionals_ids[0].value, 100)
        self.assertEqual(team_model.responsible_professional_id.value, 200)

        print(team_model.model_dump())

    def test_professional_model_custom_data(self):
        # Cria dados personalizados
        equipes_ids_custom = [IdObj(value=30), IdObj(value=31)]
        equipes_responsaveis_custom = [IdObj(value=40)]

        # Instancia o ProfessionalModel com dados personalizados
        professional_model = ProfessionalModel(
            teams_ids=equipes_ids_custom,
            responsibles_teams_ids=equipes_responsaveis_custom
        )

        # Verifica se os dados estão corretos
        self.assertEqual(len(professional_model.teams_ids), 2)
        self.assertEqual(professional_model.teams_ids[1].value, 31)
        self.assertEqual(len(professional_model.responsibles_teams_ids), 1)
        self.assertEqual(professional_model.responsibles_teams_ids[0].value, 40)


if __name__ == "__main__":
    unittest.main()
