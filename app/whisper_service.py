"""Singleton wrapper around openai-whisper for Persian (fa) transcription."""
import threading
from typing import Any

import whisper

from .config import settings


_model: Any = None
_lock = threading.Lock()


def get_model() -> Any:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = whisper.load_model(
                    settings.whisper_model_size,
                    device=settings.whisper_device,
                )
    return _model


def transcribe_file(path: str, language: str | None = None) -> dict[str, Any]:
    """Transcribe an audio file on disk. Defaults to Persian."""
    model = get_model()
    lang = language or settings.whisper_default_language
    result = model.transcribe(
        path,
        language=lang,
        initial_prompt="لطفا گفتار فارسی را به متن فارسی دقیق تبدیل کن.",
    )
    seg_list = [{"start": s["start"], "end": s["end"], "text": s["text"].strip()} for s in result["segments"]]
    full_text = result["text"].strip()
    duration = result.get("duration")
    if duration is None and seg_list:
        duration = seg_list[-1]["end"]
    return {
        "text": full_text,
        "language": result["language"],
        "duration": duration,
        "segments": seg_list,
    }
