"""Spotify OAuth2 client factory."""

from __future__ import annotations

import os

import spotipy
from spotipy.oauth2 import SpotifyOAuth

_SCOPES = (
    "user-modify-playback-state "
    "user-read-playback-state "
    "user-read-currently-playing"
)
_CACHE_PATH = "credentials/spotify_token.json"


def get_spotify_client() -> spotipy.Spotify:
    """Return an authenticated Spotipy client using Authorization Code flow.

    Token is cached at credentials/spotify_token.json. On first run, opens a
    browser for user consent. Subsequent runs reuse the cached refresh token.

    Raises:
        RuntimeError: If any required env var is missing.
    """
    client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.environ.get("SPOTIFY_REDIRECT_URI")

    if not all([client_id, client_secret, redirect_uri]):
        raise RuntimeError(
            "Spotify env vars missing. Set SPOTIFY_CLIENT_ID, "
            "SPOTIFY_CLIENT_SECRET, and SPOTIFY_REDIRECT_URI in .env."
        )

    os.makedirs("credentials", exist_ok=True)
    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=_SCOPES,
        cache_path=_CACHE_PATH,
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth_manager)
