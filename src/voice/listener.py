"""Microphone audio capture.

Records audio from the default system microphone using silence detection and
saves it as a WAV file that downstream modules (e.g. Whisper transcription)
can consume.

Recording starts when speech is detected and stops automatically after 1.5
seconds of silence.  The hard cap is 15 seconds.

Ambient-noise calibration runs once on the first call and the resulting
energy threshold is reused on all subsequent calls, eliminating the 1-second
silent delay that would otherwise occur at the start of every turn.
"""

from __future__ import annotations

import speech_recognition as sr


# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

_recognizer: sr.Recognizer | None = None
_calibrated_energy: float | None = None


def _get_recognizer() -> sr.Recognizer:
    """Return the shared Recognizer, calibrating ambient noise on first use."""
    global _recognizer, _calibrated_energy

    if _recognizer is None:
        rec = sr.Recognizer()
        rec.pause_threshold = 1.5
        try:
            mic = sr.Microphone()
        except OSError as exc:
            raise OSError(
                "No microphone device was found. "
                "Ensure a microphone is connected and accessible before calling record_audio."
            ) from exc

        with mic as source:
            rec.adjust_for_ambient_noise(source)

        _calibrated_energy = rec.energy_threshold
        _recognizer = rec

    return _recognizer


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def record_audio(output_path: str = "temp_audio.wav") -> str:
    """Record audio from the default microphone using silence detection.

    Ambient-noise calibration runs only on the first call; subsequent calls
    reuse the cached energy threshold so there is no leading silent delay.

    Waits indefinitely for speech to begin, then stops automatically after
    1.5 seconds of silence or when the 15-second hard cap is reached.

    Args:
        output_path: Destination file path for the recorded WAV audio.
            Defaults to ``"temp_audio.wav"`` in the current working directory.

    Returns:
        The path to the saved WAV file as a string (equal to *output_path*).

    Raises:
        OSError: If no microphone is available on the current system.
    """
    recognizer = _get_recognizer()

    try:
        microphone: sr.Microphone = sr.Microphone()
    except OSError as exc:
        raise OSError(
            "No microphone device was found. "
            "Ensure a microphone is connected and accessible before calling record_audio."
        ) from exc

    with microphone as source:
        if _calibrated_energy is not None:
            recognizer.energy_threshold = _calibrated_energy
        audio: sr.AudioData = recognizer.listen(
            source,
            timeout=None,
            phrase_time_limit=15,
        )

    wav_data: bytes = audio.get_wav_data()
    with open(output_path, "wb") as wav_file:
        wav_file.write(wav_data)

    return output_path
