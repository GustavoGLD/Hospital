import json
from src.backend.entities import (
    CirurgyEntity,
    ProfessionalEntity,
    RoomEntity,
    TeamEntity
)
from src.backend.models import (
    CirurgyModel,
    ProfessionalModel,
    RoomModel,
    TeamModel
)
from src.backend.repositories import (
    CirurgyRepository,
    ProfessionalRepository,
    RoomRepository,
    TeamRepository
)


class DataService:
    def __init__(self, json_path: str):
        self.json_path = json_path
        self.cirurgy_repository: CirurgyRepository | None = None
        self.professional_repository: ProfessionalRepository | None = None
        self.room_repository: RoomRepository | None = None
        self.team_repository: TeamRepository | None = None

    def load_data(self):
        """Carrega os dados do arquivo JSON e inicializa os repositórios."""
        with open(self.json_path, 'r') as f:
            data = json.load(f)

        # Carregar os repositórios com os dados do JSON
        self.cirurgy_repository = self._load_cirurgy_repository(data['cirurgies'])
        self.professional_repository = self._load_professional_repository(data['professionals'])
        self.room_repository = self._load_room_repository(data['rooms'])
        self.team_repository = self._load_team_repository(data['teams'])

    def _load_cirurgy_repository(self, cirurgias_data: list[dict]) -> CirurgyRepository:
        """Cria e retorna o repositório de cirurgias com base nos dados do JSON."""
        cirurgias = []
        for cir_data in cirurgias_data:
            cir_model = CirurgyModel(**cir_data)  # Inicializar o modelo com os dados
            cir_entity = CirurgyEntity(model=cir_model)  # Criar a entidade
            cirurgias.append(cir_entity)
        return CirurgyRepository(entity_list=cirurgias)

    def _load_professional_repository(self, profissionais_data: list[dict]) -> ProfessionalRepository:
        """Cria e retorna o repositório de profissionais com base nos dados do JSON."""
        profissionais = []
        for prof_data in profissionais_data:
            prof_model = ProfessionalModel(**prof_data)  # Inicializar o modelo com os dados
            prof_entity = ProfessionalEntity(model=prof_model)  # Criar a entidade
            profissionais.append(prof_entity)
        return ProfessionalRepository(entity_list=profissionais)

    def _load_room_repository(self, salas_data: list[dict]) -> RoomRepository:
        """Cria e retorna o repositório de salas com base nos dados do JSON."""
        salas = []
        for sala_data in salas_data:
            sala_model = RoomModel(**sala_data)  # Inicializar o modelo com os dados
            sala_entity = RoomEntity(model=sala_model)  # Criar a entidade
            salas.append(sala_entity)
        return RoomRepository(entity_list=salas)

    def _load_team_repository(self, equipes_data: list[dict]) -> TeamRepository:
        """Cria e retorna o repositório de equipes com base nos dados do JSON."""
        equipes = []
        for equipe_data in equipes_data:
            equipe_model = TeamModel(**equipe_data)  # Inicializar o modelo com os dados
            equipe_entity = TeamEntity(model=equipe_model)  # Criar a entidade
            equipes.append(equipe_entity)
        return TeamRepository(entity_list=equipes)

    def get_cirurgy_repository(self) -> CirurgyRepository:
        """Retorna o repositório de cirurgias."""
        assert self.cirurgy_repository is not None, "Repositório de cirurgias não inicializado."
        return self.cirurgy_repository  # self.cirurgy_repository: CirurgyRepository

    def get_professional_repository(self) -> ProfessionalRepository:
        """Retorna o repositório de profissionais."""
        assert self.professional_repository is not None, "Repositório de profissionais não inicializado."
        return self.professional_repository  # self.professional_repository: ProfessionalRepository

    def get_room_repository(self) -> RoomRepository:
        """Retorna o repositório de salas."""
        assert self.room_repository is not None, "Repositório de salas não inicializado."
        return self.room_repository  # self.room_repository: RoomRepository

    def get_team_repository(self) -> TeamRepository:
        """Retorna o repositório de equipes."""
        assert self.team_repository is not None, "Repositório de equipes não inicializado."
        return self.team_repository  # self.team_repository: TeamRepository

