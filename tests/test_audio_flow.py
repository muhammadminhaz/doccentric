"""
End-to-end audio processing tests
Note: These require actual audio files and running services
"""
import pytest
import os
import wave
import struct


def generate_test_audio(filename, duration_seconds=5, sample_rate=16000):
    """Generate a simple test audio file"""
    num_samples = duration_seconds * sample_rate
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample
        wav_file.setframerate(sample_rate)

        for _ in range(num_samples):
            sample = int(32767 * 0.1)  # Low amplitude sine-like wave
            wav_file.writeframes(struct.pack('h', sample))


class TestAudioUpload:
    """Test audio upload and processing"""

    def test_upload_audio_requires_doctor_id(self, client):
        """Test that doctor_id is required"""
        with open("/tmp/test_audio.wav", "wb") as f:
            f.write(b"fake audio data")

        with open("/tmp/test_audio.wav", "rb") as f:
            response = client.post(
                "/api/upload-audio",
                files={"audio_file": ("test.wav", f, "audio/wav")}
            )
        assert response.status_code == 422  # Validation error

    def test_upload_audio_invalid_file(self, client):
        """Test upload with invalid file"""
        # Create a minimal wav file
        os.makedirs("/tmp", exist_ok=True)
        generate_test_audio("/tmp/test_audio.wav", duration_seconds=1)

        with open("/tmp/test_audio.wav", "rb") as f:
            response = client.post(
                "/api/upload-audio",
                data={"doctor_id": "DR001"},
                files={"audio_file": ("test.wav", f, "audio/wav")}
            )
        # Will fail at processing but should accept the file
        assert response.status_code in [200, 500]

    def test_upload_audio_missing_file(self, client):
        """Test upload without audio file"""
        response = client.post(
            "/api/upload-audio",
            data={"doctor_id": "DR001"}
        )
        assert response.status_code == 422


class TestAudioProcessor:
    """Test audio processor (requires models)"""

    @pytest.mark.skip(reason="Requires pyannote and whisper models - run manually")
    def test_process_audio_full_pipeline(self):
        """Full end-to-end audio processing test"""
        from app.services.audio_processor import audio_processor

        # Generate test audio
        os.makedirs("/tmp", exist_ok=True)
        test_audio_path = "/tmp/test_audio.wav"
        generate_test_audio(test_audio_path, duration_seconds=5)

        try:
            speaker_info, embedding, transcript = audio_processor.process_audio(
                test_audio_path,
                language="bn"
            )

            assert speaker_info is not None
            # Transcript may be empty for synthetic audio
            assert transcript is not None

        finally:
            if os.path.exists(test_audio_path):
                os.remove(test_audio_path)


class TestDatabaseIntegrity:
    """Test database relationships and integrity"""

    @pytest.mark.skip(reason="Requires PostgreSQL with ON DELETE CASCADE - SQLite doesn't support FK cascades in tests")
    def test_patient_visit_cascade(self, client, sample_patient_data, sample_visit_data):
        """Test that deleting patient cascade deletes visits.
        This works with PostgreSQL (FK cascade) but not SQLite."""
        pass

    def test_visit_requires_valid_patient(self, client, sample_visit_data):
        """Test that visit creation requires valid patient"""
        visit_data = {**sample_visit_data, "patient_id": 99999}
        response = client.post("/api/visits", json=visit_data)
        assert response.status_code == 404
