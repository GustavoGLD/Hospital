from ctypes import Union
from typing import TypeVar, Generic

from src.entities.generic_entity import GenericEntity
from src.models import GenericModel
from src.objects import IdObj

T = TypeVar("T", bound=GenericEntity[GenericModel])


class GenericRepository(Generic[T]):
    def __init__(self, entity_list: list[T] = None):
        self._id_counter = 0
        self.repository: list[T] = []

        self.add_all(entity_list if entity_list is not None else [])

    def add(self, entity: T):
        entity._model.id.value = self._id_counter
        self._id_counter += 1
        self.repository.append(entity)

    def add_all(self, entities: list[T]):
        for entity in entities:
            self.add(entity)

    def get_all(self) -> list[T]:
        return self.repository

    def get_names(self) -> list[str]:
        return [ett._model.name.value for ett in self.repository]
    
    def get_by_id(self, _id: int | str) -> T | None:
        return next((ett for ett in self.repository if int(ett._model.id.value) == int(_id)), None)

    def get_by_name(self, name: str) -> T | None:
        return next((entity for entity in self.repository if entity._model.name.value == name), None)

    def get_names_and_ids(self) -> list[str]:
        return [f"{ett._model.name.value} - {ett._model.id.value}" for ett in self.repository]

    def get_id_by_names_with_ids(self, teams_ids: list[int]) -> list[str]:
        return [f"{self.get_by_id(team_id)._model.name.value} - {team_id}" for team_id in teams_ids]

    @staticmethod
    def extract_names_with_ids(entities: list[T]) -> list[str]:
        return [f"{entity._model.name.value} - {entity._model.id.value}" for entity in entities]

