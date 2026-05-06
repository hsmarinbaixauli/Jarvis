"""Spotify desktop app launcher for Windows.

Used by playback.py to automatically open Spotify when Spotify Connect
reports no active device, then wait for a device to register before
retrying the playback command.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import spotipy

_log = logging.getLogger(__name__)

# Module-level lock so concurrent tool calls only trigger one launch.
_launch_lock = threading.Lock()


def find_spotify_executable() -> Path | None:
    """Return the path to the Spotify executable, or None if not found.

    Searches candidate paths in priority order:
    1. Per-user AppData install (most common)
    2. Microsoft Store WindowsApps shim
    3. Program Files install
    4. PATH lookup as last resort
    """
    appdata = os.environ.get("APPDATA", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    programfiles = os.environ.get("PROGRAMFILES", r"C:\Program Files")

    candidates: list[str] = []
    if appdata:
        candidates.append(os.path.join(appdata, "Spotify", "Spotify.exe"))
    if localappdata:
        candidates.append(
            os.path.join(localappdata, "Microsoft", "WindowsApps", "Spotify.exe")
        )
    candidates.append(os.path.join(programfiles, "Spotify", "Spotify.exe"))

    for candidate in candidates:
        try:
            if Path(candidate).exists():
                return Path(candidate)
        except PermissionError:
            _log.warning("Permission denied checking Spotify path: %s", candidate)

    which = shutil.which("spotify")
    if which:
        return Path(which)

    return None


def launch_spotify() -> bool:
    """Launch the Spotify desktop app in a detached background process.

    Returns:
        True if the process was started successfully.
        False if the Spotify executable could not be found.

    Uses a module-level lock so only one launch occurs even when multiple
    playback commands are dispatched simultaneously.
    """
    import subprocess

    with _launch_lock:
        exe = find_spotify_executable()
        if exe is None:
            _log.warning("Spotify executable not found — cannot auto-launch.")
            return False

        try:
            if sys.platform == "win32":
                flags = (
                    subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                    | subprocess.CREATE_NO_WINDOW
                )
                subprocess.Popen([str(exe)], creationflags=flags, close_fds=True)
            else:
                subprocess.Popen([str(exe)], start_new_session=True, close_fds=True)
            _log.info("Spotify launched from: %s", exe)
            return True
        except Exception as exc:
            _log.warning("Failed to launch Spotify: %s", exc)
            return False


def wait_for_active_device(
    client: "spotipy.Spotify",
    timeout: float = 8.0,
    poll_interval: float = 0.5,
) -> bool:
    """Poll Spotify Connect until at least one device appears or timeout elapses.

    Args:
        client: An authenticated Spotipy client.
        timeout: Maximum seconds to wait.
        poll_interval: Seconds between each poll.

    Returns:
        True if a device was found before the timeout, False otherwise.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            devices = (client.devices() or {}).get("devices") or []
            if devices:
                _log.info("Spotify device appeared: %s", devices[0].get("name"))
                return True
        except Exception as exc:
            _log.debug("Device poll error (will retry): %s", exc)
        time.sleep(poll_interval)

    _log.warning("No Spotify device appeared within %.1fs.", timeout)
    return False
