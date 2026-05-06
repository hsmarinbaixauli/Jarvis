"""Spotify Web API playback control wrappers."""

from __future__ import annotations

from typing import Any

import spotipy


def _no_device() -> dict[str, str]:
    return {"status": "no_active_device"}


def _track_info(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "track": item["name"],
        "artist": ", ".join(a["name"] for a in item["artists"]),
        "album": item["album"]["name"],
        "uri": item["uri"],
    }


def play(client: spotipy.Spotify, query: str | None = None) -> dict[str, Any]:
    """Resume playback or start a search-driven play.

    Searches playlists first, then tracks when a query is given.
    Returns no_active_device if Spotify Connect has no open device.
    """
    try:
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
    except spotipy.SpotifyException as exc:
        if exc.http_status == 404:
            return _no_device()
        raise


def pause(client: spotipy.Spotify) -> dict[str, Any]:
    """Pause playback on the active device."""
    try:
        client.pause_playback()
        return {"status": "paused"}
    except spotipy.SpotifyException as exc:
        if exc.http_status == 404:
            return _no_device()
        raise


def next_track(client: spotipy.Spotify) -> dict[str, Any]:
    """Skip to the next track."""
    try:
        client.next_track()
        current = client.current_user_playing_track()
        item = (current or {}).get("item")
        result: dict[str, Any] = {"status": "skipped"}
        if item:
            result.update(_track_info(item))
        return result
    except spotipy.SpotifyException as exc:
        if exc.http_status == 404:
            return _no_device()
        raise


def previous_track(client: spotipy.Spotify) -> dict[str, Any]:
    """Go back to the previous track."""
    try:
        client.previous_track()
        current = client.current_user_playing_track()
        item = (current or {}).get("item")
        result: dict[str, Any] = {"status": "previous"}
        if item:
            result.update(_track_info(item))
        return result
    except spotipy.SpotifyException as exc:
        if exc.http_status == 404:
            return _no_device()
        raise


def set_volume(client: spotipy.Spotify, volume_percent: int) -> dict[str, Any]:
    """Set device volume (0–100)."""
    vol = max(0, min(volume_percent, 100))
    try:
        client.volume(vol)
        return {"status": "ok", "volume": vol}
    except spotipy.SpotifyException as exc:
        if exc.http_status == 404:
            return _no_device()
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
