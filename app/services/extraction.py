import json
import re
import logging
from google import genai
from app.core.config import GEMINI_API_KEY, GEMINI_TRANSCRIPTION_MODEL

logger = logging.getLogger(__name__)

COMBINED_PROMPT = """You are a medical AI assistant for Bangladeshi doctor-patient conversations.

The user will provide an audio recording of a doctor-patient consultation in Bangla, English, or mixed Banglish (code-switched).

Your job:
1. TRANSCRIBE the conversation exactly as spoken — keep Bangla in Bangla script, keep English words/terms as-is
2. EXTRACT structured patient and visit information from the transcribed content
3. Provide a CONFIDENCE rating for every extracted field

Return ONLY a raw JSON object with no markdown formatting, no code fences, no explanation.

The JSON must have exactly four keys: "transcript", "patient", "visit", "confidence".

=== transcript (string) ===
Full verbatim transcript of the conversation.

=== patient (object) ===
Extract these fields if explicitly mentioned. Translate all values to English.
- name (string or null)
- age (integer or null)
- gender (string: "male", "female", or null)
- phone (string or null)
- address (string or null)
- blood_type (string or null)
- allergies (string or null)
- emergency_contact (string or null)

=== visit (object) ===
Extract these fields if explicitly mentioned. Translate all values to English.
- chief_complaint (string or null) — the main reason for the visit
- symptoms (string or null) — specific symptoms described
- diagnosis (string or null) — diagnosis given
- tests (string or null) — tests/lab work ordered
- prescription (string or null) — medicines prescribed with dosage
- suggestions (string or null) — doctor's advice/recommendations
- notes (string or null) — any other important clinical notes
- visit_type (string: "initial" or "follow_up") — based on context
- summary (string or null) — brief English summary of the consultation

=== confidence (object) ===
For each field in "patient" and "visit", provide a confidence rating:
- "high" — explicitly and unambiguously stated in the conversation
- "medium" — implied, partially stated, or requiring translation
- "low" — weakly inferred, significant uncertainty
- null — field was not mentioned at all (confidence should also be null)

Structure:
{
  "patient": {
    "name": "high"|"medium"|"low"|null,
    "age": ...,
    ...
  },
  "visit": {
    "chief_complaint": ...,
    ...
  }
}

=== Critical null-safety rules ===
1. Set a field to null if the information was NOT explicitly mentioned in the conversation. Do NOT invent or hallucinate.
2. "Not mentioned" → null. "Not sure" → null. "Maybe" → "low" confidence.
3. When in doubt, prefer null over guessing.
4. Only extract information that a reasonable doctor would conclude from the conversation.
5. Bangla-English code-switching is normal — do not flag mixed language as an error.
"""

client = None


def get_client() -> genai.Client:
    global client
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required for Gemini.")
    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)
    return client


async def process_audio_direct(audio_path: str) -> dict:
    """
    Send audio directly to Gemini for combined transcription + structured extraction
    in a single call. Returns dict with keys: transcript, patient, visit, confidence.
    """
    try:
        gemini_client = get_client()
        uploaded_file = gemini_client.files.upload(file=audio_path)
        response = gemini_client.models.generate_content(
            model=GEMINI_TRANSCRIPTION_MODEL,
            contents=[COMBINED_PROMPT, uploaded_file],
        )

        content = (response.text or "").strip() if hasattr(response, "text") else str(response).strip()

        content = re.sub(r'^```(?:json)?\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
        content = content.strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise

        logger.info(
            "gemini_audio_processed",
            extra={
                "has_transcript": bool(data.get("transcript")),
                "has_patient": "patient" in data,
                "has_visit": "visit" in data,
                "has_confidence": "confidence" in data,
            },
        )
        return data
    except Exception as e:
        logger.error("gemini_audio_failed", extra={"error": str(e), "path": audio_path})
        raise


async def extract_data(transcript: str) -> dict:
    """
    Legacy: extract structured data from an already-transcribed text.
    Uses Gemini with the same combined prompt (minus the audio upload).
    Used as fallback or for text-only processing.
    """
    if not transcript:
        return {"patient": {}, "visit": {}, "confidence": {}, "transcript": ""}

    text_prompt = COMBINED_PROMPT.replace(
        "The user will provide an audio recording",
        "The user will provide a transcript"
    )
    text_prompt += f"\n\nTranscript:\n{transcript}"

    try:
        gemini_client = get_client()
        response = gemini_client.models.generate_content(
            model=GEMINI_TRANSCRIPTION_MODEL,
            contents=[text_prompt],
        )

        content = (response.text or "").strip() if hasattr(response, "text") else str(response).strip()

        content = re.sub(r'^```(?:json)?\s*', '', content, flags=re.MULTILINE)
        content = re.sub(r'\s*```$', '', content, flags=re.MULTILINE)
        content = content.strip()

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                raise

        logger.info("extraction_done", extra={"has_patient": "patient" in data, "has_visit": "visit" in data})
        return data
    except Exception as e:
        logger.error("extraction_failed", extra={"error": str(e)})
        raise
