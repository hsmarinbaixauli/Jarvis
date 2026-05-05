"""Jarvis voice assistant entry point.

Orchestrates the full voice-assistant loop:
  1. Record audio from the microphone.
  2. Transcribe with Whisper.
  3. Send the transcript to Claude (with calendar tools).
  4. Execute any tool calls Claude requests against Google Calendar.
  5. Speak the final text response aloud.

Run with:
    python -m src.main
or:
    python src/main.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from typing import Any

import anthropic
from dotenv import load_dotenv
from googleapiclient.discovery import Resource

from src.calendar.auth import get_calendar_service
from src.calendar.events import create_event, get_today_events, get_upcoming_events
from src.tools.definitions import TOOLS
from src.transcription.whisper import transcribe_audio
from src.voice.listener import record_audio
from src.voice.speaker import set_voice_properties, speak


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODEL: str = "claude-haiku-4-5-20251001"
_MAX_TOKENS: int = 1024
_RECORD_DURATION: int = 5
_MAX_TOOL_ITERATIONS: int = 10
_GREETING: str = "Hello! I am Jarvis, your personal assistant. How can I help you today?"
_GOODBYE: str = "Goodbye! Have a great day."
_FALLBACK: str = "Done."


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------


def _dispatch_tool_call(
    tool_name: str,
    tool_input: dict[str, Any],
    calendar_service: Resource,
) -> Any:
    """Route a single tool call to the appropriate calendar function.

    Args:
        tool_name: The name of the tool as declared in ``TOOLS``.
        tool_input: The raw ``input`` dict from the Anthropic tool-use block.
        calendar_service: An authenticated Google Calendar API service object.

    Returns:
        The return value of the dispatched function.  Always serialisable to
        ``str`` for inclusion in a ``tool_result`` message.

    Raises:
        ValueError: If *tool_name* is not a recognised tool.
    """
    if tool_name == "get_today_events":
        return get_today_events(calendar_service)

    if tool_name == "get_upcoming_events":
        days: int = max(1, min(int(tool_input.get("days", 7)), 90))
        return get_upcoming_events(calendar_service, days=days)

    if tool_name == "create_event":
        title: str = tool_input["title"].strip()
        if not title:
            raise ValueError("Event title must not be empty.")
        title = title[:255]
        description: str = tool_input.get("description", "").strip()[:1000]
        start_dt: datetime = datetime.fromisoformat(tool_input["start_datetime"])
        end_dt: datetime = datetime.fromisoformat(tool_input["end_datetime"])
        return create_event(
            calendar_service,
            title=title,
            start_datetime=start_dt,
            end_datetime=end_dt,
            description=description,
        )

    raise ValueError(f"Unknown tool: {tool_name!r}")


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------


def _extract_text(content: list[Any]) -> str:
    """Return the concatenated text from all text blocks in *content*.

    Args:
        content: A list of Anthropic content blocks (``TextBlock``,
            ``ToolUseBlock``, etc.).

    Returns:
        A single string with all text blocks joined by a newline.  Returns an
        empty string when no text blocks are present.
    """
    parts: list[str] = [
        block.text
        for block in content
        if hasattr(block, "type") and block.type == "text"
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Agentic turn
# ---------------------------------------------------------------------------


def _run_agentic_turn(
    client: anthropic.Anthropic,
    user_text: str,
    calendar_service: Resource,
) -> str:
    """Send *user_text* to Claude and handle the full tool-use loop.

    Iterates until Claude returns a ``stop_reason`` other than ``"tool_use"``,
    dispatching every tool call in each intermediate response to the
    appropriate Google Calendar function and feeding results back to Claude.

    Args:
        client: An initialised Anthropic API client.
        user_text: The transcribed user utterance.
        calendar_service: An authenticated Google Calendar API service object.

    Returns:
        The final plain-text response from Claude, or an empty string when
        Claude produces no text in its final turn.
    """
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_text}]

    response: anthropic.types.Message = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        tools=TOOLS,
        messages=messages,
    )

    # --- Tool-use loop ---
    _iterations: int = 0
    while response.stop_reason == "tool_use" and _iterations < _MAX_TOOL_ITERATIONS:
        _iterations += 1
        tool_calls: list[Any] = [
            block for block in response.content if block.type == "tool_use"
        ]

        results: list[Any] = [
            _dispatch_tool_call(tool.name, tool.input, calendar_service)
            for tool in tool_calls
        ]

        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool.id,
                    "content": str(result),
                }
                for tool, result in zip(tool_calls, results)
            ],
        })

        response = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            tools=TOOLS,
            messages=messages,
        )

    return _extract_text(response.content)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def _init_services() -> tuple[anthropic.Anthropic, Resource]:
    """Load environment variables and initialise all external services.

    Reads ``ANTHROPIC_API_KEY`` from the environment (after loading ``.env``)
    and raises :class:`RuntimeError` if it is absent.  Initialises and returns
    both the Anthropic client and the Google Calendar service.

    Returns:
        A tuple of ``(anthropic_client, calendar_service)``.

    Raises:
        RuntimeError: If ``ANTHROPIC_API_KEY`` is not set in the environment.
    """
    load_dotenv()

    api_key: str | None = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Add it to your .env file or export it as an environment variable."
        )

    anthropic_client: anthropic.Anthropic = anthropic.Anthropic(api_key=api_key)
    calendar_service: Resource = get_calendar_service()

    return anthropic_client, calendar_service


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the Jarvis voice assistant loop.

    Continuously records audio, transcribes it, and forwards the text to
    Claude.  Calendar tool calls are handled transparently.  Press
    ``Ctrl+C`` to stop.
    """
    # --- Initialise ---
    client: anthropic.Anthropic
    calendar_service: Resource
    client, calendar_service = _init_services()

    set_voice_properties(rate=150, volume=0.9)

    print("Jarvis is ready.")
    speak(_GREETING)

    # --- Main loop ---
    try:
        while True:
            fd, audio_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                print("\nListening...")
                record_audio(duration=_RECORD_DURATION, output_path=audio_path)

                user_text: str = transcribe_audio(audio_path)

                if not user_text.strip():
                    continue

                print(f"You said: {user_text}")

                final_text: str = _run_agentic_turn(client, user_text, calendar_service)

                if final_text:
                    print(f"Jarvis: {final_text}")
                    speak(final_text)
                else:
                    speak(_FALLBACK)
            except Exception as exc:
                print(f"Error: {exc}")
            finally:
                try:
                    os.unlink(audio_path)
                except OSError:
                    pass

    except KeyboardInterrupt:
        print(f"\n{_GOODBYE}")
        speak(_GOODBYE)
        sys.exit(0)


if __name__ == "__main__":
    main()
