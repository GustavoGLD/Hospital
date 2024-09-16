from ctypes import Union
from typing import TypeVar, Generic

from src.models.generic_model import GenericModel

T = TypeVar("T", bound=GenericModel)


class GenericRepository(Generic[T]):
    def __init__(self, models: list[T] = None):
        self._id_counter = 0
        self.models = []

        self.add_all(models if models is not None else [])

    def add(self, model: T):
        model.id = self._id_counter
        self._id_counter += 1
        self.models.append(model)

    def add_all(self, models: list[T]):
        for model in models:
            self.add(model)

    def get_models(self) -> list[T]:
        return self.models

    def get_names(self) -> list[str]:
        return [model.name for model in self.models]
    
    def get_by_id(self, _id: int | str) -> T | None:
        return next((model for model in self.models if int(model.id) == int(_id)), None)

    def get_by_name(self, name: str) -> T | None:
        return next((model for model in self.models if model.name == name), None)

    def get_names_and_ids(self) -> list[str]:
        return [f"{model.name} - {model.id}" for model in self.models]

    def get_id_by_names_with_ids(self, teams_ids: list[int]) -> list[str]:
        return [f"{self.get_by_id(team_id).name} - {team_id}" for team_id in teams_ids]

    @staticmethod
    def extract_names_with_ids(models: list[T]) -> list[str]:
        return [f"{model.name} - {model.id}" for model in models]

