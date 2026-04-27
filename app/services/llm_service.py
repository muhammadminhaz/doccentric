import ollama
from typing import Optional

from app.core.logging import get_logger, log_timing
from app.core.observability import get_tracer

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class LLMService:
    def __init__(self, model: str = "phi4-mini"):
        self.model = model

    def check_connection(self) -> bool:
        try:
            ollama.list()
            return True
        except Exception:
            return False

    def summarize_transcript(
        self,
        transcript: str,
        prompt: Optional[str] = None
    ) -> str:
        if tracer:
            with tracer.start_as_current_span("llm.summarize_transcript"):
                return self._summarize_transcript_impl(transcript, prompt)
        return self._summarize_transcript_impl(transcript, prompt)

    def _summarize_transcript_impl(
        self,
        transcript: str,
        prompt: Optional[str] = None,
    ) -> str:
        if prompt is None:
            prompt = """You are a medical assistant. Analyze this doctor-patient conversation transcript and extract:
The conversation may contain Bengali (Bangla) and English mixed. Extract:
1. Chief complaint (main health issue)
2. Symptoms described
3. Diagnosis if mentioned
4. Tests ordered if any
5. Prescription if mentioned
6. Suggestions or advice given
7. Any important notes

Return a structured summary in English. If something is not mentioned, say "Not mentioned".

Transcript:
"""

        full_prompt = f"{prompt}{transcript}"

        with log_timing(logger, "llm_chat_summarize", model=self.model, transcript_len=len(transcript)):
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": full_prompt}]
            )

        return response["message"]["content"]

    def extract_patient_info(
        self,
        transcript: str,
        existing_info: Optional[dict] = None
    ) -> dict:
        if tracer:
            with tracer.start_as_current_span("llm.extract_patient_info"):
                return self._extract_patient_info_impl(transcript, existing_info)
        return self._extract_patient_info_impl(transcript, existing_info)

    def _extract_patient_info_impl(
        self,
        transcript: str,
        existing_info: Optional[dict] = None
    ) -> dict:
        prompt = """Extract patient information from this transcript. Return a JSON with these fields if found:
- name
- age
- gender
- phone

If information is not explicitly stated, leave the field null. Only return valid JSON.

Transcript:
"""

        with log_timing(logger, "llm_chat_extract_info", model=self.model, transcript_len=len(transcript)):
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": f"{prompt}{transcript}"}]
            )

        content = response["message"]["content"]

        import json
        import re

        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                logger.info(
                    "llm_extract_info_ok",
                    extra={"fields": sorted(list(parsed.keys())) if isinstance(parsed, dict) else None},
                )
                return parsed
            except json.JSONDecodeError:
                pass

        logger.info("llm_extract_info_failed")
        return {}

    def generate_visit_notes(
        self,
        transcript: str,
        patient_name: str,
        symptoms: str
    ) -> str:
        if tracer:
            with tracer.start_as_current_span("llm.generate_visit_notes"):
                return self._generate_visit_notes_impl(transcript, patient_name, symptoms)
        return self._generate_visit_notes_impl(transcript, patient_name, symptoms)

    def _generate_visit_notes_impl(self, transcript: str, patient_name: str, symptoms: str) -> str:
        prompt = f"""As a medical scribe, create professional visit notes for a patient consultation.

Patient Name: {patient_name}
Reported Symptoms: {symptoms}

Transcript:
{transcript}

Create structured notes with:
- Subjective (patient's complaints and history)
- Objective (examinations and findings)
- Assessment (diagnosis)
- Plan (treatment and follow-up)

Return only the structured notes, no preamble.
"""

        with log_timing(logger, "llm_chat_visit_notes", model=self.model, transcript_len=len(transcript)):
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )

        return response["message"]["content"]


llm_service = LLMService()
