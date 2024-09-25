from typing import TypeVar, Generic

from src.backend.models.generic_model import GenericModel

T = TypeVar("T", bound=GenericModel)


class GenericEntity(Generic[T]):
    def __init__(self, model: T):
        self.model = model

    def __repr__(self):
        return f"{type(self.model).__qualname__}({self.model})"
