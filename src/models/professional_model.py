from pydantic import BaseModel


class Professional(BaseModel):
    id: int
    name: str