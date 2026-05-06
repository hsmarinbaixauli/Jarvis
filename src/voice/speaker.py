"""Text-to-speech output via Google Cloud Text-to-Speech API.

Converts a text string to spoken audio using the Neural2 Spanish female voice
(es-ES-Neural2-A), writes the LINEAR16 wav to a temporary file, and plays it
back through sounddevice.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile

import sounddevice as sd
import soundfile as sf
from google.cloud import texttospeech

_log = logging.getLogger(__name__)

_client: texttospeech.TextToSpeechClient | None = None
_volume: float = 0.9
_speaking_rate: float = 1.0
_pitch: float = 0.0

_VOICE = texttospeech.VoiceSelectionParams(
    language_code="es-ES",
    name="es-ES-Neural2-A",
)
_AUDIO_CONFIG = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.LINEAR16,
    speaking_rate=_speaking_rate,
    pitch=_pitch,
)


def _get_client() -> texttospeech.TextToSpeechClient:
    global _client
    if _client is None:
        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if credentials_path and not os.path.isfile(credentials_path):
            raise RuntimeError(
                f"GOOGLE_APPLICATION_CREDENTIALS points to a missing file: {credentials_path}"
            )
        _client = texttospeech.TextToSpeechClient()
    return _client


def set_voice_properties(rate: int = 150, volume: float = 0.9) -> None:
    """Set playback volume. The rate parameter is not applicable to Google Cloud TTS.

    Args:
        rate: Ignored — speaking rate is fixed at 1.0 via the API config.
        volume: Playback volume in the range 0.0–1.0. Defaults to 0.9.
    """
    global _volume
    _volume = max(0.0, min(1.0, volume))


def speak(text: str) -> None:
    """Speak *text* aloud using Google Cloud TTS (voice: es-ES-Neural2-A).

    The call blocks until playback is complete. Returns immediately if *text*
    is empty or whitespace-only.

    Args:
        text: The string to be spoken.

    Raises:
        RuntimeError: If credentials are missing or the API call fails.
    """
    if not text.strip():
        return

    client = _get_client()

    synthesis_input = texttospeech.SynthesisInput(text=text)
    try:
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=_VOICE,
            audio_config=_AUDIO_CONFIG,
        )
    except Exception:
        _log.exception("Google Cloud TTS synthesis failed")
        return

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        tmp.write(response.audio_content)

    try:
        data, samplerate = sf.read(tmp_path, dtype="float32")
        sd.play(data * _volume, samplerate=samplerate)
        sd.wait()
    except Exception:
        _log.exception("Failed to play TTS audio")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
