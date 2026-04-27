import json
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.models import Patient, VoiceEmbedding
from typing import Optional, Tuple

from app.core.logging import get_logger, log_timing
from app.core.observability import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class VoiceMatchingService:
    def __init__(self, similarity_threshold: float = 0.75):
        self.similarity_threshold = similarity_threshold

    def find_matching_patient(
        self,
        db: Session,
        embedding: np.ndarray
    ) -> Optional[Tuple[Patient, float]]:
        if tracer:
            with tracer.start_as_current_span("voice.find_matching_patient"):
                return self._find_matching_patient_impl(db, embedding)
        return self._find_matching_patient_impl(db, embedding)

    def _find_matching_patient_impl(
        self,
        db: Session,
        embedding: np.ndarray
    ) -> Optional[Tuple[Patient, float]]:
        with log_timing(logger, "voice_embeddings_load"):
            embeddings = db.query(VoiceEmbedding).all()

        if not embeddings:
            return None

        best_match = None
        best_similarity = 0.0

        with log_timing(logger, "voice_similarity_scan", embedding_count=len(embeddings)):
            for voice_embedding in embeddings:
                stored_vector = json.loads(voice_embedding.embedding_vector)

                if isinstance(stored_vector, list):
                    stored_vector = np.array(stored_vector)

                similarity = self._cosine_similarity(embedding, stored_vector)

                if similarity > best_similarity:
                    best_similarity = similarity
                    patient = db.query(Patient).filter(
                        Patient.id == voice_embedding.patient_id
                    ).first()

                    if patient:
                        best_match = (patient, similarity)

        if best_match and best_similarity >= self.similarity_threshold:
            logger.info(
                "voice_match_found",
                extra={"patient_id": best_match[0].id, "similarity": best_similarity},
            )
            return best_match

        logger.info("voice_match_not_found", extra={"best_similarity": best_similarity})
        return None

    def register_voice_embedding(
        self,
        db: Session,
        patient_id: int,
        embedding: np.ndarray,
        version: str = "1.0"
    ) -> VoiceEmbedding:
        if tracer:
            with tracer.start_as_current_span("voice.register_voice_embedding"):
                return self._register_voice_embedding_impl(db, patient_id, embedding, version)
        return self._register_voice_embedding_impl(db, patient_id, embedding, version)

    def _register_voice_embedding_impl(
        self,
        db: Session,
        patient_id: int,
        embedding: np.ndarray,
        version: str,
    ) -> VoiceEmbedding:
        embedding_list = embedding.tolist()

        voice_embedding = VoiceEmbedding(
            patient_id=patient_id,
            embedding_vector=json.dumps(embedding_list),
            embedding_version=version
        )

        db.add(voice_embedding)
        db.commit()
        db.refresh(voice_embedding)

        logger.info(
            "voice_embedding_saved",
            extra={"patient_id": patient_id, "embedding_id": voice_embedding.id, "version": version},
        )
        return voice_embedding

    def _cosine_similarity(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray
    ) -> float:
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def update_embedding(
        self,
        db: Session,
        patient_id: int,
        new_embedding: np.ndarray,
        version: str = "1.0"
    ) -> VoiceEmbedding:
        if tracer:
            with tracer.start_as_current_span("voice.update_embedding"):
                return self._update_embedding_impl(db, patient_id, new_embedding, version)
        return self._update_embedding_impl(db, patient_id, new_embedding, version)

    def _update_embedding_impl(
        self,
        db: Session,
        patient_id: int,
        new_embedding: np.ndarray,
        version: str,
    ) -> VoiceEmbedding:
        embeddings = db.query(VoiceEmbedding).filter(
            VoiceEmbedding.patient_id == patient_id
        ).all()

        avg_embedding = new_embedding
        if embeddings:
            existing_embeddings = [
                np.array(json.loads(e.embedding_vector)) for e in embeddings
            ]
            all_embeddings = existing_embeddings + [new_embedding]
            avg_embedding = np.mean(all_embeddings, axis=0)

        logger.info(
            "voice_embedding_update",
            extra={"patient_id": patient_id, "previous_count": len(embeddings)},
        )
        return self.register_voice_embedding(
            db, patient_id, avg_embedding, version
        )


voice_matching_service = VoiceMatchingService()
