import unittest
from unittest.mock import patch, mock_open
from src.backend.services.data_service import DataService
from src.backend.repositories import CirurgyRepository, ProfessionalRepository, RoomRepository, TeamRepository


class TestDataService(unittest.TestCase):

    def setUp(self):
        # Exemplo de JSON com objetos esperados (IdObj, NameObj)
        self.mock_json_data = {
            "cirurgies": [
                {"id": {"value": 1}, "name": {"value": "Cirurgia A"}, "equipe_id": {"value": 2}, "sala_id": {"value": 3}},
                {"id": {"value": 2}, "name": {"value": "Cirurgia B"}, "equipe_id": {"value": 2}, "sala_id": {"value": 4}}
            ],
            "professionals": [
                {"id": {"value": 1}, "name": {"value": "Dr. Fulano"}, "equipe_id": {"value": 2}},
                {"id": {"value": 2}, "name": {"value": "Dr. Ciclano"}, "equipe_id": {"value": 3}}
            ],
            "rooms": [
                {"id": {"value": 3}, "name": {"value": "Sala 1"}},
                {"id": {"value": 4}, "name": {"value": "Sala 2"}}
            ],
            "teams": [
                {"id": {"value": 2}, "name": {"value": "Equipe 1"}, "medico_responsavel_id": {"value": 1}},
                {"id": {"value": 3}, "name": {"value": "Equipe 2"}, "medico_responsavel_id": {"value": 2}}
            ]
        }

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch("json.load")
    def test_load_data(self, mock_json_load, mock_file):
        # Mock do retorno do json.load para simular os dados carregados do JSON
        mock_json_load.return_value = self.mock_json_data

        # Instanciar o DataService e chamar load_data
        data_service = DataService(json_path="fake_path.json")
        data_service.load_data()

        # Verificar se os repositórios foram carregados corretamente
        cirurgy_repo = data_service.get_cirurgy_repository()
        professional_repo = data_service.get_professional_repository()
        room_repo = data_service.get_room_repository()
        team_repo = data_service.get_team_repository()

        # Verificar o conteúdo dos repositórios
        self.assertIsInstance(cirurgy_repo, CirurgyRepository)
        self.assertIsInstance(professional_repo, ProfessionalRepository)
        self.assertIsInstance(room_repo, RoomRepository)
        self.assertIsInstance(team_repo, TeamRepository)

        # Verificar que as entidades foram carregadas corretamente
        cirurgias = cirurgy_repo.get_all()
        self.assertEqual(len(cirurgias), 2)
        self.assertEqual(cirurgias[0]._model.name.value, "Cirurgia A")

        profissionais = professional_repo.get_all()
        self.assertEqual(len(profissionais), 2)
        self.assertEqual(profissionais[0]._model.name.value, "Dr. Fulano")

        salas = room_repo.get_all()
        self.assertEqual(len(salas), 2)
        self.assertEqual(salas[0]._model.name.value, "Sala 1")

        equipes = team_repo.get_all()
        self.assertEqual(len(equipes), 2)
        self.assertEqual(equipes[0]._model.name.value, "Equipe 1")


if __name__ == "__main__":
    unittest.main()
