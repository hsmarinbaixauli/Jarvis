"""Jarvis voice assistant entry point.

Orchestrates the full voice-assistant loop:
  1. Record audio from the microphone.
  2. Transcribe with Whisper.
  3. Send the transcript to Claude (with calendar and Gmail tools).
  4. Execute any tool calls Claude requests against Google Calendar or Gmail.
  5. Speak the final text response aloud.

Run with:
    python -m src.main
or:
    python src/main.py
"""

from __future__ import annotations

import logging
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
from src.gmail.auth import get_gmail_service
from src.gmail.messages import get_unread_messages, mark_as_read, send_reply
from src.tools.definitions import TOOLS
from src.transcription.whisper import transcribe_audio
from src.voice.listener import record_audio
from src.voice.speaker import set_voice_properties, speak

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODEL: str = "claude-haiku-4-5-20251001"
_MAX_TOKENS: int = 1024
_RECORD_DURATION: int = 5
_MAX_TOOL_ITERATIONS: int = 10
_MAX_TRANSCRIPT_LENGTH: int = 2000  # guard against Whisper hallucinations / cost abuse
_SYSTEM_PROMPT: str = (
    "Before calling send_email_reply, always read the recipient and the full "
    "proposed reply body back to the user and wait for explicit verbal "
    "confirmation in the next turn."
)
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
    gmail_service: Resource,
) -> Any:
    """Route a single tool call to the appropriate calendar or Gmail function.

    Args:
        tool_name: The name of the tool as declared in ``TOOLS``.
        tool_input: The raw ``input`` dict from the Anthropic tool-use block.
        calendar_service: An authenticated Google Calendar API service object.
        gmail_service: An authenticated Gmail API service object.

    Returns:
        The return value of the dispatched function.  Always serialisable to
        ``str`` for inclusion in a ``tool_result`` message.

    Raises:
        ValueError: If *tool_name* is not a recognised tool.
    """
    if tool_name == "get_today_events":
        return get_today_events(calendar_service)

    if tool_name == "get_upcoming_events":
        days: int = max(1, min(int(float(tool_input.get("days", 7))), 90))
        return get_upcoming_events(calendar_service, days=days)

    if tool_name == "create_event":
        title: str = tool_input["title"].strip()
        if not title:
            raise ValueError("Event title must not be empty.")
        title = title[:255]
        description: str = tool_input.get("description", "").strip()[:1000]
        start_dt: datetime = datetime.fromisoformat(tool_input["start_datetime"])
        end_dt: datetime = datetime.fromisoformat(tool_input["end_datetime"])
        if end_dt <= start_dt:
            raise ValueError("end_datetime must be after start_datetime.")
        return create_event(
            calendar_service,
            title=title,
            start_datetime=start_dt,
            end_datetime=end_dt,
            description=description,
        )

    if tool_name == "get_unread_emails":
        max_results: int = max(1, min(int(float(tool_input.get("max_results", 10))), 25))
        return get_unread_messages(gmail_service, max_results=max_results)

    if tool_name == "send_email_reply":
        msg_id: str = tool_input["message_id"].strip()
        raw_body: str = tool_input["body_text"].strip()
        if not msg_id or not raw_body:
            raise ValueError("message_id and body_text are required.")
        if len(raw_body) > 5000:
            _log.warning("Reply body truncated from %d to 5000 chars.", len(raw_body))
        body: str = raw_body[:5000]
        if not os.environ.get("JARVIS_ALLOW_SEND"):
            raise ValueError(
                "Email sending is disabled. Set JARVIS_ALLOW_SEND=1 in .env to enable."
            )
        return send_reply(gmail_service, msg_id, body)

    if tool_name == "mark_email_read":
        mark_as_read(gmail_service, tool_input["message_id"])
        return {"status": "ok"}

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
    gmail_service: Resource,
) -> str:
    """Send *user_text* to Claude and handle the full tool-use loop.

    Iterates until Claude returns a ``stop_reason`` other than ``"tool_use"``,
    dispatching every tool call in each intermediate response to the
    appropriate Google Calendar or Gmail function and feeding results back to
    Claude.

    Args:
        client: An initialised Anthropic API client.
        user_text: The transcribed user utterance.
        calendar_service: An authenticated Google Calendar API service object.
        gmail_service: An authenticated Gmail API service object.

    Returns:
        The final plain-text response from Claude, or an empty string when
        Claude produces no text in its final turn.
    """
    messages: list[dict[str, Any]] = [{"role": "user", "content": user_text}]

    response: anthropic.types.Message = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
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

        tool_results: list[dict[str, Any]] = []
        for tool in tool_calls:
            try:
                result = _dispatch_tool_call(
                    tool.name, tool.input, calendar_service, gmail_service
                )
                content = str(result)
            except Exception as exc:
                content = f"Error: {exc}"
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool.id,
                "content": content,
            })

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

        response = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

    if _iterations >= _MAX_TOOL_ITERATIONS:
        _log.warning(
            "Tool-use loop reached iteration limit (%d).", _MAX_TOOL_ITERATIONS
        )

    return _extract_text(response.content)


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def _init_services() -> tuple[anthropic.Anthropic, Resource, Resource]:
    """Load environment variables and initialise all external services.

    Reads ``ANTHROPIC_API_KEY`` from the environment (after loading ``.env``)
    and raises :class:`RuntimeError` if it is absent.  Initialises and returns
    the Anthropic client, the Google Calendar service, and the Gmail service.

    Returns:
        A tuple of ``(anthropic_client, calendar_service, gmail_service)``.

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
    gmail_service: Resource = get_gmail_service()

    return anthropic_client, calendar_service, gmail_service


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the Jarvis voice assistant loop.

    Continuously records audio, transcribes it, and forwards the text to
    Claude.  Calendar and Gmail tool calls are handled transparently.  Press
    ``Ctrl+C`` to stop.
    """
    # --- Initialise ---
    client: anthropic.Anthropic
    calendar_service: Resource
    gmail_service: Resource
    client, calendar_service, gmail_service = _init_services()

    set_voice_properties(rate=150, volume=0.9)

    _log.info("Jarvis is ready.")
    speak(_GREETING)

    # --- Main loop ---
    try:
        while True:
            fd, audio_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                _log.info("Listening...")
                record_audio(duration=_RECORD_DURATION, output_path=audio_path)

                user_text: str = transcribe_audio(audio_path)

                if not user_text.strip():
                    continue

                if len(user_text) > _MAX_TRANSCRIPT_LENGTH:
                    _log.warning(
                        "Transcript truncated from %d to %d chars.",
                        len(user_text),
                        _MAX_TRANSCRIPT_LENGTH,
                    )
                    user_text = user_text[:_MAX_TRANSCRIPT_LENGTH]

                _log.info("You said: %s", user_text)

                final_text: str = _run_agentic_turn(
                    client, user_text, calendar_service, gmail_service
                )

                if final_text:
                    _log.info("Jarvis: %s", final_text)
                    speak(final_text)
                else:
                    speak(_FALLBACK)
            except Exception:
                _log.exception("Error in main loop")
            finally:
                try:
                    os.unlink(audio_path)
                except OSError:
                    pass

    except KeyboardInterrupt:
        _log.info(_GOODBYE)
        speak(_GOODBYE)
        sys.exit(0)


if __name__ == "__main__":
    main()
