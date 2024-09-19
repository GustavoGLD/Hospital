from typing import TypeVar, Generic

from src.models import GenericModel

T = TypeVar("T", bound=GenericModel)


class GenericEntity(Generic[T]):
    def __init__(self, model: T):
        self._model = model
