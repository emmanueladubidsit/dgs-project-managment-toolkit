"""Speech-to-text behind a provider interface. The core app never depends on a provider.

Providers: "faster-whisper" (local, optional `uv sync --extra voice`) or "none". Audio never
leaves the machine with the local provider. Cloud providers can be added by implementing
`TranscriptionProvider` without touching the API."""

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.config import get_settings

log = logging.getLogger("app.transcription")


@dataclass
class Transcription:
    text: str
    duration_seconds: float | None
    provider: str


class TranscriptionUnavailable(RuntimeError):
    pass


class TranscriptionProvider(Protocol):
    name: str

    def available(self) -> tuple[bool, str]: ...

    def transcribe(self, path: Path) -> Transcription: ...


class NoProvider:
    name = "none"

    def available(self) -> tuple[bool, str]:
        return False, (
            "No transcription provider is configured. Type or paste the text instead, "
            "or install local Whisper with `uv sync --extra voice`."
        )

    def transcribe(self, path: Path) -> Transcription:
        raise TranscriptionUnavailable(self.available()[1])


@lru_cache(maxsize=2)
def _load_model(name: str):
    """Loaded once per process and model name (loading takes seconds)."""
    from faster_whisper import WhisperModel

    log.info("Loading Whisper model %s", name)
    return WhisperModel(name, device="cpu", compute_type="int8")


class FasterWhisperProvider:
    name = "faster-whisper"

    def __init__(self, model: str):
        self.model_name = model

    def available(self) -> tuple[bool, str]:
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return False, "Local Whisper is not installed. Run `uv sync --extra voice` in backend/."
        return True, (
            f"Local Whisper (“{self.model_name}” model). Audio stays on this machine. "
            "The model downloads once on first use."
        )

    def transcribe(self, path: Path) -> Transcription:
        ok, msg = self.available()
        if not ok:
            raise TranscriptionUnavailable(msg)
        segments, info = _load_model(self.model_name).transcribe(
            str(path), language="en", vad_filter=True
        )
        text = " ".join(s.text.strip() for s in segments).strip()
        return Transcription(text=text, duration_seconds=info.duration, provider=self.name)


def get_provider() -> TranscriptionProvider:
    s = get_settings()
    choice = s.transcription_provider
    if choice == "none":
        return NoProvider()
    whisper = FasterWhisperProvider(s.whisper_model)
    if choice == "faster-whisper" or whisper.available()[0]:
        return whisper
    return NoProvider()
