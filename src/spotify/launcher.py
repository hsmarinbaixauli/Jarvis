"""Spotify desktop app launcher for Windows.

Used by playback.py to automatically open Spotify when Spotify Connect
reports no active device, then wait for a device to register before
retrying the playback command.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
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
    1. Windows Store versioned install (known path)
    2. Per-user AppData install (classic installer)
    3. Microsoft Store WindowsApps shim
    4. Program Files install
    5. PATH lookup as last resort
    """
    appdata = os.environ.get("APPDATA", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    programfiles = os.environ.get("PROGRAMFILES", r"C:\Program Files")

    candidates: list[str] = [
        # Windows Store versioned path — checked first as it is the known
        # install location on this machine.
        r"C:\Program Files\WindowsApps\SpotifyAB.SpotifyMusic_1.288.483.0_x64__zpdnekdrzrea0\Spotify.exe",
    ]
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


_STORE_APP_ID: str = r"SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify"


def launch_spotify() -> bool:
    """Launch Spotify via the Windows Store app URI, falling back to exe.

    Uses ``start shell:AppsFolder\\<app-id>`` which is the correct way to
    launch Microsoft Store apps — avoids the permission restrictions that
    prevent direct Popen on WindowsApps executables.

    Returns:
        True if the launch command was issued successfully.
        False on any error.

    Uses a module-level lock so only one launch occurs even when multiple
    playback commands are dispatched simultaneously.
    """
    with _launch_lock:
        try:
            subprocess.run(
                ["cmd", "/c", "start", f"shell:AppsFolder\\{_STORE_APP_ID}"],
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            _log.info("Spotify launched via Store app URI (%s).", _STORE_APP_ID)
            return True
        except Exception as exc:
            _log.warning("Store launch failed (%s) — trying exe fallback.", exc)

        # Fallback: direct exe launch for non-Store installs.
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
            _log.info("Spotify launched from exe: %s", exe)
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
