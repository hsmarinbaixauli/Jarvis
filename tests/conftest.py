"""Shared pytest fixtures for Jarvis tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def mock_calendar_service() -> MagicMock:
    """Return a MagicMock that mimics the Google Calendar API service object.

    The fixture pre-wires the chain ``service.events().list().execute()`` so
    individual tests can override ``.execute.return_value`` without repeating
    the chain setup.
    """
    service: MagicMock = MagicMock()
    # Default: empty events list so tests that don't care about data still work.
    service.events.return_value.list.return_value.execute.return_value = {"items": []}
    service.events.return_value.insert.return_value.execute.return_value = {
        "id": "evt001",
        "summary": "Test Event",
    }
    return service


@pytest.fixture()
def mock_gmail_service() -> MagicMock:
    """Return a MagicMock that mimics the Gmail API service object.

    Pre-wires common method chains so tests can override ``.execute.return_value``
    without boilerplate.
    """
    service: MagicMock = MagicMock()
    # Default: empty message list.
    service.users.return_value.messages.return_value.list.return_value.execute.return_value = {
        "messages": []
    }
    service.users.return_value.messages.return_value.get.return_value.execute.return_value = {}
    service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "msg001"
    }
    service.users.return_value.messages.return_value.modify.return_value.execute.return_value = {}
    # Profile lookup used by _get_sender_email.
    service.users.return_value.getProfile.return_value.execute.return_value = {
        "emailAddress": "test@example.com"
    }
    return service
