import logging
from google import genai
from app.core.config import (
    GEMINI_API_KEY,
    GEMINI_TRANSCRIPTION_MODEL,
    TRANSCRIPTION_LANGUAGE,
)

logger = logging.getLogger(__name__)

TRANSCRIPTION_PROMPT = """Transcribe this audio exactly.
Context: this is a Bangla doctor-patient conversation that may include English medical words, medicine names, acronyms, numbers, and code-switched phrases.
Transcribe exactly what is spoken.
Keep Bangla speech in Bangla script.
Keep English words, brand names, medicine names, and acronyms in English.
Do not translate, summarize, normalize, or rewrite the conversation.
Return only the transcript text. Do not include markdown, timestamps, labels, explanations, or a summary."""

client = None


def get_client() -> genai.Client:
    global client
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required for Gemini transcription.")
    if client is None:
        client = genai.Client(api_key=GEMINI_API_KEY)
    return client


def build_prompt(language: str | None) -> str:
    if not language:
        return TRANSCRIPTION_PROMPT

    return (
        f"{TRANSCRIPTION_PROMPT}\n"
        f"Primary expected language code: {language}. Preserve any English words exactly."
    )


def transcribe_audio_sync(audio_path: str, language: str | None = TRANSCRIPTION_LANGUAGE) -> str:
    try:
        gemini_client = get_client()
        uploaded_file = gemini_client.files.upload(file=audio_path)
        response = gemini_client.models.generate_content(
            model=GEMINI_TRANSCRIPTION_MODEL,
            contents=[build_prompt(language), uploaded_file],
        )

        transcript = (response.text or "").strip() if hasattr(response, "text") else str(response).strip()
        logger.info(
            "transcription_done",
            extra={
                "path": audio_path,
                "length": len(transcript),
                "model": GEMINI_TRANSCRIPTION_MODEL,
            },
        )
        return transcript
    except Exception as e:
        logger.error("transcription_failed", extra={"error": str(e), "path": audio_path})
        raise


async def transcribe_audio(audio_path: str) -> str:
    return transcribe_audio_sync(audio_path)
