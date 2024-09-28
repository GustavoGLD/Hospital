from pydantic import BaseModel, Field


class GenericObj(BaseModel):
    class Config:
        validate_assignment = True
