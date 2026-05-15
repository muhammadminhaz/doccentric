import logging
from sqlalchemy.orm import Session
from app.models.models import Patient, Visit, AudioRecord
from app.core.config import AUDIO_UPLOAD_DIR

logger = logging.getLogger(__name__)

UPLOAD_DIR = AUDIO_UPLOAD_DIR

def match_or_create_patient(db: Session, patient_data: dict) -> Patient:
    phone = patient_data.get("phone")
    
    # Try match by phone
    if phone:
        existing = db.query(Patient).filter(Patient.phone == phone).first()
        if existing:
            logger.info("patient_matched", extra={"patient_id": existing.id, "method": "phone"})
            return existing
    
    # Try match by name + age
    name = patient_data.get("name")
    age = patient_data.get("age")
    if name and age is not None:
        existing = db.query(Patient).filter(Patient.name == name, Patient.age == age).first()
        if existing:
            logger.info("patient_matched", extra={"patient_id": existing.id, "method": "name+age"})
            return existing
    
    # Create new patient
    patient = Patient(
        name=patient_data.get("name"),
        age=patient_data.get("age", 0),
        gender=patient_data.get("gender"),
        phone=patient_data.get("phone"),
        address=patient_data.get("address"),
        blood_type=patient_data.get("blood_type"),
        allergies=patient_data.get("allergies"),
        emergency_contact=patient_data.get("emergency_contact")
    )
    db.add(patient)
    db.flush()
    logger.info("patient_created", extra={"patient_id": patient.id})
    return patient

def create_visit(db: Session, patient_id: int, doctor_id: str, visit_data: dict, transcript: str) -> Visit:
    visit = Visit(
        patient_id=patient_id,
        doctor_id=doctor_id,
        transcript=transcript,
        chief_complaint=visit_data.get("chief_complaint"),
        symptoms=visit_data.get("symptoms"),
        diagnosis=visit_data.get("diagnosis"),
        tests=visit_data.get("tests"),
        prescription=visit_data.get("prescription"),
        suggestions=visit_data.get("suggestions"),
        notes=visit_data.get("notes"),
        visit_type=visit_data.get("visit_type", "initial"),
        summary=visit_data.get("summary")
    )
    db.add(visit)
    db.flush()
    logger.info("visit_saved", extra={"visit_id": visit.id, "patient_id": patient_id})
    return visit

def create_audio_record(db: Session, visit_id: int, file_path: str, file_name: str) -> AudioRecord:
    record = AudioRecord(
        visit_id=visit_id,
        file_path=file_path,
        file_name=file_name
    )
    db.add(record)
    db.flush()
    logger.info("audio_record_saved", extra={"record_id": record.id, "visit_id": visit_id})
    return record
