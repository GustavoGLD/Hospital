import os
import sys
from inspect import getsourcefile

current_dir = os.path.dirname(os.path.abspath(getsourcefile(lambda:0)))
sys.path.insert(0, current_dir[:current_dir.rfind(os.path.sep)])

import pytest
from src.models.cirurgy_model import CirurgyModel
from src.models.generic_model import GenericModel
from src.models.room_model import RoomModel
from src.models.team_model import TeamModel
from src.models.professional_model import ProfessionalModel
from src.objects import IdObj, TimeObj, PunishmentObj, NameObj


def test_generic_model_custom_data():
    # Cria dados personalizados
    custom_id = IdObj(value=10)
    custom_name = NameObj(value="Cirurgia Teste")

    # Instancia o GenericModel com dados personalizados
    generic_model = GenericModel(id=custom_id, nome=custom_name)

    # Verifica se os dados estão corretos
    assert generic_model.id.value == 10
    assert generic_model.nome.value == "Cirurgia Teste"

    print(generic_model.model_dump())


def test_cirurgy_model_custom_data():
    # Cria dados personalizados
    punicao_custom = PunishmentObj(value=5)
    equipes_ids_custom = [IdObj(value=1), IdObj(value=2)]
    tempo_inicio_custom = TimeObj(start=100)
    sala_id_custom = IdObj(value=42)

    # Instancia o CirurgyModel com dados personalizados
    cirurgy_model = CirurgyModel(
        punicao=punicao_custom,
        equipes_ids=equipes_ids_custom,
        equipes_possiveis_ids=[IdObj(value=3), IdObj(value=4)],
        tempo_inicio=tempo_inicio_custom,
        sala_id=sala_id_custom
    )

    # Verifica se os dados estão corretos
    assert cirurgy_model.punicao.value == 5
    assert len(cirurgy_model.equipes_ids) == 2
    assert cirurgy_model.equipes_ids[0].value == 1
    assert cirurgy_model.equipes_possiveis_ids[1].value == 4
    assert cirurgy_model.tempo_inicio.start == 100
    assert cirurgy_model.sala_id.value == 42

    print(cirurgy_model.model_dump())


def test_room_model_custom_data():
    # Cria dados personalizados
    cirurgias_ids_custom = [IdObj(value=10), IdObj(value=20)]

    # Instancia o RoomModel com dados personalizados
    room_model = RoomModel(cirurgias_ids=cirurgias_ids_custom)

    # Verifica se os dados estão corretos
    assert len(room_model.cirurgias_ids) == 2
    assert room_model.cirurgias_ids[0].value == 10
    assert room_model.cirurgias_ids[1].value == 20

    print(room_model.model_dump())


def test_team_model_custom_data():
    # Cria dados personalizados
    profissionais_ids_custom = [IdObj(value=100), IdObj(value=101)]
    medico_responsavel_custom = IdObj(value=200)

    # Instancia o TeamModel com dados personalizados
    team_model = TeamModel(
        profissionais_ids=profissionais_ids_custom,
        medico_responsavel_id=medico_responsavel_custom
    )

    # Verifica se os dados estão corretos
    assert len(team_model.profissionais_ids) == 2
    assert team_model.profissionais_ids[0].value == 100
    assert team_model.medico_responsavel_id.value == 200

    print(team_model.model_dump())


def test_professional_model_custom_data():
    # Cria dados personalizados
    equipes_ids_custom = [IdObj(value=30), IdObj(value=31)]
    equipes_responsaveis_custom = [IdObj(value=40)]

    # Instancia o ProfessionalModel com dados personalizados
    professional_model = ProfessionalModel(
        equipes_ids=equipes_ids_custom,
        equipes_responsaveis_ids=equipes_responsaveis_custom
    )

    # Verifica se os dados estão corretos
    assert len(professional_model.equipes_ids) == 2
    assert professional_model.equipes_ids[1].value == 31
    assert len(professional_model.equipes_responsaveis_ids) == 1
    assert professional_model.equipes_responsaveis_ids[0].value == 40

    print(professional_model.model_dump())


if __name__ == "__main__":
    pytest.main()
