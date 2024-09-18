from ctypes import Union
from typing import TypeVar, Generic

from src.entities.generic_entity import GenericEntity
from src.objects import IdObj

T = TypeVar("T", bound=GenericEntity)


class GenericRepository(Generic[T]):
    def __init__(self, entity_list: list[T] = None):
        self._id_counter = 0
        self.repository = []

        self.add_all(entity_list if entity_list is not None else [])

    def add(self, model: T):
        model.id = IdObj(value=self._id_counter)
        self._id_counter += 1
        self.repository.append(model)

    def add_all(self, models: list[T]):
        for model in models:
            self.add(model)

    def get_all(self) -> list[T]:
        return self.repository

    def get_names(self) -> list[str]:
        return [unity.value for unity in self.repository]
    
    def get_by_id(self, _id: int | str) -> T | None:
        return next((model for model in self.repository if int(model.id.value) == int(_id)), None)

    def get_by_name(self, name: str) -> T | None:
        return next((entity for entity in self.repository if entity.model.name.value == name), None)

    def get_names_and_ids(self) -> list[str]:
        return [f"{model.value} - {model.value}" for model in self.repository]

    def get_id_by_names_with_ids(self, teams_ids: list[int]) -> list[str]:
        return [f"{self.get_by_id(team_id).name} - {team_id}" for team_id in teams_ids]

    @staticmethod
    def extract_names_with_ids(models: list[T]) -> list[str]:
        return [f"{model.name} - {model.id}" for model in models]

