from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.observability import get_tracer
from app.models.models import Patient, Visit, AudioRecord
from app.models.schemas import (
    PatientCreate,
    PatientUpdate,
    PatientResponse,
    VisitCreate,
    VisitResponse,
    AudioRecordResponse
)

router = APIRouter()
logger = get_logger(__name__)
tracer = get_tracer(__name__)


@router.post("/patients", response_model=PatientResponse)
def create_patient(patient: PatientCreate, db: Session = Depends(get_db)):
    if tracer:
        with tracer.start_as_current_span("api.create_patient"):
            return _create_patient_impl(patient, db)
    return _create_patient_impl(patient, db)


def _create_patient_impl(patient: PatientCreate, db: Session):
    db_patient = Patient(**patient.model_dump())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    logger.info("patient_created", extra={"patient_id": db_patient.id})
    return db_patient


@router.get("/patients", response_model=List[PatientResponse])
def list_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if tracer:
        with tracer.start_as_current_span("api.list_patients"):
            return db.query(Patient).offset(skip).limit(limit).all()
    return db.query(Patient).offset(skip).limit(limit).all()


@router.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    if tracer:
        with tracer.start_as_current_span("api.get_patient"):
            return _get_patient_impl(patient_id, db)
    return _get_patient_impl(patient_id, db)


def _get_patient_impl(patient_id: int, db: Session):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/patients/{patient_id}", response_model=PatientResponse)
def update_patient(patient_id: int, patient: PatientUpdate, db: Session = Depends(get_db)):
    if tracer:
        with tracer.start_as_current_span("api.update_patient"):
            return _update_patient_impl(patient_id, patient, db)
    return _update_patient_impl(patient_id, patient, db)


def _update_patient_impl(patient_id: int, patient: PatientUpdate, db: Session):
    db_patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    for key, value in patient.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(db_patient, key, value)

    db.commit()
    db.refresh(db_patient)
    logger.info("patient_updated", extra={"patient_id": db_patient.id})
    return db_patient


@router.delete("/patients/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    if tracer:
        with tracer.start_as_current_span("api.delete_patient"):
            return _delete_patient_impl(patient_id, db)
    return _delete_patient_impl(patient_id, db)


def _delete_patient_impl(patient_id: int, db: Session):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    db.delete(patient)
    db.commit()
    logger.info("patient_deleted", extra={"patient_id": patient_id})
    return {"message": "Patient deleted"}


@router.post("/visits", response_model=VisitResponse)
def create_visit(visit: VisitCreate, db: Session = Depends(get_db)):
    if tracer:
        with tracer.start_as_current_span("api.create_visit"):
            return _create_visit_impl(visit, db)
    return _create_visit_impl(visit, db)


def _create_visit_impl(visit: VisitCreate, db: Session):
    patient = db.query(Patient).filter(Patient.id == visit.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    db_visit = Visit(**visit.model_dump())
    db.add(db_visit)
    db.commit()
    db.refresh(db_visit)
    logger.info("visit_created", extra={"visit_id": db_visit.id, "patient_id": db_visit.patient_id})
    return db_visit


@router.get("/visits/{visit_id}", response_model=VisitResponse)
def get_visit(visit_id: int, db: Session = Depends(get_db)):
    if tracer:
        with tracer.start_as_current_span("api.get_visit"):
            return _get_visit_impl(visit_id, db)
    return _get_visit_impl(visit_id, db)


def _get_visit_impl(visit_id: int, db: Session):
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    return visit


@router.get("/patients/{patient_id}/visits", response_model=List[VisitResponse])
def get_patient_visits(patient_id: int, db: Session = Depends(get_db)):
    if tracer:
        with tracer.start_as_current_span("api.get_patient_visits"):
            return _get_patient_visits_impl(patient_id, db)
    return _get_patient_visits_impl(patient_id, db)


def _get_patient_visits_impl(patient_id: int, db: Session):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient.visits
