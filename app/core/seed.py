from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.models import Doctor


logger = get_logger(__name__)


DUMMY_DOCTOR_ID = "BD-DR-0001"


def seed_dummy_doctor(db: Session) -> None:
    """
    Inserts a single dummy doctor row if it doesn't already exist.
    Safe to run multiple times.
    """
    existing = db.query(Doctor).filter(Doctor.id == DUMMY_DOCTOR_ID).first()
    if existing:
        return

    doctor = Doctor(
        id=DUMMY_DOCTOR_ID,
        name="Dr. Ayesha Rahman",
        specialty="General Medicine",
        phone="+8801710000000",
    )
    db.add(doctor)
    db.commit()
    logger.info("seeded_dummy_doctor", extra={"doctor_id": doctor.id})

