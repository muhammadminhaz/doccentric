from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(20))
    phone = Column(String(20), unique=True, index=True)
    email = Column(String(255))
    address = Column(Text)
    blood_type = Column(String(5))
    allergies = Column(Text)
    emergency_contact = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    visits = relationship("Visit", back_populates="patient")
    voice_embeddings = relationship("VoiceEmbedding", back_populates="patient")


class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String(100), nullable=False)
    date = Column(DateTime(timezone=True), server_default=func.now())
    chief_complaint = Column(Text)
    symptoms = Column(Text)
    diagnosis = Column(Text)
    tests = Column(Text)
    prescription = Column(Text)
    suggestions = Column(Text)
    notes = Column(Text)
    visit_type = Column(String(50), default="initial")
    transcript = Column(Text)
    summary = Column(Text)

    patient = relationship("Patient", back_populates="visits")
    audio_records = relationship("AudioRecord", back_populates="visit")


class VoiceEmbedding(Base):
    __tablename__ = "voice_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    embedding_vector = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    embedding_version = Column(String(20), default="1.0")

    patient = relationship("Patient", back_populates="voice_embeddings")


class AudioRecord(Base):
    __tablename__ = "audio_records"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255))
    duration = Column(Float)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    visit = relationship("Visit", back_populates="audio_records")