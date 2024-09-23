from abc import ABC, abstractmethod


class GenericController(ABC):

    @abstractmethod
    def start(self):
        raise NotImplementedError