import os
import numpy as np
from typing import List, Tuple, Optional
import torch


class AudioProcessor:
    def __init__(self):
        self.diarization_pipeline = None
        self.embedding_model = None
        self.whisper_model = None

    def load_diarization(self):
        if self.diarization_pipeline is None:
            from pyannote.audio import Pipeline
            self.diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=os.getenv("HUGGING_FACE_TOKEN")
            )
        return self.diarization_pipeline

    def load_embedding_model(self):
        if self.embedding_model is None:
            from speechbrain.inference import EncodecEmbedding
            self.embedding_model = EncodecEmbedding.from_hparams(
                source="speechbrain/spkrec-ecapa-voxceleb",
                savedir="pretrained_models/spkrec-ecapa-voxceleb"
            )
        return self.embedding_model

    def load_whisper(self, model_size: str = "base"):
        if self.whisper_model is None:
            import whisper
            self.whisper_model = whisper.load_model(model_size)
        return self.whisper_model

    def process_audio(
        self,
        audio_path: str,
        min_segment_duration: float = 1.0,
        language: str = "bn"
    ) -> Tuple[dict, Optional[np.ndarray], str]:
        diarization_pipeline = self.load_diarization()
        waveform = self._load_audio(audio_path)

        diarization = diarization_pipeline(audio_path)

        patient_segments = []
        doctor_segments = []

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segment_duration = turn.end - turn.start
            if segment_duration < min_segment_duration:
                continue

            if "SPEAKER_01" in speaker:
                patient_segments.append((turn.start, turn.end))
            else:
                doctor_segments.append((turn.start, turn.end))

        patient_embedding = self._extract_embedding(waveform, patient_segments)

        transcript = self._transcribe_audio(audio_path, language)

        speaker_info = {
            "patient_segments": patient_segments,
            "doctor_segments": doctor_segments
        }

        return speaker_info, patient_embedding, transcript

    def _load_audio(self, audio_path: str):
        import torchaudio
        waveform, sample_rate = torchaudio.load(audio_path)
        if sample_rate != 16000:
            import torchaudio.functional as F
            waveform = F.resample(waveform, sample_rate, 16000)
        return waveform

    def _extract_embedding(
        self,
        waveform,
        segments: List[Tuple[float, float]]
    ) -> Optional[np.ndarray]:
        if not segments:
            return None

        embedding_model = self.load_embedding_model()
        embeddings = []

        import torchaudio

        for start, end in segments:
            start_sample = int(start * 16000)
            end_sample = int(end * 16000)

            segment = waveform[:, start_sample:end_sample]

            if segment.shape[1] < 1600:
                continue

            embedding = embedding_model.encode_batch(segment)
            embeddings.append(embedding.squeeze().cpu().numpy())

        if embeddings:
            return np.mean(embeddings, axis=0)
        return None

    def _transcribe_audio(self, audio_path: str, language: str = "bn") -> str:
        whisper_model = self.load_whisper()
        result = whisper_model.transcribe(audio_path, language=language)
        return result["text"]


audio_processor = AudioProcessor()
