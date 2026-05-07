"""Spotify OAuth2 client factory."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import spotipy
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyOAuth

_log: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scopes
# ---------------------------------------------------------------------------

# user-modify-playback-state  — play, pause, next, previous, seek, volume
# user-read-playback-state    — get active device and playback state
# user-read-currently-playing — get the currently playing track
# streaming                   — required for Premium playback control via the
#                               Web Playback SDK and certain API endpoints
_SCOPES: str = (
    "user-modify-playback-state "
    "user-read-playback-state "
    "user-read-currently-playing "
    "streaming"
)

# ---------------------------------------------------------------------------
# Path constants — anchored to the project root (two levels above this file:
# src/spotify/auth.py  ->  project root) so the token is always found
# regardless of the working directory Jarvis is launched from.
# ---------------------------------------------------------------------------

_PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
_TOKEN_PATH: Path = _PROJECT_ROOT / "credentials" / "spotify_token.json"


# ---------------------------------------------------------------------------
# Custom cache handler
# ---------------------------------------------------------------------------


class _SecureCacheHandler(CacheHandler):
    """Spotipy CacheHandler that mirrors the save/load pattern used by the
    Google Calendar and Gmail auth modules:

    * Path is anchored to the project root — never relative to cwd.
    * ``Path.unlink()`` is called before every write to avoid stale-file issues
      on Windows (where overwriting a locked file can fail silently).
    * After writing, file permissions are restricted to the current user
      (icacls on Windows, chmod 600 elsewhere).
    """

    def __init__(self, token_path: Path = _TOKEN_PATH) -> None:
        self._path = token_path

    # ------------------------------------------------------------------
    # CacheHandler interface
    # ------------------------------------------------------------------

    def get_cached_token(self) -> dict[str, Any] | None:
        """Return the cached token dict, or None if the file does not exist."""
        if not self._path.exists():
            return None
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            _log.warning("Failed to read Spotify token cache %s: %s", self._path, exc)
            return None

    def save_token_to_cache(self, token_info: dict[str, Any]) -> None:
        """Persist *token_info* to disk atomically, replacing any existing file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(token_info), encoding="utf-8")
        _restrict_token_file(tmp)
        tmp.replace(self._path)


# ---------------------------------------------------------------------------
# Permission helper
# ---------------------------------------------------------------------------


def _restrict_token_file(path: Path) -> None:
    """Restrict *path* so only the current user can read it.

    On Windows uses ``icacls`` to remove inherited ACEs and grant the current
    user read-only access.  On other platforms falls back to ``chmod 600``.
    """
    if sys.platform == "win32":
        username: str | None = os.getenv("USERNAME")
        if not username:
            _log.warning(
                "Could not determine USERNAME; token file ACL not restricted: %s", path
            )
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_spotify_client() -> spotipy.Spotify:
    """Return an authenticated Spotipy client using Authorization Code flow.

    Token is cached at ``credentials/spotify_token.json`` inside the project
    root.  On first run, opens a browser for user consent.  Subsequent runs
    reuse the cached refresh token; Spotipy refreshes it automatically when it
    has expired.

    Raises:
        RuntimeError: If any required env var is missing.
    """
    client_id: str | None = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret: str | None = os.environ.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri: str | None = os.environ.get("SPOTIFY_REDIRECT_URI")

    if not all([client_id, client_secret, redirect_uri]):
        raise RuntimeError(
            "Spotify env vars missing. Set SPOTIFY_CLIENT_ID, "
            "SPOTIFY_CLIENT_SECRET, and SPOTIFY_REDIRECT_URI in .env."
        )

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=_SCOPES,
        cache_handler=_SecureCacheHandler(_TOKEN_PATH),
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth_manager)
