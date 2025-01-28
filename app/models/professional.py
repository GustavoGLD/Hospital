from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class Professional(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str
    team_id: Optional[int] = Field(default=None, foreign_key="team.id")

    team: Optional["Team"] = Relationship(back_populates="professionals")
