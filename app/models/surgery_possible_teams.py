from sqlmodel import SQLModel, Field, Relationship


class SurgeryPossibleTeams(SQLModel, table=True):
    __tablename__ = "surgery_possible_teams"
    __table_args__ = {'extend_existing': True}

    surgery_id: int = Field(foreign_key="surgery.id", primary_key=True)
    team_id: int = Field(foreign_key="team.id", primary_key=True)

    surgery: "Surgery" = Relationship(back_populates="possible_teams")
    team: "Team" = Relationship(back_populates="possible_surgeries")
