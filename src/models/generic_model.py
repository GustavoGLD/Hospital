from pydantic import BaseModel


class GenericModel(BaseModel):
    id: int
    nome: str
