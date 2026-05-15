import os
import shutil
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import AUDIO_UPLOAD_DIR
from app.core.logging import get_logger, log_timing
from app.core.observability import get_tracer
from app.models.models import Patient, Visit, AudioRecord
from app.models.schemas import AudioUploadResponse
from app.services.extraction import process_audio_direct

router = APIRouter()
logger = get_logger(__name__)
tracer = get_tracer(__name__)

UPLOAD_DIR = AUDIO_UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload-audio")
async def upload_audio(
    doctor_id: str = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if tracer:
        with tracer.start_as_current_span("api.upload_audio"):
            return await _upload_audio_impl(doctor_id=doctor_id, audio_file=audio_file, db=db)
    return await _upload_audio_impl(doctor_id=doctor_id, audio_file=audio_file, db=db)


async def _upload_audio_impl(doctor_id: str, audio_file: UploadFile, db: Session):
    file_ext = os.path.splitext(audio_file.filename)[1] or ".wav"
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with log_timing(logger, "audio_save_start", file_ext=file_ext):
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(audio_file.file, buffer)

        logger.info(
            "audio_saved",
            extra={"file_name": audio_file.filename, "file_path": file_path},
        )

        # Single Gemini call: audio -> transcript + patient info + visit data + confidence
        with log_timing(logger, "gemini_audio_direct_start"):
            result = await process_audio_direct(file_path)
            transcript = result.get("transcript", "")
            extracted_info = result.get("patient", {})
            visit_data = result.get("visit", {})
            confidence = result.get("confidence", {})

        # Patient matching purely from Gemini-extracted fields (phone unique, name fallback)
        patient = None
        is_new_patient = False

        patient_name = extracted_info.get("name") or "Unknown"
        patient_age = extracted_info.get("age") or 0
        patient_phone = extracted_info.get("phone") or None
        patient_gender = extracted_info.get("gender")

        if patient_phone:
            existing = db.query(Patient).filter(
                Patient.phone == patient_phone
            ).first()
            if existing:
                patient = existing
                is_new_patient = False

        if patient is None and patient_name != "Unknown":
            existing = db.query(Patient).filter(
                Patient.name == patient_name
            ).first()
            if existing:
                patient = existing
                is_new_patient = False

        if patient is None:
            is_new_patient = True
            logger.info("patient_create_start")
            patient = Patient(
                name=patient_name,
                age=patient_age,
                phone=patient_phone,
                gender=patient_gender
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
            logger.info("patient_created", extra={"patient_id": patient.id})

        logger.info(
            "visit_create_start",
            extra={"patient_id": patient.id, "doctor_id": doctor_id, "is_new_patient": is_new_patient},
        )
        visit = Visit(
            patient_id=patient.id,
            doctor_id=doctor_id,
            transcript=transcript,
            visit_type=visit_data.get("visit_type") or ("initial" if is_new_patient else "follow-up"),
            chief_complaint=visit_data.get("chief_complaint"),
            symptoms=visit_data.get("symptoms"),
            diagnosis=visit_data.get("diagnosis"),
            tests=visit_data.get("tests"),
            prescription=visit_data.get("prescription"),
            suggestions=visit_data.get("suggestions"),
            notes=visit_data.get("notes"),
            summary=visit_data.get("summary")
        )
        db.add(visit)
        db.commit()
        db.refresh(visit)
        logger.info("visit_created", extra={"visit_id": visit.id, "patient_id": patient.id})

        audio_record = AudioRecord(
            visit_id=visit.id,
            file_path=file_path,
            file_name=audio_file.filename
        )
        db.add(audio_record)
        db.commit()
        logger.info("audio_record_saved", extra={"visit_id": visit.id})

        return AudioUploadResponse(
            patient_id=patient.id,
            patient_name=patient.name,
            is_new_patient=is_new_patient,
            visit_id=visit.id,
            transcript=transcript,
            summary=visit.summary,
            confidence=confidence
        )

    except Exception as e:
        logger.exception("upload_audio_failed", extra={"file_path": file_path})
        raise HTTPException(
            status_code=500,
            detail=f"Error processing audio: {str(e)}"
        )
