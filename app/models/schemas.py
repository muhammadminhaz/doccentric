from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PatientBase(BaseModel):
    name: str
    age: int
    gender: Optional[str] = None
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    emergency_contact: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    emergency_contact: Optional[str] = None


class PatientResponse(PatientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class VisitBase(BaseModel):
    doctor_id: str
    chief_complaint: Optional[str] = None
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    tests: Optional[str] = None
    prescription: Optional[str] = None
    suggestions: Optional[str] = None
    notes: Optional[str] = None
    visit_type: str = "initial"


class VisitCreate(VisitBase):
    patient_id: int


class VisitResponse(VisitBase):
    id: int
    patient_id: int
    date: datetime
    transcript: Optional[str] = None
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class AudioRecordResponse(BaseModel):
    id: int
    visit_id: int
    file_path: str
    file_name: Optional[str] = None
    duration: Optional[float] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


class AudioUploadResponse(BaseModel):
    patient_id: int
    patient_name: str
    is_new_patient: bool
    visit_id: int
    transcript: Optional[str] = None
    summary: Optional[str] = None