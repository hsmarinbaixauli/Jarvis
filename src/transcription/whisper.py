"""Audio transcription via OpenAI Whisper.

Provides a single public function that converts a local audio file to text
using a locally-loaded Whisper model.  The model is loaded once and cached
at module level so repeated calls within the same process pay no reload cost.

The model size defaults to ``"base"`` but can be overridden at runtime via the
``WHISPER_MODEL`` environment variable; the value is read on the first call to
:func:`transcribe_audio`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import whisper


# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_model: Any | None = None


def _get_model() -> Any:
    """Return the cached Whisper model, loading it on first access."""
    global _model
    if _model is None:
        model_name: str = os.environ.get("WHISPER_MODEL", "base")
        _model = whisper.load_model(model_name)
    return _model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def transcribe_audio(audio_file_path: str) -> str:
    """Transcribe a local audio file to text using Whisper.

    The Whisper model is loaded lazily on the first call and reused on all
    subsequent calls within the same process.  The model size is controlled by
    the ``WHISPER_MODEL`` environment variable (defaults to ``"base"``).

    Args:
        audio_file_path: Absolute or relative path to the audio file.  Any
            format supported by ``ffmpeg`` (WAV, MP3, M4A, FLAC, …) is
            accepted.

    Returns:
        The transcribed text as a plain string with leading/trailing whitespace
        stripped.

    Raises:
        FileNotFoundError: If *audio_file_path* does not point to an existing
            file.
    """
    path: Path = Path(audio_file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Audio file not found: {path}\n"
            "Ensure the path is correct and the file exists before calling transcribe_audio."
        )

    model: Any = _get_model()
    result: dict[str, Any] = model.transcribe(str(path), language="es")
    return result["text"].strip()
