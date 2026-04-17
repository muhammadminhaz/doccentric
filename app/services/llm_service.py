import ollama
from typing import Optional


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
        prompt = """Extract patient information from this transcript. Return a JSON with these fields if found:
- name
- age
- gender
- phone

If information is not explicitly stated, leave the field null. Only return valid JSON.

Transcript:
"""

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
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {}

    def generate_visit_notes(
        self,
        transcript: str,
        patient_name: str,
        symptoms: str
    ) -> str:
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

        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )

        return response["message"]["content"]


llm_service = LLMService()