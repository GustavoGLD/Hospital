from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import date


class PatientModel(SQLModel, table=True):
    __tablename__ = "patients"
    __table_args__ = {"schema": "siscofmy_med_ctrl"}

    idpatient: Optional[int] = Field(default=None, primary_key=True)
    patient_name: Optional[str] = Field(default=None, max_length=150)
    patient_birthdate: Optional[date] = Field(default=None)
    patient_gender: Optional[str] = Field(default=None, max_length=1)
    patient_blood: Optional[str] = Field(default=None, max_length=3)
    patient_phone: Optional[str] = Field(default=None, max_length=20)
    patient_email: Optional[str] = Field(default=None, max_length=100)
    patient_address: Optional[str] = Field(default=None, max_length=250)
