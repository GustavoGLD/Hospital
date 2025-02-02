from typing import Optional

from sqlmodel import SQLModel, Field


class Patient(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str
