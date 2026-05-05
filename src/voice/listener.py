"""Microphone audio capture.

Records audio from the default system microphone for a fixed duration and
saves it as a WAV file that downstream modules (e.g. Whisper transcription)
can consume.
"""

from __future__ import annotations

import speech_recognition as sr


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def record_audio(duration: int = 5, output_path: str = "temp_audio.wav") -> str:
    """Record audio from the default microphone and save it as a WAV file.

    Args:
        duration: Number of seconds to record.  Defaults to ``5``.
        output_path: Destination file path for the recorded WAV audio.
            Defaults to ``"temp_audio.wav"`` in the current working directory.

    Returns:
        The path to the saved WAV file as a string (equal to *output_path*).

    Raises:
        OSError: If no microphone is available on the current system.
    """
    recognizer: sr.Recognizer = sr.Recognizer()

    try:
        microphone: sr.Microphone = sr.Microphone()
    except OSError as exc:
        raise OSError(
            "No microphone device was found. "
            "Ensure a microphone is connected and accessible before calling record_audio."
        ) from exc

    with microphone as source:
        recognizer.adjust_for_ambient_noise(source)
        audio: sr.AudioData = recognizer.record(source, duration=duration)

    wav_data: bytes = audio.get_wav_data()
    with open(output_path, "wb") as wav_file:
        wav_file.write(wav_data)

    return output_path
