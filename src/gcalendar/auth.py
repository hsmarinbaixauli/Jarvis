"""Google Calendar OAuth2 authentication.

Handles the full OAuth2 flow for a desktop/installed application, persisting
the token so the user is only prompted on the first run (or when the token
is revoked / expired and cannot be refreshed).
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

_log: logging.Logger = logging.getLogger(__name__)

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.discovery import Resource

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Read/write access to calendar events.  Change to a narrower scope if only
# read access is required.
SCOPES: tuple[str, ...] = ("https://www.googleapis.com/auth/calendar",)

# Resolve paths relative to the project root (two levels above this file:
# src/gcalendar/auth.py  ->  project root)
_PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
_CREDENTIALS_PATH: Path = _PROJECT_ROOT / "credentials" / "credentials.json"
_TOKEN_PATH: Path = _PROJECT_ROOT / "credentials" / "token.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_calendar_service(
    credentials_path: Path | str = _CREDENTIALS_PATH,
    token_path: Path | str = _TOKEN_PATH,
    scopes: list[str] | None = None,
) -> Resource:
    """Return an authenticated Google Calendar API service object.

    On the first call the user is directed to a browser-based consent screen
    and the resulting token is saved to *token_path*.  Subsequent calls reuse
    the cached token, refreshing it automatically when it has expired.

    Args:
        credentials_path: Path to the ``credentials.json`` file downloaded
            from the Google Cloud Console.  Defaults to
            ``credentials/credentials.json`` in the project root.
        token_path: Path where the OAuth2 token is stored after the first
            successful authorisation.  Defaults to
            ``credentials/token.json`` in the project root.
        scopes: OAuth2 scopes to request.  Defaults to full calendar access.

    Returns:
        A ``googleapiclient`` Resource object ready to make Calendar API calls.

    Raises:
        FileNotFoundError: If *credentials_path* does not exist.
        google.auth.exceptions.TransportError: On network failures during
            token refresh or the initial OAuth2 flow.
    """
    credentials_path = Path(credentials_path)
    token_path = Path(token_path)
    active_scopes: list[str] = scopes if scopes is not None else SCOPES

    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Google credentials file not found: {credentials_path}\n"
            "Download it from the Google Cloud Console and place it at that path."
        )

    creds: Credentials | None = _load_token(token_path, active_scopes)

    if creds is None or not creds.valid:
        creds = _refresh_or_reauthorise(creds, credentials_path, token_path, active_scopes)

    return build("calendar", "v3", credentials=creds)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_token(token_path: Path, scopes: list[str]) -> Credentials | None:
    """Load a previously saved token from disk, or return ``None``.

    The token is discarded if it was issued for a different set of scopes so
    that callers with broadened requirements always trigger a fresh consent.
    """
    if not token_path.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)
    except Exception:  # noqa: BLE001 — malformed token triggers fresh OAuth
        _log.warning("Discarding malformed token file %s — re-authorising.", token_path)
        return None

    # Verify the token covers exactly the requested scopes.
    if creds.scopes and not set(scopes).issubset(set(creds.scopes)):
        return None

    return creds


def _refresh_or_reauthorise(
    creds: Credentials | None,
    credentials_path: Path,
    token_path: Path,
    scopes: list[str],
) -> Credentials:
    """Refresh an expired token or run the full OAuth2 consent flow.

    Saves the resulting credentials to *token_path* for future reuse.
    """
    if creds is not None and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(credentials_path), scopes
        )
        # ``run_local_server`` opens the default browser and spins up a
        # temporary local HTTP server to capture the authorisation redirect.
        creds = flow.run_local_server(port=0)

    _save_token(creds, token_path)
    return creds


def _restrict_token_file(path: Path) -> None:
    """Restrict *path* so only the current user can read it.

    On Windows uses ``icacls`` to remove inherited ACEs and grant the current
    user read-only access.  On other platforms falls back to ``chmod 600``.
    """
    if sys.platform == "win32":
        username: str | None = os.getenv("USERNAME")
        if not username:
            _log.warning("Could not determine USERNAME; token file ACL not restricted: %s", path)
            return
        try:
            result = subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{username}:(F)"],
                check=False,
                capture_output=True,
            )
            if result.returncode != 0:
                _log.warning(
                    "icacls exited with %d for %s: %s",
                    result.returncode, path,
                    result.stderr.decode(errors="replace"),
                )
        except Exception as exc:  # noqa: BLE001
            _log.warning("icacls failed to restrict token file %s: %s", path, exc)
    else:
        os.chmod(path, 0o600)


def _save_token(creds: Credentials, token_path: Path) -> None:
    """Persist *creds* to *token_path* as JSON."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    if token_path.exists():
        token_path.unlink()
    token_path.write_text(creds.to_json(), encoding="utf-8")
    _restrict_token_file(token_path)
