from src.backend.models.cirurgy_model import CirurgyModel
from src.backend.models.room_model import RoomModel
from src.backend.models.team_model import TeamModel
from src.backend.models.professional_model import ProfessionalModel

CirurgyModel.model_rebuild()
RoomModel.model_rebuild()
TeamModel.model_rebuild()
ProfessionalModel.model_rebuild()
