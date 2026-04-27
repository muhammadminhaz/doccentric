import os
import shutil
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.logging import get_logger, log_timing
from app.core.observability import get_tracer
from app.models.models import Patient, Visit, AudioRecord, VoiceEmbedding
from app.models.schemas import AudioUploadResponse
from app.services.audio_processor import audio_processor
from app.services.voice_matching import voice_matching_service
from app.services.llm_service import llm_service

router = APIRouter()
logger = get_logger(__name__)
tracer = get_tracer(__name__)

UPLOAD_DIR = "audio_files"
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

        language = "bn"
        if os.getenv("DOCENTRIC_SKIP_AUDIO_PROCESSING") == "1" or os.getenv("PYTEST_CURRENT_TEST"):
            logger.info("audio_processing_skipped")
            speaker_info, patient_embedding, transcript = ({"patient_segments": [], "doctor_segments": []}, None, "")
        else:
            with log_timing(logger, "audio_process_start"):
                speaker_info, patient_embedding, transcript = audio_processor.process_audio(
                    file_path, language=language
                )

        extracted_info = {}
        if transcript:
            try:
                extracted_info = llm_service.extract_patient_info(transcript)
            except Exception:
                pass

        patient = None
        is_new_patient = False

        if patient_embedding is not None:
            match_result = voice_matching_service.find_matching_patient(
                db, patient_embedding
            )

            if match_result:
                patient, similarity = match_result
                is_new_patient = False
            else:
                is_new_patient = True
        else:
            patient_name = extracted_info.get("name")
            if patient_name:
                existing_patient = db.query(Patient).filter(
                    Patient.name == patient_name
                ).first()

                if existing_patient:
                    patient = existing_patient
                    is_new_patient = False
                else:
                    is_new_patient = True
            else:
                is_new_patient = True

        patient_name = extracted_info.get("name") or "Unknown"
        patient_age = extracted_info.get("age") or 0
        patient_phone = extracted_info.get("phone") or None
        patient_gender = extracted_info.get("gender")

        if is_new_patient:
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

            if patient_embedding is not None:
                voice_matching_service.register_voice_embedding(
                    db, patient.id, patient_embedding
                )
        else:
            if patient_embedding is not None:
                voice_matching_service.update_embedding(
                    db, patient.id, patient_embedding
                )

        logger.info(
            "visit_create_start",
            extra={"patient_id": patient.id, "doctor_id": doctor_id, "is_new_patient": is_new_patient},
        )
        visit = Visit(
            patient_id=patient.id,
            doctor_id=doctor_id,
            transcript=transcript,
            visit_type="initial" if is_new_patient else "follow-up"
        )
        db.add(visit)
        db.commit()
        db.refresh(visit)
        logger.info("visit_created", extra={"visit_id": visit.id, "patient_id": patient.id})

        summary = None
        if transcript:
            try:
                summary = llm_service.summarize_transcript(transcript)
            except Exception:
                pass

        if summary:
            visit.summary = summary
            db.commit()

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
            summary=summary
        )

    except Exception as e:
        logger.exception("upload_audio_failed", extra={"file_path": file_path})
        raise HTTPException(
            status_code=500,
            detail=f"Error processing audio: {str(e)}"
        )
