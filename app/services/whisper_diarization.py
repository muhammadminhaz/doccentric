from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from app.core.config import (
    WHISPER_DIARIZATION_DEVICE,
    WHISPER_DIARIZATION_NO_STEM,
    WHISPER_DIARIZATION_REPO,
    WHISPER_DIARIZATION_SCRIPT,
    WHISPER_DIARIZATION_WHISPER_MODEL,
)
from app.core.logging import get_logger, log_timing


logger = get_logger(__name__)


class WhisperDiarizationError(RuntimeError):
    pass


@dataclass(frozen=True)
class DiarizationResult:
    transcript: str
    speaker_segments: Dict[str, List[Tuple[float, float]]]


_SRT_TS_RE = re.compile(
    r"^(?P<h1>\d{2}):(?P<m1>\d{2}):(?P<s1>\d{2}),(?P<ms1>\d{3})\s+-->\s+"
    r"(?P<h2>\d{2}):(?P<m2>\d{2}):(?P<s2>\d{2}),(?P<ms2>\d{3})\s*$"
)


def _ts_to_seconds(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + (int(ms) / 1000.0)


def _parse_srt(srt_path: Path) -> DiarizationResult:
    text = srt_path.read_text(encoding="utf-8", errors="replace")
    lines = [ln.rstrip("\n") for ln in text.splitlines()]

    i = 0
    speaker_segments: Dict[str, List[Tuple[float, float]]] = {}
    transcript_parts: List[str] = []

    while i < len(lines):
        # SRT block: index, timestamp, payload line(s), blank line
        # We only care about timestamp + first payload line.
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break

        # index line
        i += 1
        if i >= len(lines):
            break

        ts_line = lines[i].strip()
        m = _SRT_TS_RE.match(ts_line)
        if not m:
            i += 1
            continue
        start = _ts_to_seconds(m["h1"], m["m1"], m["s1"], m["ms1"])
        end = _ts_to_seconds(m["h2"], m["m2"], m["s2"], m["ms2"])
        i += 1

        # payload line(s)
        payload = ""
        while i < len(lines) and lines[i].strip():
            if not payload:
                payload = lines[i].strip()
            i += 1

        if not payload:
            continue

        if ":" in payload:
            speaker, utterance = payload.split(":", 1)
            speaker = speaker.strip()
            utterance = utterance.strip()
        else:
            speaker = "SPEAKER_00"
            utterance = payload.strip()

        speaker_segments.setdefault(speaker, []).append((start, end))
        if utterance:
            transcript_parts.append(f"{speaker}: {utterance}")

    return DiarizationResult(transcript="\n".join(transcript_parts).strip(), speaker_segments=speaker_segments)


def diarize(audio_path: str, language: str = "bn") -> DiarizationResult:
    """
    Runs MahmoudAshraf97/whisper-diarization as an external pipeline and parses its SRT output.

    Setup (pick one):
    - Clone the repo and set `WHISPER_DIARIZATION_REPO=/path/to/whisper-diarization`
    - Or set `WHISPER_DIARIZATION_SCRIPT=/path/to/diarize.py`
    """
    audio = Path(audio_path)
    if not audio.exists():
        raise WhisperDiarizationError(f"Audio file not found: {audio_path}")

    script = WHISPER_DIARIZATION_SCRIPT
    if not script:
        repo = WHISPER_DIARIZATION_REPO
        if repo:
            script = str(Path(repo) / "diarize.py")

    if not script:
        raise WhisperDiarizationError(
            "Whisper diarization not configured. Set WHISPER_DIARIZATION_SCRIPT or WHISPER_DIARIZATION_REPO."
        )

    script_path = Path(script)
    if not script_path.exists():
        raise WhisperDiarizationError(f"whisper-diarization script not found: {script}")

    cmd = [sys.executable, str(script_path), "-a", str(audio)]

    if WHISPER_DIARIZATION_NO_STEM == "1":
        cmd.append("--no-stem")

    whisper_model = WHISPER_DIARIZATION_WHISPER_MODEL
    if whisper_model:
        cmd += ["--whisper-model", whisper_model]

    device = WHISPER_DIARIZATION_DEVICE
    cmd += ["--device", device]

    if language:
        cmd += ["--language", language]

    # diarize.py writes `<audio_basename>.srt` next to the audio file
    srt_path = audio.with_suffix(".srt")

    with log_timing(logger, "whisper_diarization_run", script=str(script_path), device=device):
        proc = subprocess.run(
            cmd,
            cwd=str(script_path.parent),
            capture_output=True,
            text=True,
        )

    if proc.returncode != 0:
        logger.error(
            "whisper_diarization_failed",
            extra={"returncode": proc.returncode, "stderr": proc.stderr[-4000:], "stdout": proc.stdout[-4000:]},
        )
        raise WhisperDiarizationError(f"whisper-diarization failed with exit code {proc.returncode}")

    if not srt_path.exists():
        raise WhisperDiarizationError(f"Expected SRT output not found: {srt_path}")

    with log_timing(logger, "whisper_diarization_parse_srt"):
        return _parse_srt(srt_path)
