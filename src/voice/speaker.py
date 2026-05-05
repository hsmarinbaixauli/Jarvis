"""Text-to-speech output via pyttsx3.

Converts a text string to spoken audio through the default system TTS engine.
The pyttsx3 engine is initialised lazily at module level so it is created only
once per process, regardless of how many times :func:`speak` is called.
"""

from __future__ import annotations

import atexit
from typing import Any

import pyttsx3


# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_engine: Any | None = None


def _cleanup_engine() -> None:
    global _engine
    if _engine is not None:
        try:
            _engine.stop()
        except Exception:
            pass
        _engine = None


atexit.register(_cleanup_engine)


def _get_engine() -> Any:
    """Return the cached pyttsx3 engine, initialising it on first access.

    Returns:
        The initialised ``pyttsx3.Engine`` instance.

    Raises:
        RuntimeError: If ``pyttsx3.init()`` fails to create a TTS engine on
            the current platform.
    """
    global _engine
    if _engine is None:
        try:
            _engine = pyttsx3.init()
        except Exception as exc:
            raise RuntimeError(
                "Failed to initialise the pyttsx3 TTS engine. "
                "Ensure a supported speech-synthesis driver is available on "
                "this platform (e.g. SAPI5 on Windows, espeak on Linux, "
                "NSSpeechSynthesizer on macOS)."
            ) from exc
    return _engine


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def set_voice_properties(rate: int = 150, volume: float = 0.9) -> None:
    """Configure speaking rate and volume on the cached TTS engine.

    Can be called multiple times; each call updates the live engine without
    re-initialising it.  If the engine has not yet been created it will be
    initialised as a side-effect of this call.

    Args:
        rate: Speech rate in words per minute.  Defaults to ``150``.
        volume: Output volume in the range ``0.0`` (silent) to ``1.0``
            (maximum).  Defaults to ``0.9``.

    Raises:
        RuntimeError: If the underlying TTS engine cannot be initialised.
    """
    engine: Any = _get_engine()
    engine.setProperty("rate", rate)
    engine.setProperty("volume", volume)


def speak(text: str) -> None:
    """Speak *text* aloud using the system TTS engine.

    The call blocks until the engine has finished rendering the audio.  If
    *text* is empty or contains only whitespace the function returns immediately
    without producing any audio.

    Args:
        text: The string to be spoken.

    Raises:
        RuntimeError: If the underlying TTS engine cannot be initialised.
    """
    if not text or not text.strip():
        return

    engine: Any = _get_engine()
    engine.say(text)
    engine.runAndWait()
