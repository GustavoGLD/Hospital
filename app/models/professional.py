from typing import Optional, Annotated

from sqlmodel import SQLModel, Field, Relationship


class Professional(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: Annotated[str, int]
    team_id: Optional[int] = Field(default=None, foreign_key="team.id")

    team: Optional["Team"] = Relationship(back_populates="professionals")
