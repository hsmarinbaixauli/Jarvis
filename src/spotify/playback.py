"""Spotify Web API playback control wrappers."""

from __future__ import annotations

from typing import Any, Callable

import spotipy

from src.spotify.launcher import launch_spotify, wait_for_active_device


def _no_device() -> dict[str, str]:
    return {"status": "no_active_device"}


def _track_info(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "track": item["name"],
        "artist": ", ".join(a["name"] for a in item["artists"]),
        "album": item["album"]["name"],
        "uri": item["uri"],
    }


def _handle_no_device(
    client: spotipy.Spotify,
    retry: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    """Auto-launch Spotify and retry *retry* once on no-active-device errors."""
    if not launch_spotify():
        return {"status": "no_active_device", "reason": "spotify_not_installed"}
    if not wait_for_active_device(client):
        return _no_device()
    try:
        return retry()
    except spotipy.SpotifyException as exc:
        if exc.http_status == 404:
            return _no_device()
        raise


def play(client: spotipy.Spotify, query: str | None = None) -> dict[str, Any]:
    """Resume playback or start a search-driven play.

    Searches playlists first, then tracks when a query is given.
    Auto-launches Spotify desktop if no active Connect device is found.
    """
    def _do() -> dict[str, Any]:
        if query:
            results = client.search(q=query, type="playlist,track", limit=1)
            playlists = (results.get("playlists") or {}).get("items") or []
            tracks = (results.get("tracks") or {}).get("items") or []
            if playlists:
                client.start_playback(context_uri=playlists[0]["uri"])
                return {"status": "playing", "type": "playlist", "name": playlists[0]["name"]}
            if tracks:
                client.start_playback(uris=[tracks[0]["uri"]])
                return {"status": "playing"} | _track_info(tracks[0])
            return {"status": "no_results", "query": query}
        client.start_playback()
        return {"status": "playing"}

    try:
        return _do()
    except spotipy.SpotifyException as exc:
        if exc.http_status == 404:
            return _handle_no_device(client, _do)
        raise


def pause(client: spotipy.Spotify) -> dict[str, Any]:
    """Pause playback on the active device."""
    def _do() -> dict[str, Any]:
        client.pause_playback()
        return {"status": "paused"}

    try:
        return _do()
    except spotipy.SpotifyException as exc:
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
        if exc.http_status == 404:
            return _no_device()
        raise
