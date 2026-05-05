"""Anthropic tool definitions for Jarvis calendar capabilities.

Exports a single ``TOOLS`` list that can be passed directly as the ``tools=``
argument to any Anthropic API call.  This module contains no runtime logic —
it is pure, static data.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_today_events",
        "description": (
            "Get all calendar events scheduled for today from Google Calendar. "
            "Returns events spanning from 00:00:00 to 23:59:59 in the local "
            "system timezone, including all-day events."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_upcoming_events",
        "description": (
            "Get calendar events from now until N days ahead from Google Calendar. "
            "Events are ordered by start time."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": (
                        "Number of days ahead to look for events, counting from "
                        "the current moment. Defaults to 7."
                    ),
                    "minimum": 1,
                    "maximum": 90,
                },
            },
            "required": [],
        },
    },
    {
        "name": "create_event",
        "description": (
            "Create a new event on the primary Google Calendar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The event title or summary shown in the calendar UI.",
                },
                "start_datetime": {
                    "type": "string",
                    "description": (
                        "Event start time in ISO 8601 format: \"YYYY-MM-DDTHH:MM:SS\". "
                        "Example: \"2026-05-05T09:30:00\"."
                    ),
                },
                "end_datetime": {
                    "type": "string",
                    "description": (
                        "Event end time in ISO 8601 format: \"YYYY-MM-DDTHH:MM:SS\". "
                        "Example: \"2026-05-05T10:30:00\"."
                    ),
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Optional free-text body description for the event. "
                        "Defaults to an empty string."
                    ),
                },
            },
            "required": ["title", "start_datetime", "end_datetime"],
        },
    },
]
