"""Spotify Web API playback control wrappers."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

import spotipy

from src.spotify.launcher import launch_spotify, wait_for_active_device

_log = logging.getLogger(__name__)

_cached_device_id: str | None = None


def _no_device() -> dict[str, str]:
    return {"status": "no_active_device"}


def _track_info(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "track": item["name"],
        "artist": ", ".join(a["name"] for a in item["artists"]),
        "album": item["album"]["name"],
        "uri": item["uri"],
    }


def _log_spotify_exc(exc: spotipy.SpotifyException, context: str) -> None:
    """Log every field of a SpotifyException so no-device failures are traceable."""
    _log.warning(
        "[spotify][%s] %s http_status=%r reason=%r msg=%r",
        context,
        type(exc).__name__,
        getattr(exc, "http_status", "MISSING"),
        getattr(exc, "reason", "MISSING"),
        str(exc),
    )


def _has_any_device(client: spotipy.Spotify) -> bool:
    """Return True if Spotify reports at least one Connect device."""
    devices = (client.devices() or {}).get("devices") or []
    return len(devices) > 0


def _get_first_device_id(client: spotipy.Spotify) -> str | None:
    """Return the id of the first available Connect device, falling back to the last known id."""
    global _cached_device_id
    devices = (client.devices() or {}).get("devices") or []
    if devices:
        _cached_device_id = devices[0]["id"]
        return _cached_device_id
    if _cached_device_id:
        _log.warning("[spotify] No devices reported — falling back to cached device_id=%r", _cached_device_id)
    return _cached_device_id


def _clear_device_cache() -> None:
    global _cached_device_id
    _cached_device_id = None


def _handle_no_device(
    client: spotipy.Spotify,
    retry: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Auto-launch Spotify and retry *retry* once on no-active-device errors."""
    _log.warning("[spotify] _handle_no_device called — launching Spotify.")
    _log.info("Abriendo Spotify...")
    launched = launch_spotify()
    _log.warning("[spotify] launch_spotify() returned: %r", launched)
    if not launched:
        return {"status": "no_active_device", "reason": "spotify_not_installed"}
    device_found = wait_for_active_device(client, timeout=15.0)
    _log.warning("[spotify] wait_for_active_device() returned: %r", device_found)
    if not device_found:
        return {
            "status": "opening",
            "message": "Spotify se está abriendo. Inténtalo de nuevo en un momento.",
        }
    _log.warning("[spotify] device ready — sleeping 10s then retrying playback.")
    time.sleep(10)
    device_id = _get_first_device_id(client)
    if device_id:
        _log.warning("[spotify] transferring playback to device_id=%r", device_id)
        client.transfer_playback(device_id, force_play=True)
    try:
        return retry()
    except spotipy.SpotifyException as exc:
        _clear_device_cache()
        _log_spotify_exc(exc, "_handle_no_device/retry")
        if exc.http_status == 404:
            return _no_device()
        raise


