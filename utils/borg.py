from abc import abstractmethod
from typing import TypeVar, Generic, Type, Callable, Any, Union
import streamlit as st
from loguru import logger

T = TypeVar("T")


class BorgBaseClass(Generic[T]):
    ...


class Default(BorgBaseClass[T]):
    def __init__(self, value: T):
        self.value = value


class BorgObj(BorgBaseClass[T]):
    def __init__(self, key: str, type_: Type[T]):
        self.key = key
        self.type_ = type_

    @property
    def value(self) -> T:
        if self.key not in st.session_state:
            return None
        else:
            return st.session_state[self.key]

    @value.setter
    def value(self, value: Union[T, Default[T], "BorgObj[T]"]):
        if isinstance(value, Default):
            if self.key not in st.session_state:
                st.session_state[self.key] = value.value
        elif isinstance(value, BorgObj):
            st.session_state[self.key] = value.value
        else:
            st.session_state[self.key] = value


class BorgName(BorgBaseClass[T]):
    def __init__(self, naming: Callable, type_: Type[T], pre_key: str = ''):
        self.__naming = naming
        self.__type_ = type_
        self.__pre_key = pre_key

    def get_key(self, key: str) -> str:
        return self.__naming(key)

    def exists(self, key: str) -> bool:
        return self.__naming(key) in st.session_state

    def __getitem__(self, item: Union[str, BorgObj[str]]) -> Union[T, None]:
        if isinstance(item, BorgObj):
            if self.__naming(item.key) in st.session_state:
                return st.session_state[self.__naming(item.key)]
            else:
                return None
        else:
            if self.__naming(item) in st.session_state:
                return st.session_state[self.__naming(item)]
            else:
                return None

    def __setitem__(self, key: str, value: Union[T, Default[T], BorgObj[T]]):
        if isinstance(value, Default):
            if self.__naming(key) not in st.session_state:
                st.session_state[self.__naming(key)] = value.value
        elif isinstance(value, BorgObj):
            st.session_state[self.__naming(key)] = st.session_state[value.key]
        else:
            st.session_state[self.__naming(key)] = value


class Borg:
    _shared_state = {}

    def __getattr__(self, item: str) -> Any:
        if item not in Borg._shared_state:
            raise AttributeError(f'{item} não existe no Borg Pattern')

        attr = Borg._shared_state[item]
        if isinstance(attr, BorgName) or isinstance(attr, BorgObj):
            return attr
        else:
            raise AttributeError(f'{item} não é um atributo válido no Borg Pattern')

    def __setattr__(self, key: str, value: Union[T, Default[T], BorgName[T], BorgObj[T]]):
        if isinstance(value, BorgName) or isinstance(value, BorgObj):
            Borg._shared_state[key] = value
            return

        if key not in Borg._shared_state:
            raise AttributeError(f'{key} não é um atributo válido')

        attr = Borg._shared_state[key]
        if isinstance(attr, BorgName):
            Borg._shared_state[key][self.tablename] = value
            raise AttributeError(f'{key} é um atributo de leitura apenas')
        elif isinstance(attr, BorgObj):
            if isinstance(value, Default) and attr.key not in st.session_state:
                Borg._shared_state[key].value = value.value
            elif not isinstance(value, Default):
                Borg._shared_state[key].value = value
        else:
            raise AttributeError(f'{key} não é um atributo válido')
