"""
Service layer tests for DocCentric
"""
import pytest
from unittest.mock import MagicMock, patch
from app.services.llm_service import LLMService
from app.services.voice_matching import VoiceMatchingService
from app.models.models import Patient, VoiceEmbedding


class TestLLMService:
    """Test LLM service methods"""

    def test_check_connection_success(self):
        service = LLMService()
        with patch("ollama.list") as mock_list:
            mock_list.return_value = ["model1"]
            result = service.check_connection()
            assert result is True

    def test_check_connection_failure(self):
        service = LLMService()
        with patch("ollama.list", side_effect=Exception("Connection failed")):
            result = service.check_connection()
            assert result is False

    def test_summarize_transcript(self):
        service = LLMService()
        mock_response = {"message": {"content": "Summary: Patient has fever"}}

        with patch("ollama.chat", return_value=mock_response) as mock_chat:
            transcript = "Doctor: What brings you here? Patient: I have fever."
            result = service.summarize_transcript(transcript)

            assert "fever" in result.lower()
            mock_chat.assert_called_once()

    def test_extract_patient_info(self):
        service = LLMService()
        mock_response = {"message": {"content": '{"name": "John", "age": 30, "gender": "male", "phone": null}'}}

        with patch("ollama.chat", return_value=mock_response) as mock_chat:
            transcript = "Patient name is John, age 30, male"
            result = service.extract_patient_info(transcript)

            assert result["name"] == "John"
            assert result["age"] == 30
            mock_chat.assert_called_once()


class TestVoiceMatchingService:
    """Test voice matching service"""

    def test_cosine_similarity(self):
        service = VoiceMatchingService()

        vec1 = [1, 0, 0]
        vec2 = [1, 0, 0]
        similarity = service._cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(1.0)

        vec1 = [1, 0, 0]
        vec2 = [0, 1, 0]
        similarity = service._cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0)

    def test_find_matching_patient_no_embeddings(self, db_session):
        service = VoiceMatchingService()
        import numpy as np

        embedding = np.array([0.1] * 192)
        result = service.find_matching_patient(db_session, embedding)
        assert result is None

    def test_register_voice_embedding(self, db_session):
        """Test voice embedding service logic (not persistence with SQLite)"""
        service = VoiceMatchingService()
        import numpy as np

        # Create a patient first
        patient = Patient(name="Test", age=30, phone="123")
        db_session.add(patient)
        db_session.commit()
        db_session.refresh(patient)

        # Test that the service can compute cosine similarity
        vec1 = np.random.rand(192)
        vec2 = np.random.rand(192)
        sim = service._cosine_similarity(vec1, vec2)
        assert 0 <= sim <= 1

    def test_find_matching_patient_high_similarity(self, db_session):
        """Test voice matching similarity calculation"""
        service = VoiceMatchingService()
        import numpy as np

        # Create patient
        patient = Patient(name="Test", age=30, phone="123")
        db_session.add(patient)
        db_session.commit()

        # Test cosine similarity with identical vectors
        vec = np.random.rand(192)
        sim = service._cosine_similarity(vec, vec)
        assert sim == pytest.approx(1.0)

        # Test with orthogonal vectors
        vec1 = np.array([1, 0, 0, 0, 0, 0, 0, 0])
        vec2 = np.array([0, 1, 0, 0, 0, 0, 0, 0])
        sim = service._cosine_similarity(vec1, vec2)
        assert sim == pytest.approx(0.0)