def play(
    client: spotipy.Spotify,
    query: str | None = None,
    artist: str | None = None,
    track: str | None = None,
) -> dict[str, Any]:
    """Resume playback or start a search-driven play.

    Execution order: check device → launch if needed → search → play.

    Search modes (evaluated in priority order):
    - artist + track → precise field-filter search: track:"{track}" artist:"{artist}"
    - artist only   → artist context URI (plays the artist's top tracks)
    - query only    → playlist-first search for genres / moods
    - nothing       → resume current playback
    """
    # 1) Check for an active device — launch Spotify proactively if missing.
    if not _has_any_device(client):
        _log.warning("[spotify] No device found before play() — launching Spotify.")
        launched = launch_spotify()
        if not launched:
            return {"status": "no_active_device", "reason": "spotify_not_installed"}
        device_found = wait_for_active_device(client, timeout=15.0)
        _log.warning("[spotify] wait_for_active_device() returned: %r", device_found)
        if not device_found:
            return {
                "status": "opening",
                "message": "Spotify se está abriendo. Inténtalo de nuevo en un momento.",
            }
        _log.warning("[spotify] device ready — sleeping 10s before search + playback.")
        time.sleep(10)
        device_id = _get_first_device_id(client)
        if device_id:
            _log.warning("[spotify] transferring playback to device_id=%r", device_id)
            client.transfer_playback(device_id, force_play=True)

    # 2) Resolve what to play (only after a device is confirmed ready).
    context_uri: str | None = None
    track_uris: list[str] | None = None
    result_meta: dict[str, Any] = {}

    if artist and track:
        # Precise track lookup using Spotify field filters.
        q = f'track:"{track}" artist:"{artist}"'
        results = client.search(q=q, type="track", limit=1)
        items = (results.get("tracks") or {}).get("items") or []
        if not items:
            return {"status": "no_results", "artist": artist, "track": track}
        track_uris = [items[0]["uri"]]
        result_meta = _track_info(items[0])

    elif artist:
        # Artist context — Spotify plays the artist's top tracks.
        results = client.search(q=artist, type="artist", limit=1)
        items = (results.get("artists") or {}).get("items") or []
        if not items:
            return {"status": "no_results", "artist": artist}
        context_uri = items[0]["uri"]
        result_meta = {"type": "artist", "name": items[0]["name"]}

    elif query:
        # Genre / mood — playlist-first, then track fallback.
        results = client.search(q=query, type="playlist,track", limit=1)
        playlists = (results.get("playlists") or {}).get("items") or []
        tracks = (results.get("tracks") or {}).get("items") or []
        if not playlists and not tracks:
            return {"status": "no_results", "query": query}
        if playlists:
            context_uri = playlists[0]["uri"]
            result_meta = {"type": "playlist", "name": playlists[0]["name"]}
        else:
            track_uris = [tracks[0]["uri"]]
            result_meta = _track_info(tracks[0])

    # 3) Play — always pass device_id so Spotify knows the exact target.
    device_id = _get_first_device_id(client)
    try:
        if context_uri:
            client.start_playback(device_id=device_id, context_uri=context_uri)
        elif track_uris:
            client.start_playback(device_id=device_id, uris=track_uris)
        else:
            client.start_playback(device_id=device_id)
        return {"status": "playing"} | result_meta
    except spotipy.SpotifyException as exc:
        _clear_device_cache()
        _log_spotify_exc(exc, "play")
        if exc.http_status == 404:
            return _no_device()
        raise


def pause(client: spotipy.Spotify) -> dict[str, Any]:
    """Pause playback on the active device."""
    def _do() -> dict[str, Any]:
        client.pause_playback()
        return {"status": "paused"}

    try:
        return _do()
    except spotipy.SpotifyException as exc:
        _clear_device_cache()
        _log_spotify_exc(exc, "pause")
        if exc.http_status == 404:
            return _handle_no_device(client, _do)
        raise


def next_track(client: spotipy.Spotify) -> dict[str, Any]:
    """Skip to the next track."""
    def _do() -> dict[str, Any]:
        client.next_track()
        current = client.current_user_playing_track()
        item = (current or {}).get("item")
        result: dict[str, Any] = {"status": "skipped"}
        if item:
            result.update(_track_info(item))
        return result

    try:
        return _do()
    except spotipy.SpotifyException as exc:
        _clear_device_cache()
        _log_spotify_exc(exc, "next_track")
        if exc.http_status == 404:
            return _handle_no_device(client, _do)
        raise


def previous_track(client: spotipy.Spotify) -> dict[str, Any]:
    """Go back to the previous track."""
    def _do() -> dict[str, Any]:
        client.previous_track()
        current = client.current_user_playing_track()
        item = (current or {}).get("item")
        result: dict[str, Any] = {"status": "previous"}
        if item:
            result.update(_track_info(item))
        return result

    try:
        return _do()
    except spotipy.SpotifyException as exc:
        _clear_device_cache()
        _log_spotify_exc(exc, "previous_track")
        if exc.http_status == 404:
            return _handle_no_device(client, _do)
        raise


def set_volume(client: spotipy.Spotify, volume_percent: int) -> dict[str, Any]:
    """Set device volume (0–100)."""
    vol = max(0, min(volume_percent, 100))

    def _do() -> dict[str, Any]:
        client.volume(vol)
        return {"status": "ok", "volume": vol}

    try:
        return _do()
    except spotipy.SpotifyException as exc:
        _clear_device_cache()
        _log_spotify_exc(exc, "set_volume")
        if exc.http_status == 404:
            return _handle_no_device(client, _do)
        raise


def get_current_track(client: spotipy.Spotify) -> dict[str, Any]:
    """Return the currently playing track info."""
    try:
        current = client.current_user_playing_track()
        if not current:
            return {"status": "nothing_playing"}
        item = current.get("item")
        if not item:
            return {"status": "nothing_playing"}
        result = _track_info(item)
        result["is_playing"] = current.get("is_playing", False)
        result["progress_ms"] = current.get("progress_ms", 0)
        result["duration_ms"] = item.get("duration_ms", 0)
        return result
    except spotipy.SpotifyException as exc:
        _clear_device_cache()
        _log_spotify_exc(exc, "get_current_track")
        if exc.http_status == 404:
            return _no_device()
        raise
