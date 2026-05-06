"""Text-to-speech output via ElevenLabs API.

Converts a text string to spoken audio using ElevenLabs eleven_multilingual_v2
(raw PCM 22050 Hz output), wraps the PCM bytes in a WAV container in memory,
and plays it back through sounddevice / soundfile.
"""

from __future__ import annotations

import io
import logging
import os
import wave

import sounddevice as sd
import soundfile as sf
from elevenlabs.client import ElevenLabs

_log = logging.getLogger(__name__)

_client: ElevenLabs | None = None
_volume: float = 0.9

_MODEL_ID: str = "eleven_multilingual_v2"
_OUTPUT_FORMAT: str = "pcm_22050"
_SAMPLE_RATE: int = 22050


def _get_client() -> ElevenLabs:
    global _client
    if _client is None:
        api_key: str | None = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY is not set.")
        _client = ElevenLabs(api_key=api_key)
    return _client


def _pcm_to_wav(pcm_data: bytes) -> bytes:
    """Wrap raw 16-bit mono PCM bytes in an in-memory WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def set_voice_properties(rate: int = 150, volume: float = 0.9) -> None:
    """Set playback volume.

    The rate parameter is accepted for interface compatibility but is not used —
    speaking rate is controlled by ElevenLabs voice settings in the dashboard.

    Args:
        rate: Ignored.
        volume: Playback volume in the range 0.0–1.0. Defaults to 0.9.
    """
    global _volume
    _volume = max(0.0, min(1.0, volume))


def speak(text: str) -> None:
    """Speak *text* aloud using ElevenLabs (model: eleven_multilingual_v2).

    The call blocks until playback is complete. Returns immediately if *text*
    is empty or whitespace-only.

    Args:
        text: The string to be spoken.
    """
    if not text.strip():
        return

    voice_id: str = os.environ.get("ELEVENLABS_VOICE_ID", "")
    if not voice_id:
        _log.error("ELEVENLABS_VOICE_ID is not set — skipping speak().")
        return

    try:
        client = _get_client()
        pcm_bytes: bytes = b"".join(
            client.text_to_speech.convert(
                voice_id=voice_id,
                model_id=_MODEL_ID,
                text=text,
                output_format=_OUTPUT_FORMAT,
            )
        )
    except Exception:
        _log.exception("ElevenLabs TTS synthesis failed")
        return

    try:
        wav_bytes = _pcm_to_wav(pcm_bytes)
        data, samplerate = sf.read(io.BytesIO(wav_bytes), dtype="float32")
        sd.play(data * _volume, samplerate=samplerate)
        sd.wait()
    except Exception:
        _log.exception("Failed to play TTS audio")
