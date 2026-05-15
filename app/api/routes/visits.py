import os
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.config import AUDIO_UPLOAD_DIR
from app.core.database import get_db
from app.services.transcription import transcribe_audio
from app.services.extraction import extract_data
from app.services.patient_service import match_or_create_patient, create_visit, create_audio_record

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/visits", tags=["visits"])

UPLOAD_DIR = AUDIO_UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload-audio")
async def upload_audio(
    audio_file: UploadFile = File(...),
    doctor_id: str = Form(...),
    db: Session = Depends(get_db)
):
    # Save audio file
    file_path = os.path.join(UPLOAD_DIR, audio_file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(audio_file.file, f)
    
    # Transcribe
    try:
        transcript = await transcribe_audio(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    
    # Extract structured data
    extracted = None
    warning = None
    try:
        extracted = await extract_data(transcript)
    except Exception as e:
        warning = f"JSON extraction failed: {str(e)}"
        logger.warning("extraction_failed_continuing", extra={"error": str(e)})
    
    # Get patient and visit data
    patient_data = (extracted or {}).get("patient", {})
    visit_data = (extracted or {}).get("visit", {})
    
    # Match or create patient
    patient = match_or_create_patient(db, patient_data)
    
    # Create visit
    visit = create_visit(db, patient.id, doctor_id, visit_data, transcript)
    
    # Create audio record
    create_audio_record(db, visit.id, file_path, audio_file.filename)
    
    db.commit()
    
    response = {
        "patient_id": patient.id,
        "visit_id": visit.id,
        "transcript": transcript,
        "extracted_data": extracted
    }
    if warning:
        response["warning"] = warning
    
    return response
