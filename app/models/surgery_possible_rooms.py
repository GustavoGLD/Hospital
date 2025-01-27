from sqlmodel import SQLModel, Field


class SurgeryPossibleRooms(SQLModel, table=True):
    __tablename__ = 'surgery_possible_rooms'

    surgery_id: int = Field(foreign_key='surgery.id', primary_key=True)
    room_id: int = Field(foreign_key='room.id', primary_key=True)
