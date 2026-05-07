"""Always-on offline wake-word detection using openWakeWord.

Uses sounddevice (already a project dependency) for audio capture at
16 kHz / 16-bit mono — the format openWakeWord expects.

No API key required.  The "alexa" built-in model is downloaded
automatically on first use and cached locally by openwakeword.

Usage:
    with WakeWordDetector() as detector:
        while True:
            detector.wait_for_wake_word()
            speak("¿Sí?")
            # ... record, transcribe, Claude, speak ...
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Any

_log = logging.getLogger(__name__)

_SAMPLE_RATE: int = 16_000   # Hz — required by openWakeWord models
_CHUNK_SIZE: int = 1_280     # samples = 80 ms at 16 kHz


class WakeWordDetector:
    """Listens continuously for the 'alexa' wake word using openWakeWord.

    Call ``set_speaking(True)`` before TTS playback and
    ``set_speaking(False)`` after to suppress false triggers from speaker
    bleed into the microphone.
    """

    def __init__(
        self,
        model_name: str = "alexa",
        threshold: float = 0.7,
    ) -> None:
        """Initialise openWakeWord with the given model.

        Args:
            model_name: openWakeWord built-in model name.  Defaults to
                "alexa".  Other available models: "hey_jarvis",
                "hey_mycroft", etc.
            threshold: Detection score threshold in [0, 1].  Higher values
                reduce false positives at the cost of recall.

        Raises:
            RuntimeError: If openwakeword is not installed.
        """
        try:
            from openwakeword.model import Model  # type: ignore[import]
        except ImportError as exc:
            raise RuntimeError(
                "openwakeword is not installed. "
                "Run: pip install openwakeword"
            ) from exc

        self._model = Model(
            wakeword_models=[model_name],
            inference_framework="onnx",
        )
        self._model_name = model_name
        self._threshold = threshold
        self._queue: queue.Queue[bytes] = queue.Queue()
        # Set when TTS is playing — audio callback drops frames to avoid
        # speaker bleed re-triggering the detector.
        self._speaking = threading.Event()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "WakeWordDetector":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        """No-op — openWakeWord has no explicit native resource to release."""

    # ------------------------------------------------------------------
    # Speaking gate
    # ------------------------------------------------------------------

    def set_speaking(self, speaking: bool) -> None:
        """Suppress detection while Jarvis is speaking to avoid false triggers.

        Call with True before speak() and False immediately after.
        """
        if speaking:
            self._speaking.set()
        else:
            self._speaking.clear()

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def wait_for_wake_word(self) -> None:
        """Block until the wake word is detected.

        Opens a sounddevice RawInputStream, feeds 80 ms chunks to the
        openWakeWord model, and returns as soon as the score exceeds the
        threshold.  The stream is closed before returning so record_audio()
        can re-open the microphone for the user's command.
        """
        import numpy as np
        import sounddevice as sd  # type: ignore[import]

        detected = threading.Event()

        def _callback(indata: Any, _frames: int, _time: Any, _status: Any) -> None:
            if not self._speaking.is_set():
                self._queue.put(bytes(indata))

        with sd.RawInputStream(
            samplerate=_SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=_CHUNK_SIZE,
            callback=_callback,
        ):
            _log.debug("openWakeWord: listening for '%s'...", self._model_name)
            while not detected.is_set():
                raw = self._queue.get()
                chunk = np.frombuffer(raw, dtype=np.int16)
                prediction: dict[str, float] = self._model.predict(chunk)
                score: float = prediction.get(self._model_name, 0.0)
                if score >= self._threshold:
                    _log.info(
                        "Wake word '%s' detected (score=%.3f).",
                        self._model_name,
                        score,
                    )
                    detected.set()

        # Drain any frames queued during detection so the next call starts
        # from a clean state and doesn't immediately re-trigger.
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
