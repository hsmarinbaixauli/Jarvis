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
    {
        "name": "get_unread_emails",
        "description": (
            "Fetch unread emails from the user's Gmail inbox. Returns a list with "
            "id, subject, sender, snippet, and date for each unread message. "
            "Use this whenever the user asks to check, read, or summarize their email."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "max_results": {
                    "type": "integer",
                    "description": (
                        "Maximum number of unread messages to return. Defaults to 10."
                    ),
                    "minimum": 1,
                    "maximum": 25,
                },
            },
            "required": [],
        },
    },
    {
        "name": "send_email_reply",
        "description": (
            "Send a plain-text reply to a specific email message. "
            "IMPORTANT: Always read the recipient and the full proposed reply body "
            "back to the user and wait for explicit verbal confirmation before "
            "calling this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": (
                        "The id of the message to reply to, as returned by "
                        "get_unread_emails."
                    ),
                },
                "body_text": {
                    "type": "string",
                    "description": "The plain-text body of the reply (max 5000 characters).",
                },
            },
            "required": ["message_id", "body_text"],
        },
    },
    {
        "name": "mark_email_read",
        "description": (
            "Mark a single email as read after the user has heard it summarized "
            "or replied to it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The id of the message to mark as read.",
                },
            },
            "required": ["message_id"],
        },
    },
]
