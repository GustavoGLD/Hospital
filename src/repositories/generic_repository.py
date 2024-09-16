from ctypes import Union

from src.models.generic_model import GenericModel


class GenericRepository:
    def __init__(self, models: list[GenericModel]):
        self.models = models

    def get_names(self):
        return [model.name for model in self.models]
    
    def get_by_id(self, _id: int | str) -> GenericModel | None:
        return next((model for model in self.models if int(model.id) == int(_id)), None)

    def get_by_name(self, name: str) -> GenericModel | None:
        return next((model for model in self.models if model.name == name), None)

    def get_names_and_ids(self) -> list[str]:
        return [f"{model.name} - {model.id}" for model in self.models]

    def get_id_by_names_with_ids(self, teams_ids: list[int]) -> list[str]:
        return [f"{self.get_by_id(team_id).name} - {team_id}" for team_id in teams_ids]

    @staticmethod
    def extract_names_with_ids(models: list[GenericModel]) -> list[str]:
        return [f"{model.name} - {model.id}" for model in models]



